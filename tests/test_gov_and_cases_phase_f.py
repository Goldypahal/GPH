"""
Test Suite for Phase F: Government Integrations & Investigation Workflows
Verifies:
1. Stateful Government Database Adapters (VAHAN, SARTHI, eGujCop, AFIS) with Redis caching & signatures.
2. Unified Government Intelligence Dossier aggregation & composite risk scoring.
3. Automated case creation from alert & timeline evidence linkage.
4. Court-admissible Section 65B Electronic Evidence ZIP Bundle export.
"""

import os
import sys
import io
import json
import zipfile
import uuid
from datetime import datetime, timezone

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Alert, VehicleSighting, Camera, Case
from backend.app.services.gov_adapters.vahan_adapter import vahan_adapter
from backend.app.services.gov_adapters.sarathi_adapter import sarathi_adapter
from backend.app.services.gov_adapters.egujcop_adapter import egujcop_adapter
from backend.app.services.gov_adapters.afis_adapter import afis_adapter
from backend.app.services.gov_adapters.bundle import gov_intel_bundle_service

client = TestClient(app)

def test_gov_adapters_caching_and_signatures():
    """Verify government adapters sign responses and cache in Redis."""
    target = "GJ01AB1234"

    # 1. VAHAN Query 1 (Direct Query)
    v1 = vahan_adapter.query(target)
    assert v1["registration_number"] == target
    assert v1["stolen_flag"] is True
    assert "source_signature_hash" in v1
    assert len(v1["source_signature_hash"]) == 64

    # 2. VAHAN Query 2 (Cache Hit)
    v2 = vahan_adapter.query(target)
    assert v2["registration_number"] == target
    assert v2.get("cache_hit") is True

    # 3. SARTHI Query
    s1 = sarathi_adapter.query(target)
    assert "license_number" in s1
    assert "source_signature_hash" in s1

    # 4. eGujCop Query
    e1 = egujcop_adapter.query(target)
    assert e1["cctns_registered_match"] is True
    assert "NON_BAILABLE" in e1["warrant_status"]
    assert "source_signature_hash" in e1

    # 5. AFIS Query
    a1 = afis_adapter.query(target)
    assert a1["biometric_reference_match"] is True
    assert "source_signature_hash" in a1

    print(f"[PASS] test_gov_adapters_caching_and_signatures passed (VAHAN, SARTHI, eGujCop, AFIS signed & cached).")

def test_unified_intel_bundle():
    """Verify unified intelligence bundle aggregates all 4 registries with composite risk scoring."""
    target = "GJ01AB1234"
    bundle = gov_intel_bundle_service.query_intel_bundle(target)
    assert bundle["plate_number"] == target
    assert bundle["composite_risk_score"] >= 80.0
    assert "CRITICAL_THREAT_FUGITIVE" in bundle["risk_assessment"]
    assert len(bundle["source_signature_hash"]) == 64

    # Verify HTTP API
    res = client.get(f"/api/system/gov/intel-bundle/{target}")
    assert res.status_code == 200
    data = res.json()
    assert data["composite_risk_score"] >= 80.0
    assert "vahan" in data and "egujcop" in data
    print(f"[PASS] test_unified_intel_bundle passed (Risk: {data['composite_risk_score']}/100, Assessment: {data['risk_assessment'][:35]}...).")

def test_case_creation_from_alert():
    """Verify opening an investigation case directly from an alert with automated intel enrichment."""
    db = SessionLocal()
    try:
        alert = db.query(Alert).first()
        assert alert is not None

        res = client.post(
            f"/api/cases/from-alert/{alert.id}",
            json={
                "title": f"Special Taskforce Pursuit: {alert.plate_text}",
                "assigned_investigator": "Inspector Vikram Patel",
                "priority": "CRITICAL"
            }
        )
        assert res.status_code == 200
        case_data = res.json()
        assert case_data["case_number"].startswith("CASE-2026-GJ-")
        assert case_data["status"] == "INVESTIGATING"
        assert case_data["timeline_count"] >= 2 # Has alert trigger + gov intel notes

        # Link an additional sighting to the case
        sighting = db.query(VehicleSighting).first()
        res_link = client.post(f"/api/cases/{case_data['id']}/link-sighting/{sighting.id}")
        assert res_link.status_code == 200
        assert res_link.json()["status"] == "SUCCESS"

        print(f"[PASS] test_case_creation_from_alert passed (Case: {case_data['case_number']} with {case_data['timeline_count']} timeline items).")
    finally:
        db.close()

def test_evidence_zip_bundle_export():
    """
    Verify court-admissible Section 65B Electronic Evidence ZIP Bundle export:
    Validates ZIP file format, manifest.json, Section_65B_Certificate.json, and investigation_dossier.json.
    """
    db = SessionLocal()
    try:
        case = db.query(Case).first()
        assert case is not None

        res = client.get(f"/api/cases/{case.id}/evidence-bundle")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/zip"
        assert f"GIVIN_Evidence_{case.case_number}.zip" in res.headers["content-disposition"]

        # Parse in-memory ZIP archive
        zip_bytes = res.content
        assert len(zip_bytes) > 200
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            file_list = zf.namelist()
            assert "manifest.json" in file_list
            assert "Section_65B_Certificate.json" in file_list
            assert "investigation_dossier.json" in file_list

            # Validate manifest
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            assert manifest["case_number"] == case.case_number
            assert "Section 65B" in manifest["evidence_act_reference"]

            # Validate Section 65B Certificate
            cert = json.loads(zf.read("Section_65B_Certificate.json").decode("utf-8"))
            assert cert["case_number"] == case.case_number
            assert cert["status"] == "STATUTORILY_VERIFIED_AUTHENTIC"
            assert "integrity_signature_hash" in cert

            # Validate Investigation Dossier
            dossier = json.loads(zf.read("investigation_dossier.json").decode("utf-8"))
            assert dossier["case_number"] == case.case_number
            assert len(dossier["timeline"]) >= 1

        print(f"[PASS] test_evidence_zip_bundle_export passed (Valid ZIP with {len(file_list)} legal evidence artifacts).")
    finally:
        db.close()

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING PHASE F GOV INTEGRATIONS & CASES VERIFICATION SUITE     ")
    print("==================================================================")
    test_gov_adapters_caching_and_signatures()
    test_unified_intel_bundle()
    test_case_creation_from_alert()
    test_evidence_zip_bundle_export()
    print("\n*** ALL PHASE F GOV & CASE TESTS PASSED WITH 100% SUCCESS!\n")
