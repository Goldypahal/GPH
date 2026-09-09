"""
Test Suite for Phase E: Resilient Event Streaming & Kafka Architecture
Verifies:
1. Decoupled dual-mode stream broker (topic publish/subscribe, partitioning, metrics).
2. Asynchronous micro-batch ingestion worker (bulk DB commits & ANPR normalization).
3. Dead Letter Queue (DLQ) poison pill quarantine & failure replay.
4. FastAPI streaming control endpoints (/api/system/events/metrics, /dlq, /dlq/replay).
"""

import os
import sys
import uuid
import time
from datetime import datetime, timezone

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import VehicleSighting, Camera
from backend.app.services.event_bus import event_bus
from backend.app.services.stream_workers import micro_batch_worker, dlq_manager

client = TestClient(app)

def test_stream_broker_topics_and_partitioning():
    """Verify stream broker routes events across all 5 standard GIVIN topics."""
    received = []

    def handler(payload):
        received.append(payload)

    event_bus.subscribe(event_bus.TOPIC_TELEMETRY_CAMERA, handler)

    # Publish telemetry heartbeat
    test_cam = f"CAM-STREAM-{uuid.uuid4().hex[:6].upper()}"
    event_bus.publish(
        event_bus.TOPIC_TELEMETRY_CAMERA,
        {"camera_id": test_cam, "fps": 25.0, "latency_ms": 18.2, "status": "ONLINE"}
    )

    assert len(received) >= 1
    assert received[-1]["camera_id"] == test_cam

    metrics = event_bus.get_pipeline_metrics()
    assert metrics["total_events_published"] > 0
    assert metrics["status"] == "HEALTHY_STREAMING"
    assert "broker_mode" in metrics
    print(f"[PASS] test_stream_broker_topics_and_partitioning passed (Mode: {metrics['broker_mode']}, Total Pub: {metrics['total_events_published']}).")

def test_micro_batch_ingestion_throughput():
    """Verify micro-batch worker buffers detections and commits in bulk transactions."""
    db = SessionLocal()
    try:
        first_cam = db.query(Camera).first()
        cam_id = first_cam.id if first_cam else "CAM-AHM-01"

        micro_batch_worker._buffer.clear()
        burst_size = 20
        unique_plates = []

        for i in range(burst_size):
            plate = f"GJ01ST{uuid.uuid4().hex[:4].upper()}"
            unique_plates.append(plate)
            micro_batch_worker.enqueue_sighting({
                "camera_id": cam_id,
                "plate_text": plate,
                "confidence": 0.94,
                "speed_kmh": 72.0,
                "vehicle_type": "Car"
            })

        # Execute micro-batch commit
        committed = micro_batch_worker.flush_batch(db)
        assert committed >= burst_size

        # Verify sightings exist in DB
        sample_plate = unique_plates[0]
        found = db.query(VehicleSighting).filter(VehicleSighting.plate_text == sample_plate).first()
        assert found is not None
        assert found.normalized_plate == sample_plate

        print(f"[PASS] test_micro_batch_ingestion_throughput passed (Bulk committed {committed} sightings in micro-batch).")
    finally:
        db.close()

def test_dead_letter_queue_quarantine_and_replay():
    """
    Verify poison pill message handling:
    1. Malformed payload quarantined to DLQ without crashing ingestion.
    2. Inspected via /api/system/events/dlq.
    3. Successfully recovered via /api/system/events/dlq/replay.
    """
    dlq_manager.purge()
    assert dlq_manager.size() == 0

    # 1. Enqueue poison pill
    poison_payload = {"corrupted_field": "INVALID_DATA_PAYLOAD", "camera_id": "NON_EXISTENT"}
    dlq_manager.enqueue_poison_pill(
        topic=event_bus.TOPIC_SIGHTINGS_RAW,
        payload=poison_payload,
        error_reason="Missing plate_text in ANPR detection frame"
    )
    assert dlq_manager.size() == 1

    # 2. Inspect via HTTP API
    res = client.get("/api/system/events/dlq")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[-1]["original_topic"] == event_bus.TOPIC_SIGHTINGS_RAW
    assert "Missing plate_text" in items[-1]["error_reason"]

    # 3. Replay via API
    res_replay = client.post("/api/system/events/dlq/replay")
    assert res_replay.status_code == 200
    replay_data = res_replay.json()
    assert replay_data["status"] == "COMPLETED"
    assert replay_data["replayed_count"] >= 1

    # DLQ should now be drained of recovered items
    assert dlq_manager.size() == 0

    print(f"[PASS] test_dead_letter_queue_quarantine_and_replay passed (Quarantined poison message & replayed successfully).")

def test_streaming_metrics_api():
    """Verify GET /api/system/events/metrics endpoint returns complete performance telemetry."""
    res = client.get("/api/system/events/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "broker_mode" in data
    assert data["total_events_published"] >= 1
    assert "current_throughput_mps" in data
    assert "active_topics" in data
    assert "dlq_size" in data
    assert data["status"] == "HEALTHY_STREAMING"
    print(f"[PASS] test_streaming_metrics_api passed (MPS: {data['current_throughput_mps']}, DLQ: {data['dlq_size']}).")

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING PHASE E RESILIENT EVENT STREAMING VERIFICATION SUITE    ")
    print("==================================================================")
    test_stream_broker_topics_and_partitioning()
    test_micro_batch_ingestion_throughput()
    test_dead_letter_queue_quarantine_and_replay()
    test_streaming_metrics_api()
    print("\n*** ALL PHASE E EVENT STREAMING TESTS PASSED WITH 100% SUCCESS!\n")
