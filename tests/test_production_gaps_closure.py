"""
GIVIN Production Gap Closure & Verification Test Suite.
Verifies the P0, P1, and P2 operational guarantees:
1. Explicit Source Provenance across all events and sightings.
2. Complete 7-state Alert Lifecycle with mandatory officer justification for FALSE_POSITIVE and ESCALATED.
3. Spatiotemporal Anomaly Engine with SUSPICIOUS_MOVEMENT classification and multi-factor diagnostics.
4. Camera Stream Lifecycle State Machine across all operational states.
5. Byte-Level Evidence Vault SHA-256 Verification & WORM Immutability.
6. Government Integration Adapters Fail-Closed Enforcement.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import (
    Camera, VehicleSighting, Alert, Watchlist, AuditLog, Department
)
from backend.app.services.anomaly_engine import TravelAnomalyEngine
from backend.app.services.evidence_vault import evidence_vault
from backend.app.services.gov_adapters.base import IntegrationMode, ReadinessState
from backend.app.services.gov_adapters.vahan_adapter import VAHANAdapter
from backend.app.services.gov_adapters.sarathi_adapter import SARATHIAdapter
from backend.app.services.gov_adapters.egujcop_adapter import EGujCopAdapter

client = TestClient(app)


def test_source_provenance_enforcement():
    """Verify that sightings and alerts record explicit provenance."""
    db = SessionLocal()
    try:
        cam = db.query(Camera).first()
        assert cam is not None, "Camera fixture must be present"

        # Create sighting with explicit provenance
        sighting = VehicleSighting(
            plate_text="GJ01AB9999",
            normalized_plate="GJ01AB9999",
            camera_id=cam.id,
            timestamp=datetime.now(timezone.utc),
            confidence=0.97,
            vehicle_type="Car",
            vehicle_color="Silver",
            speed_kmh=52.0,
            direction="Southbound",
            processing_provenance="PHYSICAL_STREAM"
        )
        db.add(sighting)
        db.commit()
        db.refresh(sighting)

        assert sighting.processing_provenance == "PHYSICAL_STREAM"

        # Create alert with explicit provenance
        import uuid
        alert = Alert(
            alert_uid=f"ALT-PROV-{uuid.uuid4().hex[:8].upper()}",
            sighting_id=sighting.id,
            camera_id=cam.id,
            plate_text="GJ01AB9999",
            risk_level="HIGH",
            status="NEW",
            remarks="Provenance Verification Alert",
            processing_provenance="SIMULATION"
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        assert alert.processing_provenance == "SIMULATION"
    finally:
        db.close()


def test_7_state_alert_lifecycle_and_officer_review():
    """Verify all 7 alert lifecycle states, officer review reasons, and validation."""
    db = SessionLocal()
    try:
        cam = db.query(Camera).first()
        sighting = db.query(VehicleSighting).first()

        import uuid
        alert = Alert(
            alert_uid=f"ALT-LIFECYCLE-{uuid.uuid4().hex[:8].upper()}",
            sighting_id=sighting.id,
            camera_id=cam.id,
            plate_text="GJ01CD5555",
            risk_level="HIGH",
            status="NEW",
            remarks="Lifecycle state transition test"
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # 1. Transition to ACKNOWLEDGED
        resp = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "ACKNOWLEDGED",
                "operator_name": "Insp. V. Patel",
                "remarks": "Control room acknowledged alert."
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ACKNOWLEDGED"
        assert data["acknowledged_by"] == "Insp. V. Patel"

        # 2. Transition to UNDER_REVIEW
        resp = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "UNDER_REVIEW",
                "operator_name": "Insp. V. Patel",
                "review_reason": "Verifying high-speed ANPR crop against ANPR corridor trajectory."
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "UNDER_REVIEW"

        # 3. Transition to DISPATCHED
        resp = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "DISPATCHED",
                "operator_name": "Insp. V. Patel",
                "dispatched_unit": "PCR Van 07 - SG Highway Intercept",
                "remarks": "Intercept squad dispatched to SG Highway Toll."
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DISPATCHED"
        assert "PCR Van 07" in resp.json()["dispatched_unit"]

        # 4. Attempt FALSE_POSITIVE without justification (must fail)
        resp_fail = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "FALSE_POSITIVE",
                "operator_name": "Insp. V. Patel",
                "remarks": "",
                "review_reason": ""
            }
        )
        assert resp_fail.status_code == 400
        assert "Officer remarks or review_reason are mandatory" in resp_fail.json()["detail"]

        # 5. Successfully mark FALSE_POSITIVE with justification
        resp_fp = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "FALSE_POSITIVE",
                "operator_name": "Insp. V. Patel",
                "review_reason": "Plate character '8' was misread by OCR as 'B'; vehicle owner does not match hotlist make."
            }
        )
        assert resp_fp.status_code == 200
        assert resp_fp.json()["status"] == "FALSE_POSITIVE"

        # 6. Verify ESCALATED transition with mandatory justification
        resp_esc = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "ESCALATED",
                "operator_name": "Superintendent R. Sharma",
                "review_reason": "Suspect vehicle sighted near vital state infrastructure; statewide alert broadcast."
            }
        )
        assert resp_esc.status_code == 200
        assert resp_esc.json()["status"] == "ESCALATED"

        # 7. Final RESOLVED transition
        resp_res = client.post(
            f"/api/alerts/{alert.id}/action",
            json={
                "status": "RESOLVED",
                "operator_name": "Insp. V. Patel",
                "remarks": "Suspect intercepted and verified at designated checkpoint."
            }
        )
        assert resp_res.status_code == 200
        assert resp_res.json()["status"] == "RESOLVED"

        # 8. Verify audit logs recorded every transition
        audits = db.query(AuditLog).filter(AuditLog.resource == f"ALERT:{alert.alert_uid}").all()
        assert len(audits) >= 6
    finally:
        db.close()


def test_spatiotemporal_anomaly_suspicious_movement_standard():
    """Verify anomaly engine flags SUSPICIOUS_MOVEMENT with multi-factor diagnostics."""
    db = SessionLocal()
    try:
        cams = db.query(Camera).limit(2).all()
        assert len(cams) >= 2, "At least two cameras required for cross-camera test"
        cam_a, cam_b = cams[0], cams[1]

        now = datetime.now(timezone.utc)
        test_plate = "GJ01SM9999"

        # Create two sightings with impossible ground speed (e.g. 100km in 1 minute)
        s1 = VehicleSighting(
            plate_text=test_plate,
            normalized_plate=test_plate,
            camera_id=cam_a.id,
            timestamp=now - timedelta(minutes=1),
            confidence=0.95,
            vehicle_type="Car",
            vehicle_color="White",
            speed_kmh=60.0,
            direction="Northbound",
            processing_provenance="SIMULATION"
        )
        s2 = VehicleSighting(
            plate_text=test_plate,
            normalized_plate=test_plate,
            camera_id=cam_b.id,
            timestamp=now,
            confidence=0.95,
            vehicle_type="Car",
            vehicle_color="White",
            speed_kmh=60.0,
            direction="Northbound",
            processing_provenance="SIMULATION"
        )
        db.add_all([s1, s2])
        db.commit()

        anomalies = TravelAnomalyEngine.evaluate_sightings_for_plate(
            db=db,
            plate_number=test_plate,
            auto_raise_alert=True
        )

        assert len(anomalies) >= 1
        anom = anomalies[0]
        # Verify conservative classification
        assert anom.get("investigative_classification") == "SUSPICIOUS_MOVEMENT"
        assert "potential_causes" in anom
        assert "likely cloned plate" in anom["potential_causes"]
        assert "OCR error" in anom["potential_causes"]
        assert "timestamp error" in anom["potential_causes"]
        assert "evidentiary_disclaimer" in anom
    finally:
        db.close()


def test_camera_stream_lifecycle_states():
    """Verify camera lifecycle transitions and heartbeat updates across valid states."""
    db = SessionLocal()
    try:
        cam = db.query(Camera).first()
        assert cam is not None

        # Test heartbeat with DEGRADED state
        resp = client.post(
            f"/api/cameras/{cam.id}/heartbeat",
            json={
                "status": "DEGRADED",
                "latency_ms": 120.0,
                "packet_loss": 0.08,
                "cpu_usage": 88.0,
                "memory_usage": 72.0
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DEGRADED"

        # Test heartbeat with OFFLINE state
        resp = client.post(
            f"/api/cameras/{cam.id}/heartbeat",
            json={
                "status": "OFFLINE",
                "latency_ms": None,
                "packet_loss": 1.0,
                "cpu_usage": 0.0,
                "memory_usage": 0.0
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "OFFLINE"

        # Restore to ACTIVE / ONLINE
        resp = client.post(
            f"/api/cameras/{cam.id}/heartbeat",
            json={
                "status": "ONLINE",
                "latency_ms": 32.0,
                "packet_loss": 0.0,
                "cpu_usage": 22.0,
                "memory_usage": 35.0
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"
    finally:
        db.close()


def test_evidence_vault_exact_byte_verification():
    """Verify SHA-256 byte-level verification, WORM immutability, and tamper detection."""
    from backend.app.services.storage.base import WORMImmutableViolationError
    test_case_id = f"CASE-VERIF-{datetime.now().strftime('%H%M%S')}"
    test_frame = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00GIVIN_GENUINE_FRAME_BYTES_9999"

    pkg = evidence_vault.store_evidence_package(
        case_id=test_case_id,
        camera_id="CAM-AHM-01",
        plate_text="GJ01AB1234",
        original_frame_bytes=test_frame,
        created_by="TEST_OFFICER",
        classification="CONFIDENTIAL"
    )

    evid_id = pkg["evidence_id"]

    # 1. Verify genuine bytes
    verif = evidence_vault.verify_evidence_integrity(case_id=test_case_id, evidence_id=evid_id)
    assert verif["verified"] is True
    assert verif["audit_verdict"] == "INTEGRITY_CONFIRMED"
    assert verif["computed_sha256"] == verif["expected_sha256"]

    # 2. Verify WORM storage blocks direct overwrite
    tampered_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00GIVIN_TAMPERED_FRAME_BYTES_MALICIOUS"
    with pytest.raises(WORMImmutableViolationError):
        evidence_vault.storage.put_object(
            evidence_vault.BUCKET_NAME,
            f"evidence/{test_case_id}/{evid_id}/original_frame.jpg",
            tampered_bytes,
            "image/jpeg"
        )

    # 3. Simulate low-level physical disk tampering behind the WORM storage engine
    file_path = evidence_vault.storage._resolve_path(
        evidence_vault.BUCKET_NAME,
        f"evidence/{test_case_id}/{evid_id}/original_frame.jpg"
    )
    with open(file_path, "wb") as f:
        f.write(tampered_bytes)

    # 4. Re-verify: must catch tampering by computing SHA-256 over physical stored bytes
    verif_tampered = evidence_vault.verify_evidence_integrity(case_id=test_case_id, evidence_id=evid_id)
    assert verif_tampered["verified"] is False
    assert verif_tampered["audit_verdict"] == "TAMPER_DETECTED"
    assert verif_tampered["computed_sha256"] != verif_tampered["expected_sha256"]


def test_gov_adapters_fail_closed_in_production_mode():
    vahan = VAHANAdapter()
    vahan.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
    sarathi = SARATHIAdapter()
    sarathi.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
    egujcop = EGujCopAdapter()
    egujcop.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)

    # In clean or test environments where mTLS and GSWAN VPN are absent,
    # queries MUST raise RuntimeError and fail closed.
    for adapter in [vahan, sarathi, egujcop]:
        with pytest.raises(RuntimeError) as exc_info:
            adapter.query("GJ01AB1234")
        assert "AUTHORIZED_PRODUCTION refuses to operate" in str(exc_info.value)

        # Check readiness state correctly reports requirement
        readiness = adapter.get_readiness_state()
        assert readiness["readiness"] in (
            ReadinessState.PRODUCTION_CREDENTIALS_REQUIRED.value,
            ReadinessState.NETWORK_ACCESS_REQUIRED.value,
            ReadinessState.GOVERNMENT_AUTHORIZATION_REQUIRED.value
        )
