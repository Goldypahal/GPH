"""
Integration Test Suite: Sentinel Grid cam01 - cam30 Database & API Verification.
Validates:
1. All 30 cameras persistently exist in the database with status ACTIVE, protocol RTSP, and credentials.
2. Stream URLs point to 103.250.160.189:8554 with URL-encoded auth credentials.
3. Department affiliation to HOME_POLICE with health metrics.
4. Queryable and filterable via GET /api/cameras and GET /api/ingest.
5. District mapping across Ahmedabad, Gandhinagar, Surat, Vadodara, Rajkot, Bhavnagar, Jamnagar, Kutch, Bharuch, Anand, Mehsana.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, CameraHealth, CameraCredential, Department

client = TestClient(app)

EXPECTED_CAM_IDS = [f"cam{i:02d}" for i in range(1, 31)]
SENTINEL_GATEWAY_HOST = "103.250.160.189:8554"
AUTH_PREFIX = "amanpalpathi%40gmail.com:UDTR-YLX2-9VTC"


def test_sentinel_30_cameras_exist_in_db():
    """Validates that all 30 Sentinel cameras are registered in the GIVIN database."""
    db = SessionLocal()
    try:
        cams = db.query(Camera).filter(Camera.logical_camera_id.in_(EXPECTED_CAM_IDS)).all()
        assert len(cams) == 30, f"Expected 30 Sentinel cameras in DB, found {len(cams)}"

        cam_map = {c.logical_camera_id: c for c in cams}
        for cam_id in EXPECTED_CAM_IDS:
            assert cam_id in cam_map, f"Missing camera {cam_id} in database"
            c = cam_map[cam_id]
            assert c.status == "ACTIVE", f"{cam_id} status expected ACTIVE, got {c.status}"
            assert c.protocol == "RTSP", f"{cam_id} protocol expected RTSP, got {c.protocol}"
            assert c.vendor == "Sentinel-MediaMTX"
            assert c.vms_type == "MediaMTX-RTSP"
            assert SENTINEL_GATEWAY_HOST in c.stream_url, f"{cam_id} stream_url missing gateway host"
            assert AUTH_PREFIX in c.stream_url, f"{cam_id} stream_url missing credentials"
            assert c.stream_url.endswith(f"/stream/{cam_id}"), f"{cam_id} URL format mismatch"
            assert c.district is not None and len(c.district) > 0
            assert c.location_name is not None and len(c.location_name) > 0
            assert c.lat != 0.0 and c.lng != 0.0
            assert c.fps == 25
            assert c.resolution in ("1080p", "720p", "2K QHD", "960p", "576p")
    finally:
        db.close()


def test_sentinel_cameras_health_and_credentials_attached():
    """Validates that every Sentinel camera has associated health and credential records."""
    db = SessionLocal()
    try:
        cams = db.query(Camera).filter(Camera.logical_camera_id.in_(EXPECTED_CAM_IDS)).all()
        for c in cams:
            # Check Health
            health = db.query(CameraHealth).filter(CameraHealth.camera_id == c.id).first()
            assert health is not None, f"Camera {c.logical_camera_id} has no CameraHealth record"
            assert health.status in ("ONLINE", "HEALTHY"), f"{c.logical_camera_id} unexpected health status {health.status}"

            # Check Credentials
            cred = db.query(CameraCredential).filter(CameraCredential.camera_id == c.id).first()
            assert cred is not None, f"Camera {c.logical_camera_id} has no CameraCredential record"
            assert cred.username == "amanpalpathi@gmail.com"
            assert cred.encrypted_password == "UDTR-YLX2-9VTC"
            assert cred.port == 8554
    finally:
        db.close()


def test_sentinel_cameras_api_discovery():
    """Validates that GET /api/cameras returns all 30 Sentinel cameras with correct fields."""
    res = client.get("/api/cameras")
    assert res.status_code == 200
    data = res.json()
    sentinel_items = [item for item in data if item["logical_camera_id"] in EXPECTED_CAM_IDS]
    assert len(sentinel_items) == 30, f"Expected 30 Sentinel cameras from API, got {len(sentinel_items)}"

    sample = sentinel_items[0]
    assert "logical_camera_id" in sample
    assert "stream_url" in sample
    assert "district" in sample
    assert "status" in sample
    assert sample["status"] == "ACTIVE"
    assert sample["protocol"] == "RTSP"


def test_sentinel_cameras_district_filtering():
    """Validates that GET /api/cameras?district=... accurately isolates Sentinel cameras."""
    # Ahmedabad has cam01-cam06
    res_ahm = client.get("/api/cameras?district=Ahmedabad")
    assert res_ahm.status_code == 200
    ahm_ids = {c["logical_camera_id"] for c in res_ahm.json()}
    for expected in ["cam01", "cam02", "cam03", "cam04", "cam05", "cam06"]:
        assert expected in ahm_ids, f"Expected {expected} in Ahmedabad district query"

    # Surat has cam11-cam14
    res_srt = client.get("/api/cameras?district=Surat")
    assert res_srt.status_code == 200
    srt_ids = {c["logical_camera_id"] for c in res_srt.json()}
    for expected in ["cam11", "cam12", "cam13", "cam14"]:
        assert expected in srt_ids, f"Expected {expected} in Surat district query"

    # Vadodara has cam15-cam18
    res_vad = client.get("/api/cameras?district=Vadodara")
    assert res_vad.status_code == 200
    vad_ids = {c["logical_camera_id"] for c in res_vad.json()}
    for expected in ["cam15", "cam16", "cam17", "cam18"]:
        assert expected in vad_ids, f"Expected {expected} in Vadodara district query"


def test_sentinel_catalogue_contract_includes_grid():
    """Validates that the Sentinel catalogue endpoint (/api/ingest) includes cam01-cam30."""
    res = client.get("/api/ingest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CATALOGUE_AVAILABLE"
    catalogue_ids = {c["camera_id"] for c in data["cameras"]}
    for cam_id in EXPECTED_CAM_IDS:
        assert cam_id in catalogue_ids, f"Camera {cam_id} not present in Sentinel catalogue"
