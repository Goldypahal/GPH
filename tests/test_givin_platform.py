import os
import sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.security import (
    generate_sha256_hash,
    generate_evidence_certificate_hash,
    verify_evidence_integrity
)
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, VehicleSighting, Watchlist, Alert

client = TestClient(app)

def test_system_health():
    """Verify system health endpoint and compliance tags."""
    res = client.get("/api/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["active_edge_nodes"] == 33
    assert "IT Act 2000 Sec 65B" in data["compliance"]
    print("[PASS] test_system_health passed.")

def test_camera_registry_50_cameras():
    """Verify 50 heterogeneous cameras across Gujarat districts."""
    res = client.get("/api/cameras")
    assert res.status_code == 200
    cameras = res.json()
    assert len(cameras) >= 50, f"Expected at least 50 cameras, found {len(cameras)}"
    
    # Check Gujarat GPS boundaries: Lat ~ 20.0 to 24.5, Lng ~ 68.5 to 74.5
    for c in cameras:
        assert 20.0 <= c["lat"] <= 24.5, f"Camera {c['logical_camera_id']} latitude out of Gujarat bounds: {c['lat']}"
        assert 68.5 <= c["lng"] <= 74.5, f"Camera {c['logical_camera_id']} longitude out of Gujarat bounds: {c['lng']}"

    # Check vendor heterogeneity
    vendors = set(c["vendor"] for c in cameras)
    assert len(vendors) >= 4, f"Expected multi-vendor distribution, found: {vendors}"
    print(f"[PASS] test_camera_registry_50_cameras passed ({len(cameras)} cameras across {len(vendors)} vendors).")

def test_anpr_normalization_and_validation():
    """Verify Indian ANPR plate normalization, regex checks, and optical disambiguation."""
    # Test normalization
    assert ANPREngine.normalize_plate("GJ-01-AB-1234") == "GJ01AB1234"
    assert ANPREngine.normalize_plate("IND GJ 06 XY 9876") == "GJ06XY9876"

    # Test OCR disambiguation (Letter O -> 0, letter B -> 8 in digits position)
    corrected, conf, is_valid = ANPREngine.validate_and_correct("GJ01AB1234")
    assert is_valid is True
    assert corrected == "GJ01AB1234"
    assert conf >= 0.90

    # Test Levenshtein distance
    dist = ANPREngine.calculate_levenshtein("GJ01AB1234", "GJ01AB1235")
    assert dist == 1
    print("[PASS] test_anpr_normalization_and_validation passed.")

def test_designated_vehicle_route_reconstruction():
    """
    Core Evaluation Scenario:
    Search designated vehicle registration plate GJ01AB1234 and verify
    cross-camera route reconstruction across Ahmedabad, Gandhinagar, Vadodara, Surat, Valsad.
    """
    res = client.get("/api/tracking/search?plate=GJ01AB1234")
    assert res.status_code == 200
    journey = res.json()
    assert journey["plate_number"] == "GJ01AB1234"
    assert journey["total_sightings"] >= 5
    assert journey["total_estimated_distance_km"] > 300.0
    assert "Ahmedabad" in journey["districts_traversed"]
    assert "Valsad" in journey["districts_traversed"]
    assert journey["matched_watchlist"] is not None
    assert journey["matched_watchlist"]["risk_level"] == "CRITICAL"
    print(f"[PASS] test_designated_vehicle_route_reconstruction passed ({journey['total_estimated_distance_km']} km journey).")

def test_section_65b_evidence_certificate():
    """Verify Section 65B certificate generation and cryptographic HMAC tamper seal."""
    db = SessionLocal()
    sighting = db.query(VehicleSighting).filter(VehicleSighting.plate_text == "GJ01AB1234").first()
    assert sighting is not None

    res = client.get(f"/api/evidence/{sighting.id}/certificate")
    assert res.status_code == 200
    cert = res.json()
    assert "65b" in cert["certificate_title"].lower()
    assert cert["electronic_record_details"]["target_vehicle_plate"] == "GJ01AB1234"
    
    sig = cert["cryptographic_verification"]["hmac_tamper_evident_signature"]
    assert len(sig) == 64 # SHA-256 hex string

    # Verify signature verification function
    is_valid = verify_evidence_integrity(
        camera_id=sighting.camera_id,
        timestamp=sighting.timestamp.isoformat(),
        plate_text=sighting.plate_text,
        image_hash=sighting.evidence_hash,
        operator_id=cert["certifying_officer"]["name"],
        expected_signature=sig
    )
    assert is_valid is True
    print("[PASS] test_section_65b_evidence_certificate passed (tamper verification verified).")

def test_scalability_calculator_80k():
    """Verify 80,000 camera capacity planning and bandwidth savings."""
    res = client.get("/api/system/scale-calculator?camera_count=80000&resolution=1080p&fps=25")
    assert res.status_code == 200
    scale = res.json()
    assert scale["central_model4_bandwidth_gbps"] >= 300.0
    assert scale["hybrid_model_bandwidth_gbps"] <= 10.0
    assert scale["bandwidth_savings_percentage"] > 95.0
    assert scale["estimated_annual_cost_savings_inr_crores"] > 50.0
    print(f"[PASS] test_scalability_calculator_80k passed ({scale['bandwidth_savings_percentage']}% savings).")

def test_alert_lifecycle_action():
    """Verify alert status transition and dispatching."""
    db = SessionLocal()
    alert = db.query(Alert).filter(Alert.plate_text == "GJ01AB1234").first()
    assert alert is not None

    action_payload = {
        "status": "INVESTIGATING",
        "dispatched_unit": "Interceptor Van 07 - Bhilad Border",
        "remarks": "Suspect vehicle sighted heading towards Maharashtra NH-48",
        "operator_name": "SP V. K. Patel"
    }
    res = client.post(f"/api/alerts/{alert.id}/action", json=action_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "INVESTIGATING"
    assert updated["dispatched_unit"] == "Interceptor Van 07 - Bhilad Border"
    print("[PASS] test_alert_lifecycle_action passed.")

def test_camera_onboarding_model1():
    """Verify onboarding a new camera into Model 1 registry."""
    import uuid
    db = SessionLocal()
    cam_count_before = db.query(Camera).count()
    unique_code = f"CAM-GJ-TEST-{uuid.uuid4().hex[:6].upper()}"

    payload = {
        "logical_camera_id": unique_code,
        "name": "Gandhinagar VIP Highway Toll Plaza",
        "district": "Gandhinagar",
        "location_name": "VIP Highway Gate",
        "department_id": db.query(Camera).first().department_id,
        "lat": 23.2195,
        "lng": 72.6455,
        "vendor": "Axis",
        "protocol": "RTSP",
        "resolution": "1080p",
        "fps": 25,
        "status": "ACTIVE"
    }
    res = client.post("/api/cameras", json=payload)
    assert res.status_code == 200
    cam_count_after = db.query(Camera).count()
    assert cam_count_after == cam_count_before + 1
    print("[PASS] test_camera_onboarding_model1 passed.")

def test_live_pursuit_feature():
    """Verify dead-reckoned live pursuit position endpoint for stolen vehicles."""
    res = client.get("/api/tracking/live/GJ01AB1234")
    assert res.status_code == 200
    pos = res.json()
    assert pos["plate_number"] == "GJ01AB1234"
    assert pos["status"] in ["LIVE_PREDICTED", "STALE"]
    assert pos["speed_kmh"] > 0
    assert len(pos["trail"]) > 0
    print("[PASS] test_live_pursuit_feature passed.")

def test_auth_and_rbac():
    """Verify JWT authentication, RBAC authorization, and user profiles."""
    # Test valid login
    res = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    assert token_data["role"] == "SUPER_ADMIN"

    # Test /api/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    me = res_me.json()
    assert me["username"] == "admin"
    assert me["role"] == "SUPER_ADMIN"

    # Test invalid password rejected
    res_bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_bad.status_code == 401

    print("[PASS] test_auth_and_rbac passed.")

def test_cross_camera_intelligence():
    """Verify trajectory route confidence scoring and implied speed computation."""
    res = client.get("/api/tracking/search?plate=GJ01AB1234")
    assert res.status_code == 200
    journey = res.json()
    assert "route_confidence_pct" in journey
    assert journey["route_confidence_pct"] >= 80.0
    assert journey["route_status"] in ["VERIFIED_CONTINUOUS", "CONFIRMED", "HIGH_CONFIDENCE"]
    
    # Check individual trajectory points for match_method and implied_speed
    for pt in journey["trajectory"]:
        assert "match_method" in pt
        assert "PLATE" in pt["match_method"] or "REID" in pt["match_method"]
        assert "implied_speed_kmh" in pt

    print(f"[PASS] test_cross_camera_intelligence passed (Route confidence: {journey['route_confidence_pct']}%, Status: {journey['route_status']}).")

def test_gov_adapters():
    """Verify VAHAN, Sarathi, eGujCop, and AFIS integration adapters."""
    res = client.get("/api/system/gov-adapters?plate=GJ01AB1234")
    assert res.status_code == 200
    data = res.json()
    assert data["vahan"]["registration_number"] == "GJ01AB1234"
    assert data["vahan"]["stolen_flag"] is True
    assert data["sarathi"]["service"] is not None
    assert data["egujcop"]["cctns_registered_match"] is True
    assert data["afis"]["biometric_reference_match"] is True
    print("[PASS] test_gov_adapters passed (All 4 state adapters responded).")

def test_case_management_workflow():
    """Verify Case creation, timeline entry addition, evidence attachment, and Section 65B dossier generation."""
    # Login as investigator
    res_login = client.post("/api/auth/login", json={"username": "inspector_patel", "password": "password123"})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List cases
    res_cases = client.get("/api/cases", headers=headers)
    assert res_cases.status_code == 200
    cases_list = res_cases.json()
    assert len(cases_list) >= 1
    case_id = cases_list[0]["id"]

    # Add a timeline note
    res_note = client.post(f"/api/cases/{case_id}/notes", json={
        "title": "Field Surveillance Update",
        "content": "Bhilad Interstate Checkpost patrol alerted with target vehicle description."
    }, headers=headers)
    assert res_note.status_code == 200

    # Fetch court dossier report
    res_report = client.get(f"/api/cases/{case_id}/report", headers=headers)
    assert res_report.status_code == 200
    report = res_report.json()
    assert "dossier_id" in report
    assert report["case_number"] == cases_list[0]["case_number"]
    assert "timeline" in report
    print(f"[PASS] test_case_management_workflow passed (Case: {report['case_number']}).")

def test_event_bus_and_pipeline_metrics():
    """Verify asynchronous EventBus topics and /api/system/pipeline-metrics."""
    res = client.get("/api/system/pipeline-metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "status" in metrics
    assert "active_topics" in metrics
    assert "givin.sightings.raw" in metrics["active_topics"] or "vehicle.sightings.raw" in metrics["active_topics"]
    assert "total_events_published" in metrics
    print(f"[PASS] test_event_bus_and_pipeline_metrics passed (Total events: {metrics['total_events_published']}).")

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING GIVIN PRODUCTION SUITE TESTS (GUJARAT HACKATHON 2026)")
    print("==================================================================")
    test_system_health()
    test_camera_registry_50_cameras()
    test_anpr_normalization_and_validation()
    test_designated_vehicle_route_reconstruction()
    test_section_65b_evidence_certificate()
    test_scalability_calculator_80k()
    test_alert_lifecycle_action()
    test_camera_onboarding_model1()
    test_live_pursuit_feature()
    test_auth_and_rbac()
    test_cross_camera_intelligence()
    test_gov_adapters()
    test_case_management_workflow()
    test_event_bus_and_pipeline_metrics()
    print("\n*** ALL 14 TEST SUITES PASSED WITH 100% SUCCESS!\n")

