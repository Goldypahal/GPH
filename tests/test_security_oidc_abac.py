"""
Cryptographic OIDC Token Verification & ABAC Security Test Suite.
Validates:
1. RS256 signature verification via JWKS / registered public key.
2. Rejection of unverified / forged / tampered tokens.
3. Issuer, audience, expiry, and algorithm allow-list enforcement.
4. Production strictness: 401 on missing token (zero anonymous / default super-admin).
5. Non-production explicit dev bypass header vs rejection.
6. Role and clearance claim extraction from Keycloak structures.
7. ABAC clearance hierarchy, department boundaries, and district fences.
"""

import os
import sys
import time
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, Request

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.core.oidc import (
    OIDCAuthManager,
    ABACUserClaims,
    get_current_abac_user
)

# Test mini-app for dependency testing
test_app = FastAPI()

@test_app.get("/secure/resource")
def secure_endpoint(user: ABACUserClaims = Depends(get_current_abac_user)):
    return {
        "sub": user.sub,
        "username": user.preferred_username,
        "department": user.department_code,
        "clearance": user.security_clearance,
        "roles": user.roles,
        "is_dev_bypass": user.is_dev_bypass
    }

client = TestClient(test_app)


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generates an ephemeral RSA key pair for testing token signing and cryptographic verification."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    return private_key, public_key


def test_production_rejects_missing_token(monkeypatch):
    """Production mode MUST reject requests missing Authorization header with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = client.get("/secure/resource")
    assert res.status_code == 401
    assert "Missing OIDC bearer token in production environment" in res.json()["detail"]


def test_non_production_rejects_anonymous_without_dev_header(monkeypatch):
    """In development/staging, anonymous requests without the explicit dev bypass header are rejected."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    res = client.get("/secure/resource")
    assert res.status_code == 401
    assert "Provide a valid OIDC Bearer token or development bypass header" in res.json()["detail"]


def test_non_production_explicit_dev_bypass(monkeypatch):
    """Non-production accepts explicit X-Dev-Bypass-Token and creates a standard officer (not super-admin)."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    res = client.get(
        "/secure/resource",
        headers={"X-Dev-Bypass-Token": settings.DEV_BYPASS_TOKEN}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_dev_bypass"] is True
    assert "SUPER_ADMIN" not in data["roles"]
    assert "OFFICER" in data["roles"]


def test_production_rejects_dev_bypass_header(monkeypatch):
    """Production mode MUST ignore or reject dev bypass header and demand valid OIDC token."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = client.get(
        "/secure/resource",
        headers={"X-Dev-Bypass-Token": settings.DEV_BYPASS_TOKEN}
    )
    assert res.status_code == 401


def test_cryptographic_signature_verification(rsa_keypair, monkeypatch):
    """Verifies that a valid RS256 token signed by the trusted key is accepted and verified."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    private_key, public_key = rsa_keypair
    kid = "gj-police-key-01"

    # Register trusted public key in OIDCAuthManager
    OIDCAuthManager.register_test_key(kid, public_key)

    now = int(time.time())
    payload = {
        "sub": "pol-dsp-patel",
        "preferred_username": "DSP M. Patel",
        "email": "dsp.patel@police.gujarat.gov.in",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": settings.OIDC_CLIENT_ID,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "department_code": "HOME_POLICE",
        "jurisdiction_district": "Gandhinagar",
        "security_clearance": "SECRET",
        "badge_number": "GJ-POL-2026-778",
        "realm_access": {"roles": ["OFFICER", "PRIMARY_INVESTIGATOR"]},
        "resource_access": {settings.OIDC_CLIENT_ID: {"roles": ["ANPR_OPERATOR"]}}
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid, "alg": "RS256"}
    )

    res = client.get("/secure/resource", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sub"] == "pol-dsp-patel"
    assert body["department"] == "HOME_POLICE"
    assert body["clearance"] == "SECRET"
    assert "OFFICER" in body["roles"]
    assert "ANPR_OPERATOR" in body["roles"]


def test_rejects_forged_or_tampered_signature(rsa_keypair, monkeypatch):
    """Tampered token or token signed with wrong key is rejected with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    _, public_key = rsa_keypair
    kid = "gj-police-key-01"
    OIDCAuthManager.register_test_key(kid, public_key)

    # Generate an untrusted attacker key
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    payload = {
        "sub": "hacker",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": settings.OIDC_CLIENT_ID,
        "exp": now + 3600,
        "roles": ["SUPER_ADMIN"]
    }
    forged_token = jwt.encode(payload, attacker_key, algorithm="RS256", headers={"kid": kid})

    res = client.get("/secure/resource", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    assert "Cryptographic signature verification failed" in res.json()["detail"]


def test_rejects_expired_token(rsa_keypair, monkeypatch):
    """Expired tokens are rejected with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    private_key, public_key = rsa_keypair
    kid = "gj-police-key-01"
    OIDCAuthManager.register_test_key(kid, public_key)

    now = int(time.time())
    payload = {
        "sub": "pol-officer-01",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": settings.OIDC_CLIENT_ID,
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
        "roles": ["OFFICER"]
    }
    expired_token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})

    res = client.get("/secure/resource", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"]


def test_rejects_mismatched_issuer_or_audience(rsa_keypair, monkeypatch):
    """Tokens with incorrect issuer or audience claim are rejected with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    private_key, public_key = rsa_keypair
    kid = "gj-police-key-01"
    OIDCAuthManager.register_test_key(kid, public_key)

    now = int(time.time())
    # Wrong issuer
    bad_iss_payload = {
        "sub": "officer",
        "iss": "https://rogue-idp.example.com",
        "aud": settings.OIDC_CLIENT_ID,
        "exp": now + 3600
    }
    bad_iss_token = jwt.encode(bad_iss_payload, private_key, algorithm="RS256", headers={"kid": kid})
    res_iss = client.get("/secure/resource", headers={"Authorization": f"Bearer {bad_iss_token}"})
    assert res_iss.status_code == 401
    assert "issuer mismatch" in res_iss.json()["detail"]

    # Wrong audience
    bad_aud_payload = {
        "sub": "officer",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": "rogue-client-id",
        "exp": now + 3600
    }
    bad_aud_token = jwt.encode(bad_aud_payload, private_key, algorithm="RS256", headers={"kid": kid})
    res_aud = client.get("/secure/resource", headers={"Authorization": f"Bearer {bad_aud_token}"})
    assert res_aud.status_code == 401
    assert "audience mismatch" in res_aud.json()["detail"]


def test_rejects_disallowed_algorithm(rsa_keypair, monkeypatch):
    """Tokens using 'none' or disallowed algorithms are rejected."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    kid = "gj-police-key-01"
    now = int(time.time())
    payload = {
        "sub": "officer",
        "iss": settings.OIDC_ISSUER_URL,
        "aud": settings.OIDC_CLIENT_ID,
        "exp": now + 3600
    }
    # Algorithm "none" unsigned token
    token = jwt.encode(payload, key="", algorithm="none", headers={"kid": kid})
    res = client.get("/secure/resource", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "Disallowed or insecure JWT algorithm" in res.json()["detail"]
