"""
Substrate Phase A Verification Suite
Tests the production foundation layers:
1. Database health & dialect inspection
2. Pluggable Object Storage abstraction (Local & MinIO)
3. Redis distributed state & temporal OCR fusion cache
4. Camera connector abstractions & Factory
5. Deployment Readiness API (/api/system/readiness)
"""

import os
import sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import check_db_health
from backend.app.services.storage import get_storage, LocalFileStorage
from backend.app.core.redis_client import redis_state
from backend.app.services.connectors import ConnectorFactory, RTSPConnector, ONVIFConnector, VMSConnector
from backend.app.models.orm import Camera

client = TestClient(app)

def test_database_substrate_health():
    """Verify database connection health check returns dialect and latency."""
    health = check_db_health()
    assert health["status"] == "READY"
    assert "dialect" in health
    assert health["latency_ms"] >= 0.0
    print(f"[PASS] test_database_substrate_health (Dialect: {health['dialect']}, Latency: {health['latency_ms']} ms)")

def test_storage_abstraction_local():
    """Verify ObjectStorage contract using LocalFileStorage."""
    storage = LocalFileStorage()
    test_bucket = "test-evidence"
    test_key = "snapshot_sample.jpg"
    test_data = b"SAMPLE_BINARY_IMAGE_DATA_SEC_65B"

    # Put object
    uri = storage.put_object(test_bucket, test_key, test_data)
    assert uri.startswith("file://")

    # Get object
    retrieved = storage.get_object(test_bucket, test_key)
    assert retrieved == test_data

    # Presigned URL
    url = storage.get_presigned_url(test_bucket, test_key)
    assert f"{test_bucket}/{test_key}" in url

    # Health check
    h = storage.health_check()
    assert h["status"] == "READY"

    # Clean up
    deleted = storage.delete_object(test_bucket, test_key)
    assert deleted is True
    print("[PASS] test_storage_abstraction_local (Put/Get/URL/Delete verified)")

def test_redis_state_and_temporal_fusion():
    """Verify Redis distributed state caching and temporal OCR fusion buffer."""
    # 1. Watchlist cache
    plate = "GJ01AB1234"
    sample_data = {"owner": "Rameshwar Sharma", "risk": "CRITICAL", "fir": "FIR-2026/0981"}
    redis_state.cache_watchlist_entry(plate, sample_data, ttl_seconds=60)
    cached = redis_state.get_cached_watchlist_entry(plate)
    assert cached is not None
    assert cached["owner"] == "Rameshwar Sharma"

    # 2. Temporal OCR fusion buffer
    cam_id = "CAM-GJ-AHM-01"
    import random
    track_id = random.randint(10000, 99999)
    redis_state.record_track_ocr_sample(cam_id, track_id, "GJ01AB1234", 0.94)
    redis_state.record_track_ocr_sample(cam_id, track_id, "GJ01AB1234", 0.96)
    redis_state.record_track_ocr_sample(cam_id, track_id, "GJ01A81234", 0.72)

    samples = redis_state.get_track_ocr_samples(cam_id, track_id)
    assert len(samples) == 3
    assert samples[0]["plate"] == "GJ01AB1234"

    # 3. Track state
    redis_state.set_track_state(cam_id, track_id, {"speed": 62.5, "heading": "North"})
    t_state = redis_state.get_track_state(cam_id, track_id)
    assert t_state is not None
    assert t_state["speed"] == 62.5

    print("[PASS] test_redis_state_and_temporal_fusion (Watchlist cache, OCR fusion buffer & Track state verified)")

def test_camera_connector_factory():
    """Verify ConnectorFactory produces appropriate protocol drivers for RTSP, ONVIF, and VMS cameras."""
    # RTSP Camera
    rtsp_cam = Camera(logical_camera_id="CAM-RTSP-01", protocol="RTSP", stream_url="rtsp://10.0.0.1:554/live")
    conn_rtsp = ConnectorFactory.create_connector(rtsp_cam)
    assert isinstance(conn_rtsp, RTSPConnector)
    assert conn_rtsp.get_health_metrics()["protocol"] == "RTSP"

    # ONVIF Camera
    onvif_cam = Camera(logical_camera_id="CAM-ONVIF-01", protocol="ONVIF", stream_url="10.0.0.2")
    conn_onvif = ConnectorFactory.create_connector(onvif_cam)
    assert isinstance(conn_onvif, ONVIFConnector)

    # VMS Federated Camera
    vms_cam = Camera(logical_camera_id="CAM-VMS-01", protocol="VMS-API", stream_url="10.0.0.3", vms_type="Genetec")
    conn_vms = ConnectorFactory.create_connector(vms_cam)
    assert isinstance(conn_vms, VMSConnector)
    assert conn_vms.get_health_metrics()["vms_vendor"] == "Genetec"

    print("[PASS] test_camera_connector_factory (RTSP, ONVIF, VMS protocol connectors instantiated)")

def test_deployment_readiness_api():
    """Verify /api/system/readiness contract for full infrastructure substrate."""
    res = client.get("/api/system/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("READY", "DEGRADED")
    assert "database" in data
    assert "redis" in data
    assert "kafka" in data
    assert "object_storage" in data
    assert "ai_models" in data
    assert "camera_connectivity" in data
    assert "government_adapters" in data
    assert "ONLINE" in data["government_adapters"]["vahan"]
    assert "ONLINE" in data["government_adapters"]["egujcop"]
    print(f"[PASS] test_deployment_readiness_api (Overall status: {data['status']})")

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING SUBSTRATE PHASE A VERIFICATION TESTS                    ")
    print("==================================================================")
    test_database_substrate_health()
    test_storage_abstraction_local()
    test_redis_state_and_temporal_fusion()
    test_camera_connector_factory()
    test_deployment_readiness_api()
    print("\n*** ALL PHASE A SUBSTRATE TESTS PASSED WITH 100% SUCCESS!\n")
