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
        self._lock = threading.RLock()
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
        self._lock = threading.RLock()
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


# =====================================================================
# CANONICAL KAFKA STREAM WORKERS (END-TO-END PIPELINE)
# =====================================================================
import base64
import logging

logger = logging.getLogger("givin.stream_workers")


def _get_event_bus():
    from backend.app.services.event_bus import event_bus
    return event_bus


class AIVisionStreamWorker:
    """
    AI Vision Stream Consumer Group Worker ('cg-ai-vision-workers').
    Consumes raw camera frame events from Kafka topic 'givin.camera.frames' / 'givin.camera.frames.raw',
    executes YOLO11 vehicle detection, ByteTrack tracking, and PaddleOCR via vision_pipeline,
    and publishes structured detections and ANPR results down the canonical event bus.
    """

    def __init__(self, bus: Optional[Any] = None):
        self._bus = bus
        self._frames_processed = 0
        self._lock = threading.Lock()

    def process_frame_event(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        bus = self._bus or _get_event_bus()
        camera_id = payload.get("camera_id", "CAM-DEFAULT")
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        frame_pts = payload.get("frame_pts")
        pts_delta = payload.get("pts_delta")
        arrival_timestamp = payload.get("arrival_timestamp") or time.time()

        frame_bytes = None
        if "frame_bytes" in payload:
            raw = payload["frame_bytes"]
            if isinstance(raw, bytes):
                frame_bytes = raw
            elif isinstance(raw, str):
                try:
                    frame_bytes = base64.b64decode(raw)
                except Exception:
                    frame_bytes = raw.encode("utf-8")
        elif "frame_base64" in payload:
            try:
                frame_bytes = base64.b64decode(payload["frame_base64"])
            except Exception:
                pass

        detections = []
        if frame_bytes:
            try:
                from backend.app.services.vision_pipeline import vision_pipeline
                plate_detections = vision_pipeline.detect(
                    frame_bytes,
                    camera_id=camera_id,
                    frame_pts=frame_pts,
                    pts_delta=pts_delta
                )
                detections = [d.to_dict() for d in plate_detections]
            except Exception as ex:
                logger.warning(f"AIVisionStreamWorker detection failed on {camera_id}: {ex}")
        elif "detections" in payload:
            detections = payload["detections"]
        elif "plate_text" in payload:
            detections = [{
                "plate_text": payload["plate_text"],
                "ocr_confidence": payload.get("confidence", 0.95),
                "vehicle_type": payload.get("vehicle_type", "Car"),
                "detector_confidence": 0.95,
                "bbox": payload.get("bbox", [100, 100, 300, 300]),
                "track_id": payload.get("track_id", 1),
                "frame_pts": frame_pts,
                "pts_delta": pts_delta
            }]

        with self._lock:
            self._frames_processed += 1

        results = []
        for det in detections:
            # 1. Publish vehicle detection
            veh_event = {
                "camera_id": camera_id,
                "track_id": det.get("track_id", 1),
                "bbox": det.get("bbox"),
                "detector_confidence": det.get("detector_confidence", 0.9),
                "vehicle_type": det.get("vehicle_type", "Car"),
                "timestamp": timestamp,
                "frame_pts": det.get("frame_pts", frame_pts),
                "pts_delta": det.get("pts_delta", pts_delta),
                "arrival_timestamp": arrival_timestamp
            }
            bus.publish(bus.TOPIC_VEHICLE_DETECTIONS, veh_event, partition_key=camera_id)

            # 2. Publish ANPR result
            plate_text = det.get("plate_text", "")
            anpr_event = {
                "camera_id": camera_id,
                "track_id": det.get("track_id", 1),
                "plate_text": plate_text,
                "ocr_confidence": det.get("ocr_confidence", 0.9),
                "vehicle_type": det.get("vehicle_type", "Car"),
                "detector_confidence": det.get("detector_confidence", 0.9),
                "bbox": det.get("bbox"),
                "speed_kmh": payload.get("speed_kmh", 55.0),
                "timestamp": timestamp,
                "frame_pts": det.get("frame_pts", frame_pts),
                "pts_delta": det.get("pts_delta", pts_delta),
                "arrival_timestamp": arrival_timestamp,
                "evidence_hash": payload.get("evidence_hash"),
                "evidence_uri": payload.get("evidence_uri")
            }
            bus.publish(bus.TOPIC_ANPR_RESULTS, anpr_event, partition_key=plate_text or camera_id)
            results.append(anpr_event)

        return results

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"frames_processed": self._frames_processed}


class TrackingStreamWorker:
    """
    Tracking Stream Consumer Group Worker ('cg-tracking-workers').
    Consumes ANPR results and vehicle detections from Kafka, correlates tracklets,
    and publishes tracking events and vehicle sightings down the pipeline.
    """

    def __init__(self, bus: Optional[Any] = None):
        self._bus = bus
        self._tracks_processed = 0
        self._lock = threading.Lock()

    def process_anpr_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        bus = self._bus or _get_event_bus()
        camera_id = payload.get("camera_id", "CAM-DEFAULT")
        track_id = payload.get("track_id", 1)
        plate_text = payload.get("plate_text", "")
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        frame_pts = payload.get("frame_pts")
        pts_delta = payload.get("pts_delta")
        arrival_timestamp = payload.get("arrival_timestamp")

        # 1. Publish tracking event
        tracking_event = {
            "camera_id": camera_id,
            "track_id": track_id,
            "plate_text": plate_text,
            "timestamp": timestamp,
            "frame_pts": frame_pts,
            "pts_delta": pts_delta,
            "arrival_timestamp": arrival_timestamp
        }
        bus.publish(bus.TOPIC_TRACKING_EVENTS, tracking_event, partition_key=f"{camera_id}-{track_id}")

        # 2. Publish vehicle sighting for micro-batch persistence & watchlist matching
        norm_plate = ANPREngine.normalize_plate(plate_text) or plate_text
        sighting_event = {
            "camera_id": camera_id,
            "plate_text": plate_text,
            "normalized_plate": norm_plate,
            "confidence": payload.get("ocr_confidence", 0.9),
            "vehicle_type": payload.get("vehicle_type", "Car"),
            "vehicle_color": payload.get("vehicle_color", "Unknown"),
            "speed_kmh": payload.get("speed_kmh", 60.0),
            "timestamp": timestamp,
            "frame_pts": frame_pts,
            "pts_delta": pts_delta,
            "arrival_timestamp": arrival_timestamp,
            "evidence_hash": payload.get("evidence_hash"),
            "evidence_uri": payload.get("evidence_uri")
        }
        bus.publish(bus.TOPIC_VEHICLE_SIGHTINGS, sighting_event, partition_key=norm_plate)

        with self._lock:
            self._tracks_processed += 1

        return sighting_event

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"tracks_processed": self._tracks_processed}


class WatchlistStreamWorker:
    """
    Watchlist Stream Consumer Group Worker ('cg-watchlist-matchers').
    Consumes vehicle sightings from Kafka, matches against database watchlists,
    and publishes alerts across Kafka and WebSocket real-time channels.
    """

    def __init__(self, bus: Optional[Any] = None):
        self._bus = bus
        self._matches_count = 0
        self._lock = threading.Lock()

    def process_sighting_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        bus = self._bus or _get_event_bus()
        plate = payload.get("plate_text", "")
        norm_plate = payload.get("normalized_plate") or ANPREngine.normalize_plate(plate) or plate
        camera_id = payload.get("camera_id", "CAM-DEFAULT")

        # Database matching
        from backend.app.core.database import SessionLocal
        db = SessionLocal()
        try:
            cam = db.query(Camera).filter((Camera.id == camera_id) | (Camera.logical_camera_id == camera_id)).first()
            district = cam.district if cam else "Ahmedabad"

            sighting_obj = VehicleSighting(
                id=payload.get("id") or f"sight-{uuid.uuid4().hex[:8]}",
                camera_id=cam.id if cam else camera_id,
                plate_text=plate,
                normalized_plate=norm_plate,
                confidence=payload.get("confidence", 0.9),
                speed_kmh=payload.get("speed_kmh", 60.0),
                vehicle_type=payload.get("vehicle_type", "Car"),
                timestamp=datetime.now(timezone.utc)
            )
            alert = WatchlistMatcher.trigger_alert_if_matched(db, sighting_obj)
            if alert:
                alert_payload = {
                    "alert_uid": alert.alert_uid,
                    "risk_level": alert.risk_level,
                    "plate_text": alert.plate_text,
                    "camera_id": cam.logical_camera_id if cam else camera_id,
                    "district": district,
                    "matched_reason": getattr(alert, "remarks", "Watchlist Match") or "Watchlist Match",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                # Publish watchlist match
                bus.publish(bus.TOPIC_WATCHLIST_MATCHES, alert_payload, partition_key=norm_plate)

                # Publish alert
                bus.publish(bus.TOPIC_ALERTS, alert_payload, partition_key=norm_plate)

                with self._lock:
                    self._matches_count += 1
                return alert_payload
        except Exception as e:
            logger.error(f"WatchlistStreamWorker matching failed: {e}")
        finally:
            db.close()

        return None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"matches_count": self._matches_count}


# Singleton worker instances
ai_vision_worker = AIVisionStreamWorker()
tracking_stream_worker = TrackingStreamWorker()
watchlist_stream_worker = WatchlistStreamWorker()


def initialize_canonical_pipeline(bus: Optional[Any] = None) -> None:
    """
    Wires consumer groups across the statewide Kafka streaming backbone:
    - givin.camera.frames.raw -> AIVisionStreamWorker
    - givin.anpr.results -> TrackingStreamWorker
    - givin.vehicle.sightings -> WatchlistStreamWorker
    """
    event_bus = bus or _get_event_bus()

    # Bind AI Vision consumer group
    event_bus.subscribe_consumer_group(
        "cg-ai-vision-workers",
        event_bus.TOPIC_CAMERA_FRAMES,
        ai_vision_worker.process_frame_event
    )
    event_bus.subscribe_consumer_group(
        "cg-ai-vision-workers",
        event_bus.TOPIC_CAMERA_FRAMES_RAW,
        ai_vision_worker.process_frame_event
    )

    # Bind Tracking consumer group
    event_bus.subscribe_consumer_group(
        "cg-tracking-workers",
        event_bus.TOPIC_ANPR_RESULTS,
        tracking_stream_worker.process_anpr_event
    )

    # Bind Watchlist consumer group
    event_bus.subscribe_consumer_group(
        "cg-watchlist-matchers",
        event_bus.TOPIC_VEHICLE_SIGHTINGS,
        watchlist_stream_worker.process_sighting_event
    )
    logger.info("Canonical Kafka streaming pipeline initialized with 3 consumer groups.")
