"""
Test Suite for Phase C: Cross-Camera Intelligence & Spatial-Temporal Analytics
Verifies:
1. CameraNetworkGraph topology generation, corridor classification, and downstream camera ranking.
2. TravelAnomalyEngine detecting teleportation / cloned license plates and auto-raising CRITICAL alerts.
3. ContainmentService generating directional isochrone polygons and tactical intercept chokepoints.
4. FastAPI endpoints (/api/tracking/containment, /anomalies, /cloned-plates, /camera-graph).
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, VehicleSighting, Alert
from backend.app.services.camera_graph import camera_network_graph
from backend.app.services.anomaly_engine import travel_anomaly_engine
from backend.app.services.containment import containment_service

client = TestClient(app)

def test_camera_network_graph():
    """Verify camera network spatial graph generates valid topology and downstream predictions."""
    db = SessionLocal()
    try:
        summary = camera_network_graph.get_topology_summary(db)
        assert summary["total_cameras"] > 0
        assert summary["total_corridor_edges"] > 0
        assert len(summary["active_corridors"]) > 0

        # Test downstream camera ranking from first active camera
        first_cam = db.query(Camera).filter(Camera.status == "ACTIVE").first()
        assert first_cam is not None

        # Predict downstream cameras heading North-East (45 deg)
        downstream = camera_network_graph.get_downstream_cameras(
            db=db,
            current_camera_id=first_cam.id,
            current_heading_deg=45.0,
            top_k=3
        )
        assert len(downstream) > 0
        cand = downstream[0]
        assert "camera_name" in cand
        assert cand["distance_km"] > 0
        assert cand["typical_travel_time_min"] > 0
        assert cand["confidence_score"] > 0
        print(f"[PASS] test_camera_network_graph passed ({summary['total_corridor_edges']} edges across corridors: {summary['active_corridors'][:2]}).")
    finally:
        db.close()

def test_cloned_plate_detection_and_alert():
    """
    Verify TravelAnomalyEngine detects teleportation / duplicate cloned plates
    and automatically escalates to a CRITICAL Alert in the command center.
    """
    db = SessionLocal()
    try:
        # Find two cameras far apart (> 50 km)
        cams = db.query(Camera).filter(Camera.status == "ACTIVE").all()
        cam_a = cams[0]
        cam_b = None
        for c in cams[1:]:
            from backend.app.services.vehicle_tracker import haversine_distance_km
            if haversine_distance_km(cam_a.lat, cam_a.lng, c.lat, c.lng) > 40.0:
                cam_b = c
                break

        assert cam_b is not None, "Could not find two cameras > 40 km apart for cloned plate test."

        test_plate = f"GJ01CL{uuid.uuid4().hex[:4].upper()}"
        now = datetime.now(timezone.utc)

        # Sighting 1: Camera A at T = 0
        s1 = VehicleSighting(
            id=f"sight-test-a-{uuid.uuid4().hex[:8]}",
            camera_id=cam_a.id,
            plate_text=test_plate,
            normalized_plate=test_plate,
            confidence=0.95,
            speed_kmh=80.0,
            vehicle_type="Car",
            vehicle_color="White",
            timestamp=now - timedelta(minutes=4)
        )
        # Sighting 2: Camera B at T = +4 minutes (Impossible distance in 4 mins)
        s2 = VehicleSighting(
            id=f"sight-test-b-{uuid.uuid4().hex[:8]}",
            camera_id=cam_b.id,
            plate_text=test_plate,
            normalized_plate=test_plate,
            confidence=0.96,
            speed_kmh=85.0,
            vehicle_type="Car",
            vehicle_color="White",
            timestamp=now
        )
        db.add(s1)
        db.add(s2)
        db.commit()

        # Evaluate anomalies
        anomalies = travel_anomaly_engine.evaluate_sightings_for_plate(
            db=db,
            plate_number=test_plate,
            auto_raise_alert=True
        )

        assert len(anomalies) >= 1
        cloned_anom = [a for a in anomalies if a["anomaly_type"] == "CLONED_PLATE"][0]
        assert cloned_anom["severity"] == "CRITICAL"
        assert cloned_anom["implied_speed_kmh"] > 180.0
        assert cloned_anom["alert_raised"] is True

        # Verify Alert was persisted in database
        alert = db.query(Alert).filter(Alert.plate_text == test_plate).first()
        assert alert is not None
        assert alert.risk_level == "CRITICAL"
        assert "CLONED_PLATE" in alert.remarks

        print(f"[PASS] test_cloned_plate_detection_and_alert passed (Flagged speed: {cloned_anom['implied_speed_kmh']} km/h, Alert: {alert.alert_uid}).")
    finally:
        db.close()

def test_pursuit_containment_perimeter():
    """Verify ContainmentService computes 5, 10, 15 min directional isochrones and checkpoints."""
    db = SessionLocal()
    try:
        # Find any vehicle with recorded sightings in DB
        sighting = db.query(VehicleSighting).order_by(VehicleSighting.timestamp.desc()).first()
        assert sighting is not None

        containment = containment_service.compute_containment(db, sighting.plate_text)
        assert containment is not None
        assert containment["plate_number"] == sighting.plate_text
        assert len(containment["isochrones"]) == 3
        
        # Verify 5, 10, 15 minute rings
        for iso in containment["isochrones"]:
            assert iso["minutes"] in (5, 10, 15)
            assert iso["radius_km"] > 0
            assert len(iso["polygon"]) >= 12 # Has polygon vertices

        assert containment["enclosed_camera_count"] >= 1
        assert len(containment["intercept_checkpoints"]) >= 1
        assert "Tactical Action" in containment["tactical_recommendation"]

        top_cp = containment["intercept_checkpoints"][0]
        print(f"[PASS] test_pursuit_containment_perimeter passed (Enclosed: {containment['enclosed_camera_count']} cams, Top Intercept: {top_cp['checkpoint_name']} @ {top_cp['eta_sec']}s).")
    finally:
        db.close()

def test_cross_camera_api_endpoints():
    """Verify HTTP API endpoints for Phase C intelligence."""
    # 1. Camera Graph
    res = client.get("/api/tracking/camera-graph")
    assert res.status_code == 200
    data = res.json()
    assert data["total_cameras"] > 0
    assert "edges" in data

    # 2. Cloned plates
    res = client.get("/api/tracking/cloned-plates")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 3. Containment endpoint for existing vehicle
    db = SessionLocal()
    try:
        sighting = db.query(VehicleSighting).order_by(VehicleSighting.timestamp.desc()).first()
        plate = sighting.plate_text if sighting else "GJ01AB1234"
    finally:
        db.close()

    res = client.get(f"/api/tracking/containment/{plate}")
    assert res.status_code == 200
    c_data = res.json()
    assert c_data["plate_number"] == plate
    assert len(c_data["isochrones"]) == 3

    # 4. Anomalies endpoint
    res = client.get(f"/api/tracking/anomalies/{plate}")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    print("[PASS] test_cross_camera_api_endpoints passed (All 4 Phase C endpoints verified 200 OK).")

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING PHASE C CROSS-CAMERA INTELLIGENCE VERIFICATION SUITE   ")
    print("==================================================================")
    test_camera_network_graph()
    test_cloned_plate_detection_and_alert()
    test_pursuit_containment_perimeter()
    test_cross_camera_api_endpoints()
    print("\n*** ALL PHASE C CROSS-CAMERA TESTS PASSED WITH 100% SUCCESS!\n")
