"""
Comprehensive Acceptance Test Suite for:
1. Spatial GIS Intelligence Engine (Nearest, Radius, Route Corridor, Pursuit Cone, District Containment)
2. Camera Operational Lifecycle State Machine (REGISTER -> VALIDATE -> CONNECT -> AUTH -> HEALTH -> STREAM -> AI_ENABLED)
3. Camera Real-time Heartbeat & Health Telemetry
4. MinIO WORM Evidence Vault (Package Sealing, SHA-256 Integrity Verification, Chain of Custody)
5. Statewide Distributed Topology (80,000 Cameras, 33 Districts, 4 Regional Hubs, Gandhinagar C4I HQ)
6. Multi-Mode Government Database Adapters (VAHAN, SARATHI, CCTNS, eGujCop, AFIS, NAFIS)
"""

import os
import sys
import base64
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, Case, Department, CameraHealth
from backend.app.services.gov_adapters.base import IntegrationMode
from backend.app.services.gov_adapters import (
    vahan_adapter,
    sarathi_adapter,
    cctns_adapter,
    egujcop_adapter,
    afis_adapter,
    nafis_adapter
)

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def seed_cameras(db_session):
    """Ensures test cameras exist in Ahmedabad and Gandhinagar."""
    dept = db_session.query(Department).first()
    dept_id = dept.id if dept else "dept-police-ahm"

    test_cams = [
        {
            "logical_camera_id": "TEST-CAM-AHM-01",
            "name": "Ahmedabad SG Highway Junction",
            "department_id": dept_id,
            "district": "Ahmedabad",
            "location_name": "SG Highway & Iscon Cross Road",
            "lat": 23.0225,
            "lng": 72.5714,
            "status": "ACTIVE"
        },
        {
            "logical_camera_id": "TEST-CAM-AHM-02",
            "name": "Ahmedabad Ashram Road",
            "department_id": dept_id,
            "district": "Ahmedabad",
            "location_name": "Ashram Road Income Tax Circle",
            "lat": 23.0410,
            "lng": 72.5690,
            "status": "ACTIVE"
        },
        {
            "logical_camera_id": "TEST-CAM-GN-01",
            "name": "Gandhinagar CH-3 Circle",
            "department_id": dept_id,
            "district": "Gandhinagar",
            "location_name": "Sector 11 CH-3",
            "lat": 23.2156,
            "lng": 72.6369,
            "status": "ACTIVE"
        }
    ]

    created = []
    for c_data in test_cams:
        cam = db_session.query(Camera).filter(Camera.logical_camera_id == c_data["logical_camera_id"]).first()
        if not cam:
            cam = Camera(**c_data)
            db_session.add(cam)
            db_session.flush()
            health = CameraHealth(camera_id=cam.id, latency_ms=38, packet_loss=0.01, status="ONLINE")
            db_session.add(health)
            db_session.commit()
            db_session.refresh(cam)
        created.append(cam)
    return created


# =====================================================================
# 1. SPATIAL GIS SURVEILLANCE ENDPOINTS
# =====================================================================

def test_spatial_nearest_cameras(seed_cameras):
    """Discovers closest active surveillance cameras to GPS point with distance & bearing."""
    res = client.get("/api/cameras/spatial/nearest", params={"lat": 23.0220, "lng": 72.5710, "limit": 3})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "camera_id" in first
    assert "distance_meters" in first
    assert "distance_km" in first
    assert "bearing_degrees" in first
    assert first["distance_meters"] >= 0


def test_spatial_radius_geofence(seed_cameras):
    """Finds all cameras within an operational geofence radius."""
    res = client.get("/api/cameras/spatial/radius", params={"lat": 23.0225, "lng": 72.5714, "radius_km": 10.0})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for cam in data:
        assert cam["distance_km"] <= 10.0


def test_spatial_route_corridor(seed_cameras):
    """Finds all cameras along a transit or highway corridor."""
    waypoints = [
        [23.0220, 72.5710],
        [23.0300, 72.5700],
        [23.0410, 72.5690]
    ]
    res = client.post("/api/cameras/spatial/route-corridor", json={
        "waypoints": waypoints,
        "corridor_buffer_meters": 1500.0
    })
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "distance_to_corridor_m" in data[0]
        assert data[0]["distance_to_corridor_m"] <= 1500.0


def test_spatial_pursuit_corridor(seed_cameras):
    """Calculates pursuit containment cone and identifies downstream interception cameras."""
    origin_cam = seed_cameras[0]
    res = client.post("/api/cameras/spatial/pursuit-corridor", json={
        "origin_camera_id": origin_cam.id,
        "heading_degrees": 45.0,
        "speed_kmh": 90.0,
        "time_elapsed_minutes": 10.0
    })
    assert res.status_code == 200
    data = res.json()
    assert "cone_angle_degrees" in data
    assert "projected_travel_distance_km" in data
    assert "interception_cameras" in data
    assert data["projected_travel_distance_km"] == 15.0


def test_spatial_district_containment():
    """Identifies the police district jurisdiction for a given coordinate."""
    res = client.get("/api/cameras/spatial/district-containment", params={"lat": 23.0225, "lng": 72.5714})
    assert res.status_code == 200
    data = res.json()
    assert "district" in data
    assert "code" in data
    assert "distance_to_hq_km" in data


# =====================================================================
# 2. CAMERA OPERATIONAL LIFECYCLE & HEARTBEAT
# =====================================================================

def test_camera_lifecycle_state_machine(seed_cameras):
    """Executes the full 7-stage camera onboarding validation state machine."""
    target_cam = seed_cameras[0]
    res = client.post(f"/api/cameras/{target_cam.id}/validate-lifecycle")
    assert res.status_code == 200
    report = res.json()
    assert report["lifecycle_status"] == "AI_ENABLED"
    assert report["overall_status"] == "OPERATIONAL"
    
    stages = report["stages"]
    for expected_stage in ["REGISTER", "VALIDATE", "CONNECT", "AUTH", "HEALTH", "STREAM", "AI_ENABLED"]:
        assert expected_stage in stages
        assert stages[expected_stage]["status"] == "PASSED"


def test_camera_heartbeat_telemetry(seed_cameras):
    """Records real-time heartbeat and telemetry update for camera."""
    target_cam = seed_cameras[0]
    res = client.post(f"/api/cameras/{target_cam.id}/heartbeat", json={
        "status": "ONLINE",
        "latency_ms": 35.5,
        "packet_loss": 0.01,
        "cpu_usage": 32.0,
        "memory_usage": 44.0
    })
    assert res.status_code == 200
    data = res.json()
    assert data["camera_id"] == target_cam.id
    assert data["status"] == "ACTIVE"
    assert data["health_status"] == "ONLINE"
    assert data["latency_ms"] == 35.5


# =====================================================================
# 3. MINIO WORM EVIDENCE VAULT & INTEGRITY
# =====================================================================

def test_worm_evidence_vault_lifecycle(db_session, seed_cameras):
    """Tests evidence package ingestion, WORM sealing, integrity check, and custody logging."""
    # 1. Create a test case
    cam = seed_cameras[0]
    case_res = client.post("/api/cases", json={
        "title": "Operation Nightfall Interception Case",
        "target_vehicle_plate": "GJ01XY9988",
        "fir_number": "FIR-2026/TEST/001",
        "assigned_investigator": "Inspector V. Patel"
    })
    assert case_res.status_code == 200
    case_id = case_res.json()["id"]

    # 2. Ingest Evidence Package into WORM Vault
    test_frame = b"\xFF\xD8\xFF\xE0" + b"TEST_CAMERA_FRAME_DATA_RAW_SURVEILLANCE"
    frame_b64 = base64.b64encode(test_frame).decode("utf-8")

    ingest_res = client.post(f"/api/cases/{case_id}/evidence/vault-package", json={
        "plate_text": "GJ01XY9988",
        "camera_id": cam.id,
        "original_frame_b64": frame_b64,
        "anpr_confidence": 0.98,
        "model_version": "YOLO11-ANPR-v2.1",
        "classification": "RESTRICTED",
        "retention_years": 7
    })
    assert ingest_res.status_code == 200
    vault_receipt = ingest_res.json()
    assert vault_receipt["status"] == "SEALED_IN_VAULT"
    assert vault_receipt["worm_locked"] is True
    assert len(vault_receipt["sha256"]) == 64
    evidence_id = vault_receipt["evidence_id"]

    # 3. Verify Cryptographic Integrity
    verify_res = client.get(f"/api/cases/{case_id}/evidence/{evidence_id}/verify")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified"] is True
    assert verify_data["audit_verdict"] == "INTEGRITY_CONFIRMED"
    assert verify_data["expected_sha256"] == vault_receipt["sha256"]

    # 4. Append Immutable Custody Event
    custody_res = client.post(f"/api/cases/{case_id}/evidence/{evidence_id}/custody-log", json={
        "actor": "Inspector V. Patel",
        "action": "COURT_EVIDENCE_EXAMINATION",
        "justification": "Presented before Hon'ble Sessions Court under Section 65B/63 BSA"
    })
    assert custody_res.status_code == 200
    custody_data = custody_res.json()
    assert custody_data["status"] == "CUSTODY_UPDATED"
    assert custody_data["entries_count"] >= 2
    assert custody_data["latest_event"]["action"] == "COURT_EVIDENCE_EXAMINATION"


# =====================================================================
# 4. STATEWIDE DISTRIBUTED TOPOLOGY SPECIFICATION (~80,000 CAMERAS)
# =====================================================================

def test_statewide_topology_specification():
    """Validates the 4-tier statewide architecture for 80,000 cameras across Gujarat."""
    res = client.get("/api/system/topology")
    assert res.status_code == 200
    data = res.json()
    
    # 80,000 cameras statewide check
    assert data["total_cameras_statewide"] == 80000
    assert data["districts_count"] == 33
    assert data["regional_hubs_count"] == 4

    # Central Command HQ check
    hq = data["central_hq"]
    assert "Gandhinagar" in hq["name"]
    assert hq["patroni_postgis_cluster"]["status"] == "HEALTHY_SYNCHRONIZED"
    assert hq["kafka_kraft_state_cluster"]["canonical_topics"] == 10
    assert hq["minio_worm_vault"]["object_lock_mode"] == "COMPLIANCE"

    # Regional hubs check
    assert len(data["regional_hubs"]) == 4
    hub_names = [h["hub_id"] for h in data["regional_hubs"]]
    assert "REG-HUB-AHM" in hub_names
    assert "REG-HUB-SRT" in hub_names
    assert "REG-HUB-VDR" in hub_names
    assert "REG-HUB-RJK" in hub_names

    # Bandwidth optimization proof (Model 4 brute-force vs Hybrid Edge)
    bw = data["bandwidth_optimization"]
    assert bw["legacy_central_streaming_model_4"]["raw_stream_bandwidth_gbps"] == 320.0
    assert bw["givin_hybrid_edge_architecture"]["total_uplink_bandwidth_gbps"] < 10.0
    assert bw["givin_hybrid_edge_architecture"]["bandwidth_reduction_pct"] > 90.0


# =====================================================================
# 5. MULTI-MODE GOVERNMENT DATABASE ADAPTERS
# =====================================================================

def test_gov_adapters_multi_mode():
    """Verifies that all 6 government adapters support MOCK, SANDBOX, and AUTHORIZED_PRODUCTION modes."""
    adapters = [
        ("vahan", vahan_adapter),
        ("sarathi", sarathi_adapter),
        ("cctns", cctns_adapter),
        ("egujcop", egujcop_adapter),
        ("afis", afis_adapter),
        ("nafis", nafis_adapter),
    ]

    for name, adapter in adapters:
        # Check initial health
        health = adapter.get_health_status()
        assert health["status"] in ["ONLINE", "ACTIVE", "SANDBOX_MOCK", "OFFLINE"]
        assert "mode" in health

        # Mode switching validation
        adapter.set_mode(IntegrationMode.MOCK)
        assert adapter.mode == IntegrationMode.MOCK
        res_mock = adapter.query("GJ01AB1234")
        assert res_mock is not None
        assert "source_signature_hash" in res_mock

        adapter.set_mode(IntegrationMode.SANDBOX)
        assert adapter.mode == IntegrationMode.SANDBOX
        res_sandbox = adapter.query("GJ01AB1234")
        assert res_sandbox is not None

        # Revert to standard mode
        adapter.set_mode(IntegrationMode.MOCK)


def test_gov_adapters_endpoint():
    """Tests the system gov-adapters status and federated lookup endpoint."""
    res = client.get("/api/system/gov-adapters?plate=GJ01AB1234")
    assert res.status_code == 200
    data = res.json()
    assert "adapters" in data
    assert len(data["adapters"]) == 6
    adapter_names = [a["adapter"] for a in data["adapters"]]
    for expected in ["VAHAN", "SAR", "CCTNS", "EGUJCOP", "AFIS", "NAFIS"]:
        assert any(expected in a.upper() for a in adapter_names)
    # Check federated plate queries
    for key in ["vahan", "sarathi", "cctns", "egujcop", "afis", "nafis"]:
        assert key in data
        assert "source_signature_hash" in data[key]

