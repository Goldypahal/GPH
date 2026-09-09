"""
Test Suite for Phase D: Enterprise RBAC, Multi-Department Security & Cryptographic Audit
Verifies:
1. 5-Tier Hierarchical Roles & granular JWT scopes.
2. Fine-grained permission enforcement (403 Forbidden when scope is missing).
3. Department data segregation & inter-department camera federation lifecycle (Request -> Approve -> Access).
4. Blockchain-style cryptographic audit hash chain integrity & tampering detection.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import User, Department, Camera, FederationAccessRequest, AuditLog
from backend.app.core.security import hash_password, create_access_token, ROLE_SCOPES
from backend.app.services.audit_service import audit_service
from backend.app.services.federation import federation_service

client = TestClient(app)

def test_roles_and_jwt_authentication():
    """Verify 5-tier role hierarchy and authenticated token generation."""
    res = client.get("/api/auth/roles")
    assert res.status_code == 200
    roles = res.json()
    role_names = [r["role"] for r in roles]
    assert "SUPER_ADMIN" in role_names
    assert "DGP_STATE_COMMISSIONER" in role_names
    assert "SP_DISTRICT_CHIEF" in role_names
    assert "FIELD_OFFICER" in role_names
    assert "AUDITOR_COMPLIANCE" in role_names

    # Test login with seed admin
    res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password123"}
    )
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "SUPER_ADMIN"
    print(f"[PASS] test_roles_and_jwt_authentication passed (5 tiers verified, JWT obtained for {token_data['username']}).")

def test_fine_grained_permission_denial():
    """Verify that an officer lacking required scope is denied with HTTP 403."""
    db = SessionLocal()
    try:
        # Create or fetch a test Field Officer
        field_user = db.query(User).filter(User.username == "test_field_constable").first()
        if not field_user:
            field_user = User(
                username="test_field_constable",
                email="field.constable@gujaratpolice.gov.in",
                full_name="Constable D. Rawat",
                role="FIELD_OFFICER",
                department_code="HOME_POLICE",
                jurisdiction_district="Ahmedabad",
                password_hash=hash_password("fieldpass123")
            )
            db.add(field_user)
            db.commit()

        # Token for Field Officer
        token = create_access_token({"sub": field_user.username, "role": field_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        # Field Officer trying to call an auditor-only endpoint (audit:verify)
        res = client.get("/api/auth/audit/verify-chain", headers=headers)
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]

        # Auditor user calling the same endpoint
        auditor_user = db.query(User).filter(User.role.in_(["AUDITOR", "AUDITOR_COMPLIANCE", "SUPER_ADMIN"])).first()
        auditor_token = create_access_token({"sub": auditor_user.username, "role": auditor_user.role})
        res2 = client.get("/api/auth/audit/verify-chain", headers={"Authorization": f"Bearer {auditor_token}"})
        assert res2.status_code == 200
        assert res2.json()["status"] in ("VERIFIED_INTACT", "TAMPERING_DETECTED")

        print("[PASS] test_fine_grained_permission_denial passed (Field Officer denied audit:verify with 403, Auditor allowed).")
    finally:
        db.close()

def test_department_camera_federation_lifecycle():
    """
    Verify inter-departmental data segregation:
    1. Foreign department camera with INTERNAL_ONLY is restricted.
    2. Federation request is submitted with legal FIR justification.
    3. State Command approves request.
    4. Access is granted.
    """
    db = SessionLocal()
    try:
        # Create test Civil Supplies Department & Internal Camera
        dept = db.query(Department).filter(Department.code == "TEST_CIVIL_SUPPLIES").first()
        if not dept:
            dept = Department(
                name="Test Department of Food & Civil Supplies",
                code="TEST_CIVIL_SUPPLIES",
                category="State Government"
            )
            db.add(dept)
            db.commit()

        cam = db.query(Camera).filter(Camera.logical_camera_id == "CAM-TEST-INTERNAL-01").first()
        if not cam:
            cam = Camera(
                logical_camera_id="CAM-TEST-INTERNAL-01",
                name="Godown Secure Grain Vault Camera",
                department_id=dept.id,
                district="Surat",
                location_name="Civil Supplies Godown Unit 4",
                lat=21.1702,
                lng=72.8311,
                share_scope="INTERNAL_ONLY"
            )
            db.add(cam)
            db.commit()

        # Police Officer from HOME_POLICE
        police_user = db.query(User).filter(User.username == "test_field_constable").first()
        assert police_user is not None

        # Clean prior test requests for test idempotency
        db.query(FederationAccessRequest).filter(
            FederationAccessRequest.camera_id == cam.id,
            FederationAccessRequest.requester_user_id == police_user.id
        ).delete()
        db.commit()

        # 1. Check access: Must be restricted
        allowed, reason = federation_service.can_user_access_camera(db, police_user, cam)
        assert allowed is False
        assert "Access Restricted" in reason

        # 2. Submit formal Federation Access Request
        req = federation_service.create_access_request(
            db=db,
            user=police_user,
            camera_id=cam.id,
            legal_justification="PDS grain black-marketing investigation under Essential Commodities Act",
            fir_number="FIR-2026/SURAT-ECA/0042",
            duration_hours=12
        )
        assert req.status == "PENDING"
        assert req.target_department_code == "TEST_CIVIL_SUPPLIES"

        # 3. Super Admin approves the federation request
        admin_user = db.query(User).filter(User.role == "SUPER_ADMIN").first()
        approved = federation_service.approve_access_request(
            db=db,
            request_id=req.id,
            approver_user=admin_user,
            status="APPROVED",
            duration_hours=12,
            remarks="Approved pursuant to Section 102 CrPC evidence collection"
        )
        assert approved.status == "APPROVED"
        assert approved.valid_until is not None

        # 4. Check access now: Must be granted
        allowed_after, reason_after = federation_service.can_user_access_camera(db, police_user, cam)
        assert allowed_after is True
        assert "Authorized via approved federation permit" in reason_after

        print(f"[PASS] test_department_camera_federation_lifecycle passed (Federation permit {req.request_uid} successfully authorized).")
    finally:
        db.close()

def test_blockchain_audit_hash_chain_tamper_detection():
    """
    Verify blockchain-style cryptographic hash chaining:
    1. Sequential actions produce valid chained hashes H_n = SHA256(H_{n-1} + ...).
    2. verify_chain returns VERIFIED_INTACT.
    3. Mutating one row directly in DB triggers TAMPERING_DETECTED.
    4. Restoring row returns VERIFIED_INTACT.
    """
    db = SessionLocal()
    try:
        # Append 3 test audit blocks
        b1 = audit_service.log_action(db, "OFFICER_1", "SEARCH_VEHICLE", "PLATE:GJ01XX1111", "Details 1")
        b2 = audit_service.log_action(db, "OFFICER_2", "STREAM_FEED", "CAMERA:CAM-01", "Details 2")
        b3 = audit_service.log_action(db, "OFFICER_1", "EXPORT_EVIDENCE", "CASE:CASE-01", "Details 3")

        # Verify hash link
        assert b2.prev_signature_hash == b1.signature_hash
        assert b3.prev_signature_hash == b2.signature_hash

        # Run verification: must be intact
        res = audit_service.verify_chain(db)
        assert res["status"] == "VERIFIED_INTACT"
        assert res["total_records_verified"] >= 3

        # TAMPER TEST: Modify b2's action in the database directly
        original_action = b2.action
        b2.action = "TAMPERED_ACTION_FORGED"
        db.commit()

        # Run verification again: must detect tampering!
        tamper_res = audit_service.verify_chain(db)
        assert tamper_res["status"] == "TAMPERING_DETECTED"
        assert tamper_res["compromised_record_id"] == b2.id

        # RESTORE: Put back original value so DB remains consistent
        b2.action = original_action
        db.commit()

        restored_res = audit_service.verify_chain(db)
        assert restored_res["status"] == "VERIFIED_INTACT"

        print(f"[PASS] test_blockchain_audit_hash_chain_tamper_detection passed (Chain intact -> Tampering detected at #{tamper_res['tampered_record_index']} -> Restored).")
    finally:
        db.close()

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING PHASE D ENTERPRISE RBAC & SECURITY VERIFICATION SUITE   ")
    print("==================================================================")
    test_roles_and_jwt_authentication()
    test_fine_grained_permission_denial()
    test_department_camera_federation_lifecycle()
    test_blockchain_audit_hash_chain_tamper_detection()
    print("\n*** ALL PHASE D RBAC & SECURITY TESTS PASSED WITH 100% SUCCESS!\n")
