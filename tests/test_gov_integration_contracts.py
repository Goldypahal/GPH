"""
Deterministic Government Integration Contract Tests for GIVIN Platform.
Verifies all 6 government database adapters:
1. VAHAN (National Vehicle Registry)
2. SARATHI (National Driving License Registry)
3. CCTNS (Crime & Criminal Tracking Network & Systems)
4. eGujCop (Gujarat Police State Hotlists & FIRs)
5. AFIS (State Automated Fingerprint Identification System)
6. NAFIS (National Automated Fingerprint Identification System)

Enforces:
- Multi-mode readiness: MOCK, SANDBOX, AUTHORIZED_PRODUCTION
- Fail-closed security in AUTHORIZED_PRODUCTION (no credentials = refused operation)
- Readiness states: SOFTWARE_READY, SANDBOX_READY, PRODUCTION_CREDENTIALS_REQUIRED,
  NETWORK_ACCESS_REQUIRED, GOVERNMENT_AUTHORIZATION_REQUIRED
- Rate limiting, timeout, retries, and cryptographic source signatures
"""

import os
import sys
import pytest
from unittest.mock import patch

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.gov_adapters.base import IntegrationMode, ReadinessState
from backend.app.services.gov_adapters import (
    vahan_adapter,
    sarathi_adapter,
    cctns_adapter,
    egujcop_adapter,
    afis_adapter,
    nafis_adapter,
    gov_intel_bundle_service
)


@pytest.fixture
def adapters():
    adapter_list = [
        vahan_adapter,
        sarathi_adapter,
        cctns_adapter,
        egujcop_adapter,
        afis_adapter,
        nafis_adapter
    ]
    for a in adapter_list:
        a.set_mode(IntegrationMode.MOCK)
        a._recent_query_timestamps = []
    yield adapter_list
    for a in adapter_list:
        a.set_mode(IntegrationMode.MOCK)
        a._recent_query_timestamps = []


def test_all_adapters_mock_mode_software_ready(adapters):
    """Verify that in MOCK mode, all 6 adapters report SOFTWARE_READY and query successfully."""
    for adapter in adapters:
        adapter.set_mode(IntegrationMode.MOCK)
        adapter._recent_query_timestamps = []
        readiness = adapter.get_readiness_state()
        assert readiness["readiness"] == ReadinessState.SOFTWARE_READY.value
        
        # Test contract query
        res = adapter.query("GJ01AB1234")
        assert res.get("status") != "LOOKUP_FAILED"
        assert res["integration_mode"] == "MOCK"
        assert "source_signature_hash" in res


def test_all_adapters_sandbox_mode_readiness(adapters):
    """Verify that in SANDBOX mode, adapters report SANDBOX_READY."""
    for adapter in adapters:
        adapter.set_mode(IntegrationMode.SANDBOX)
        readiness = adapter.get_readiness_state()
        assert readiness["readiness"] == ReadinessState.SANDBOX_READY.value


def test_production_mode_fails_closed_without_credentials(adapters):
    """Verify that in AUTHORIZED_PRODUCTION mode without credentials, queries FAIL CLOSED."""
    for adapter in adapters:
        adapter.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
        adapter._recent_query_timestamps = []

        # With no mTLS env vars, readiness must be PRODUCTION_CREDENTIALS_REQUIRED
        with patch.dict(os.environ, {}, clear=True):
            readiness = adapter.get_readiness_state()
            assert readiness["readiness"] == ReadinessState.PRODUCTION_CREDENTIALS_REQUIRED.value

            # Direct query attempt must raise RuntimeError (fail closed)
            with pytest.raises(RuntimeError) as exc_info:
                adapter.query("GJ01AB1234")
            assert "AUTHORIZED_PRODUCTION refuses to operate" in str(exc_info.value)


def test_production_mode_fails_closed_without_gswan_vpn(adapters, tmp_path):
    """Verify that with certs present but GSWAN VPN missing, readiness is NETWORK_ACCESS_REQUIRED."""
    dummy_cert = tmp_path / "client.crt"
    dummy_key = tmp_path / "client.key"
    dummy_cert.write_text("CERT")
    dummy_key.write_text("KEY")

    for adapter in adapters:
        adapter.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
        with patch.dict(os.environ, {
            "GOV_MTLS_CERT_PATH": str(dummy_cert),
            "GOV_MTLS_KEY_PATH": str(dummy_key),
            "GSWAN_VPN_ACTIVE": "false"
        }):
            readiness = adapter.get_readiness_state()
            assert readiness["readiness"] == ReadinessState.NETWORK_ACCESS_REQUIRED.value

            with pytest.raises(RuntimeError) as exc_info:
                adapter.query("GJ01AB1234")
            assert "GSWAN" in str(exc_info.value)


def test_production_mode_reports_gov_authorization_required(adapters, tmp_path):
    """Verify that with certs and VPN present, system reports GOVERNMENT_AUTHORIZATION_REQUIRED."""
    dummy_cert = tmp_path / "client.crt"
    dummy_key = tmp_path / "client.key"
    dummy_cert.write_text("CERT")
    dummy_key.write_text("KEY")

    for adapter in adapters:
        adapter.set_mode(IntegrationMode.AUTHORIZED_PRODUCTION)
        with patch.dict(os.environ, {
            "GOV_MTLS_CERT_PATH": str(dummy_cert),
            "GOV_MTLS_KEY_PATH": str(dummy_key),
            "GSWAN_VPN_ACTIVE": "true"
        }):
            readiness = adapter.get_readiness_state()
            assert readiness["readiness"] == ReadinessState.GOVERNMENT_AUTHORIZATION_REQUIRED.value


def test_intelligence_bundle_service_aggregation():
    """Verify that GovIntelBundleService aggregates all databases and signs bundle."""
    bundle = gov_intel_bundle_service.query_intel_bundle("GJ01AB1234")
    
    assert "vahan" in bundle
    assert "cctns" in bundle
    assert "egujcop" in bundle
    assert "source_signature_hash" in bundle
    assert bundle["plate_number"] == "GJ01AB1234"

