"""
Tests for GSWAN (Gujarat State Wide Area Network) IPsec VPN Tunnel Connector and Gateway.
Verifies cryptographic configurations, Kubernetes manifests, diagnostic telemetry,
truth-in-engineering boundary enforcement, and API endpoints.
"""

import os
import yaml
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.gswan_connector import gswan_connector, GSWANTunnelStatus
from backend.app.services.gov_adapters import vahan_adapter
from backend.app.services.gov_adapters.base import IntegrationMode

client = TestClient(app)


def test_ipsec_configuration_files_exist_and_valid():
    """Verify strongSwan IPsec configuration files exist and adhere to RFC 7296 standards."""
    ipsec_conf_path = "deploy/ipsec/ipsec.conf"
    assert os.path.exists(ipsec_conf_path), "deploy/ipsec/ipsec.conf must exist"

    with open(ipsec_conf_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "keyexchange=ikev2" in content
    assert "aes256gcm16-sha384" in content
    assert "conn gswan-primary-gsdc" in content
    assert "conn gswan-secondary-dr" in content
    assert "10.100.1.1" in content
    assert "dpdaction=restart" in content

    secrets_path = "deploy/ipsec/ipsec.secrets.example"
    assert os.path.exists(secrets_path), "deploy/ipsec/ipsec.secrets.example must exist"

    strongswan_conf = "deploy/ipsec/strongswan.conf"
    assert os.path.exists(strongswan_conf), "deploy/ipsec/strongswan.conf must exist"
    with open(strongswan_conf, "r", encoding="utf-8") as f:
        ss_content = f.read()
    assert "charon" in ss_content


def test_kubernetes_ipsec_gateway_manifest():
    """Verify k8s/09-gswan-ipsec-gateway.yaml is valid YAML and includes NET_ADMIN security context."""
    k8s_manifest_path = "k8s/09-gswan-ipsec-gateway.yaml"
    assert os.path.exists(k8s_manifest_path), "k8s/09-gswan-ipsec-gateway.yaml must exist"

    with open(k8s_manifest_path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    assert len(docs) >= 2, "Expected at least Deployment and ConfigMap in manifest"
    deployment = next(d for d in docs if d.get("kind") == "Deployment")
    assert deployment["metadata"]["name"] == "gswan-ipsec-gateway"
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert "NET_ADMIN" in container["securityContext"]["capabilities"]["add"]

    configmap = next(d for d in docs if d.get("kind") == "ConfigMap")
    assert configmap["metadata"]["name"] == "gswan-ipsec-config"


def test_gswan_connector_unpeered_truthful_default():
    """Verify that by default (unpeered local host), GSWAN is reported as disconnected."""
    with patch.dict(os.environ, {"GSWAN_VPN_ACTIVE": "false", "GSWAN_SIMULATED_TEST": "false"}):
        assert not gswan_connector.is_tunnel_active()
        status = gswan_connector.get_connectivity_status()
        assert status["status"] == GSWANTunnelStatus.DISCONNECTED
        assert status["is_active"] is False
        assert status["latency_ms"] is None
        assert "not detected" in status["message"].lower()
        assert len(status["missing_requirements"]) > 0


def test_gswan_connector_simulated_test_mode():
    """Verify that in verified simulated test mode, connector transitions cleanly to SIMULATED_ACTIVE."""
    with patch.dict(os.environ, {"GSWAN_VPN_ACTIVE": "true", "GSWAN_SIMULATED_TEST": "true"}):
        assert gswan_connector.is_tunnel_active()
        status = gswan_connector.get_connectivity_status()
        assert status["status"] == GSWANTunnelStatus.SIMULATED_ACTIVE
        assert status["is_active"] is True
        assert status["latency_ms"] == 4.2
        assert status["latency_provenance"] == "SIMULATED_TEST_HARNESS"


def test_gswan_connector_fails_closed_when_flagged_without_network():
    """
    Verify that if someone sets GSWAN_VPN_ACTIVE=true on an unpeered machine
    without GSWAN_SIMULATED_TEST, the physical probe fails closed.
    """
    with patch.dict(os.environ, {"GSWAN_VPN_ACTIVE": "true", "GSWAN_SIMULATED_TEST": "false"}):
        # The probe to 10.100.1.1:500 will fail/timeout immediately
        assert not gswan_connector.is_tunnel_active()
        status = gswan_connector.get_connectivity_status()
        assert status["status"] == GSWANTunnelStatus.DISCONNECTED
        assert status["is_active"] is False


def test_gswan_api_endpoint():
    """Verify /api/system/gswan-status endpoint returns valid HTTP 200 with schema compliance."""
    res = client.get("/api/system/gswan-status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "is_active" in data
    assert "gateway_ip" in data
    assert "encryption_profile" in data
    assert "missing_requirements" in data
    assert data["encryption_profile"] == "AES-256-GCM / SHA384 / IKEv2 (RFC 7296)"


def test_system_readiness_includes_gswan_telemetry():
    """Verify /api/system/readiness includes GSWAN IPsec status."""
    res = client.get("/api/system/readiness")
    assert res.status_code == 200
    data = res.json()
    assert "gswan_ipsec" in data
    assert "status" in data["gswan_ipsec"]
    assert "is_active" in data["gswan_ipsec"]


def test_gov_adapter_fail_closed_without_gswan(tmp_path):
    """Verify that BaseGovAdapter strictly blocks queries in AUTHORIZED_PRODUCTION when GSWAN is inactive."""
    dummy_cert = tmp_path / "client.crt"
    dummy_key = tmp_path / "client.key"
    dummy_cert.write_text("CERT")
    dummy_key.write_text("KEY")

    vahan_adapter.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
    try:
        with patch.dict(os.environ, {
            "GOV_MTLS_CERT_PATH": str(dummy_cert),
            "GOV_MTLS_KEY_PATH": str(dummy_key),
            "GSWAN_VPN_ACTIVE": "false"
        }):
            with pytest.raises(RuntimeError) as exc:
                vahan_adapter.query("GJ01AB1234")
            assert "GSWAN" in str(exc.value)
    finally:
        vahan_adapter.set_mode(IntegrationMode.MOCK)
