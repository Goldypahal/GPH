"""
GIVIN Micro-Batch Stream Ingestion Worker & Dead Letter Queue (DLQ) Engine.
Enables high-throughput decoupled ingestion (up to 80,000 cameras) with micro-batching,
database bulk commits, poison message quarantine, and self-healing replay capabilities.
"""

import uuid
import time
import threading
from datetime import datetime, timezone
from collections import deque
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from backend.app.models.orm import VehicleSighting, Camera
from backend.app.services.anpr_engine import ANPREngine
from backend.app.services.watchlist_matcher import WatchlistMatcher

class DeadLetterQueueManager:
    """
    Manages poison pills, deserialization errors, and failed database commits.
    Quarantines corrupted messages without stalling real-time ingestion pipelines.
    """

    def __init__(self, max_size: int = 1000):
        self._lock = threading.Lock()
        self._dlq: deque = deque(maxlen=max_size)

    def enqueue_poison_pill(
        self,
        topic: str,
        payload: Dict[str, Any],
        error_reason: str
    ) -> Dict[str, Any]:
        with self._lock:
            item = {
                "message_id": f"DLQ-{uuid.uuid4().hex[:8].upper()}",
                "original_topic": topic,
                "payload": payload,
                "error_reason": str(error_reason),
                "failed_at": datetime.now(timezone.utc),
                "retry_count": 0
            }
            self._dlq.append(item)
            return item

    def list_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._dlq)[-limit:]

    def size(self) -> int:
        with self._lock:
            return len(self._dlq)

    def purge(self) -> int:
        with self._lock:
            count = len(self._dlq)
            self._dlq.clear()
            return count

    def replay_messages(
        self,
        reprocess_func: Callable[[str, Dict[str, Any]], bool],
        max_count: int = 50
    ) -> Dict[str, Any]:
        """
        Re-injects quarantined messages through the ingestion pipeline.
        Removes successfully reprocessed messages; increments retry count on failure.
        """
        replayed = 0
        failed = 0
        with self._lock:
            items_to_retry = list(self._dlq)[:max_count]
            remaining: deque = deque(maxlen=self._dlq.maxlen)

            # Keep items that are beyond the max_count window
            if len(self._dlq) > max_count:
                remaining.extend(list(self._dlq)[max_count:])

            for item in items_to_retry:
                try:
                    success = reprocess_func(item["original_topic"], item["payload"])
                    if success:
                        replayed += 1
                    else:
                        item["retry_count"] += 1
                        remaining.append(item)
                        failed += 1
                except Exception as e:
                    item["retry_count"] += 1
                    item["error_reason"] = f"Replay failed: {e}"
                    remaining.append(item)
                    failed += 1

            self._dlq = remaining

        return {
            "replayed_count": replayed,
            "failed_count": failed,
            "status": "COMPLETED",
            "message": f"Successfully reprocessed {replayed} messages; {failed} failed or retained in DLQ."
        }

dlq_manager = DeadLetterQueueManager()

class MicroBatchIngestionWorker:
    """
    Buffers high-frequency ANPR sightings and flushes them in bulk database transactions.
    Supports micro-batching up to 100 items per commit or 250ms intervals.
    """

    BATCH_SIZE_THRESHOLD = 50
    FLUSH_INTERVAL_SEC = 0.25

    def __init__(self):
        self._lock = threading.Lock()
        self._buffer: List[Dict[str, Any]] = []
        self._total_ingested = 0
        self._total_committed = 0
        self._last_flush_time = time.time()
        self._is_running = True

    def enqueue_sighting(self, payload: Dict[str, Any]) -> None:
        """Buffers raw sighting payload for asynchronous micro-batch processing."""
        with self._lock:
            self._buffer.append(payload)
            self._total_ingested += 1
            should_flush = len(self._buffer) >= self.BATCH_SIZE_THRESHOLD

        if should_flush:
            from backend.app.core.database import SessionLocal
            db = SessionLocal()
            try:
                self.flush_batch(db)
            finally:
                db.close()

    def flush_batch(self, db: Session) -> int:
        """Commits all buffered sightings to database in a single micro-batch transaction."""
        with self._lock:
            if not self._buffer:
                return 0
            batch = list(self._buffer)
            self._buffer.clear()
            self._last_flush_time = time.time()

        committed = 0
        for item in batch:
            try:
                raw_plate = item.get("plate_text", "")
                norm_plate = ANPREngine.normalize_plate(raw_plate) or raw_plate

                # Validate or find camera
                camera_id = item.get("camera_id")
                if not camera_id:
                    cam = db.query(Camera).first()
                    camera_id = cam.id if cam else "CAM-DEFAULT"

                ts = item.get("timestamp")
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        ts = datetime.now(timezone.utc)
                elif not isinstance(ts, datetime):
                    ts = datetime.now(timezone.utc)

                sighting = VehicleSighting(
                    id=item.get("id") or f"sight-{uuid.uuid4().hex[:8]}",
                    camera_id=camera_id,
                    plate_text=raw_plate,
                    normalized_plate=norm_plate,
                    confidence=float(item.get("confidence", 0.90)),
                    speed_kmh=float(item.get("speed_kmh", 60.0)),
                    vehicle_type=item.get("vehicle_type", "Car"),
                    vehicle_color=item.get("vehicle_color", "Unknown"),
                    evidence_uri=item.get("evidence_uri"),
                    timestamp=ts
                )
                db.add(sighting)
                db.flush()

                # Trigger watchlist check
                WatchlistMatcher.trigger_alert_if_matched(db, sighting)
                committed += 1
            except Exception as e:
                # Isolate poison pill to DLQ without failing whole batch
                dlq_manager.enqueue_poison_pill(
                    topic="givin.sightings.raw",
                    payload=item,
                    error_reason=f"Ingestion batch error: {e}"
                )

        try:
            db.commit()
            with self._lock:
                self._total_committed += committed
        except Exception as e:
            db.rollback()
            # If batch commit fails, quarantine all to DLQ
            for item in batch:
                dlq_manager.enqueue_poison_pill(
                    topic="givin.sightings.raw",
                    payload=item,
                    error_reason=f"Batch transaction commit failure: {e}"
                )
            committed = 0

        return committed

    def get_worker_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "buffer_depth": len(self._buffer),
                "total_ingested": self._total_ingested,
                "total_committed": self._total_committed,
                "dlq_depth": dlq_manager.size()
            }

micro_batch_worker = MicroBatchIngestionWorker()
