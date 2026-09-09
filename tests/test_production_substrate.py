"""
Production Substrate & Hardening Verification Test Suite:
1. Prometheus exposition format metrics exporter (/api/system/metrics).
2. Enterprise OIDC and Attribute-Based Access Control (ABAC) enforcement.
3. Kubernetes production manifest syntax & structural integrity.
"""

import os
import sys
import yaml
import pytest

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.oidc import OIDCAuthManager, ABACUserClaims

client = TestClient(app)


def test_prometheus_metrics_endpoint():
    """Validates that /api/system/metrics serves standard Prometheus exposition format."""
    res = client.get("/api/system/metrics")
    assert res.status_code == 200, res.text
    content = res.text
    
    # Assert standard Prometheus headers and gauges
    assert "# HELP givin_up" in content
    assert "# TYPE givin_up gauge" in content
    assert "givin_up 1" in content
    assert "givin_streaming_throughput_mps" in content
    assert "givin_cameras_total" in content
    assert "givin_dlq_messages_current" in content
    print("[PASS] test_prometheus_metrics_endpoint passed (Valid Prometheus exposition format).")


def test_abac_policy_clearance_and_jurisdiction():
    """Tests Attribute-Based Access Control (clearance, department fence, district boundary)."""
    # 1. Statewide Home Department Officer with SECRET clearance
    state_officer = ABACUserClaims(
        sub="officer-01",
        preferred_username="Inspector V. Patel",
        department_code="HOME_POLICE",
        jurisdiction_district="Statewide",
        security_clearance="SECRET",
        roles=["PRIMARY_INVESTIGATOR"]
    )
    # Allowed access to confidential Ahmedabad resource
    assert OIDCAuthManager.evaluate_abac_policy(
        claims=state_officer,
        resource_department="HOME_POLICE",
        resource_district="Ahmedabad",
        required_clearance="CONFIDENTIAL"
    ) is True

    # 2. Local District Officer with district fence
    surat_officer = ABACUserClaims(
        sub="officer-surat",
        preferred_username="Sub-Inspector Dave",
        department_code="HOME_POLICE",
        jurisdiction_district="Surat",
        security_clearance="CONFIDENTIAL",
        roles=["OFFICER"]
    )
    # Denied access to Ahmedabad camera
    assert OIDCAuthManager.evaluate_abac_policy(
        claims=surat_officer,
        resource_department="HOME_POLICE",
        resource_district="Ahmedabad",
        required_clearance="CONFIDENTIAL"
    ) is False

    # 3. Department Boundary Check
    mining_officer = ABACUserClaims(
        sub="mines-inspector-01",
        preferred_username="Mines Officer Joshi",
        department_code="MINES_GEOLOGY",
        jurisdiction_district="Statewide",
        security_clearance="CONFIDENTIAL",
        roles=["OFFICER"]
    )
    # Denied access to Police internal hotlist resource
    assert OIDCAuthManager.evaluate_abac_policy(
        claims=mining_officer,
        resource_department="HOME_POLICE",
        resource_district="Statewide",
        required_clearance="CONFIDENTIAL"
    ) is False

    # 4. Super Admin Override
    super_admin = ABACUserClaims(
        sub="admin-01",
        preferred_username="DGP Gujarat",
        department_code="HOME_POLICE",
        jurisdiction_district="Statewide",
        security_clearance="TOP_SECRET",
        roles=["STATE_POLICE_CHIEF", "SUPER_ADMIN"]
    )
    assert OIDCAuthManager.evaluate_abac_policy(
        claims=super_admin,
        resource_department="MINES_GEOLOGY",
        resource_district="Dahod",
        required_clearance="TOP_SECRET"
    ) is True

    print("[PASS] test_abac_policy_clearance_and_jurisdiction passed (Clearance, department, and district fences enforced).")


def test_kubernetes_manifests_syntax():
    """Validates that all Kubernetes manifests in k8s/ parse into valid YAML structures."""
    k8s_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "k8s"))
    assert os.path.exists(k8s_dir), f"Directory {k8s_dir} does not exist"

    manifest_files = [f for f in os.listdir(k8s_dir) if f.endswith(".yaml") or f.endswith(".yml")]
    assert len(manifest_files) >= 7, f"Expected at least 7 manifests, found {len(manifest_files)}"

    for mf in manifest_files:
        filepath = os.path.join(k8s_dir, mf)
        with open(filepath, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            assert len(docs) >= 1, f"Empty manifest: {mf}"
            for d in docs:
                if d is not None:
                    assert "apiVersion" in d, f"Missing apiVersion in {mf}"
                    assert "kind" in d, f"Missing kind in {mf}"
                    assert "metadata" in d, f"Missing metadata in {mf}"

    print(f"[PASS] test_kubernetes_manifests_syntax passed ({len(manifest_files)} manifests parsed cleanly).")


if __name__ == "__main__":
    test_prometheus_metrics_endpoint()
    test_abac_policy_clearance_and_jurisdiction()
    test_kubernetes_manifests_syntax()
    print("\n*** ALL PRODUCTION SUBSTRATE & HARDENING TESTS PASSED WITH 100% SUCCESS!")
