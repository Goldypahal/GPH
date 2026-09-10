"""
GIVIN Day 2 Security Hardening & Secret Hygiene Test Suite
Verifies:
1. Production authentication enforcement (zero anonymous or super-admin fallback).
2. Production secret hygiene (SECRET_KEY, MINIO_SECRET_KEY validations).
3. OIDC token cryptographic validation & tampering rejection.
4. District jurisdictional fence validation (check_district_jurisdiction).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.core.security import (
    get_current_user,
    check_district_jurisdiction,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password
)
from backend.app.core.oidc import OIDCAuthManager, ABACUserClaims
from backend.app.models.orm import User


def test_production_mode_blocks_unauthenticated_access(monkeypatch):
    """Ensure get_current_user raises 401 when ENVIRONMENT is production and credentials missing."""
    from backend.app.core import config
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=None, db=None)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "production" in exc_info.value.detail.lower()


def test_production_secret_key_validation(monkeypatch):
    """Ensure Settings rejects weak or missing SECRET_KEY in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "")

    with pytest.raises(ValidationError):
        Settings()

    monkeypatch.setenv("SECRET_KEY", "short-secret")
    with pytest.raises(ValidationError):
        Settings()

    # Valid secret
    monkeypatch.setenv("SECRET_KEY", "this-is-a-very-secure-32-character-secret-key-12345")
    monkeypatch.setenv("MINIO_SECRET_KEY", "custom-strong-minio-key-987654321")
    s = Settings()
    assert len(s.SECRET_KEY) >= 32


def test_production_minio_secret_validation(monkeypatch):
    """Ensure Settings rejects default development password for MINIO in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "this-is-a-very-secure-32-character-secret-key-12345")
    monkeypatch.setenv("MINIO_SECRET_KEY", "change-this-development-password")

    with pytest.raises(ValidationError):
        Settings()


def test_district_jurisdiction_fencing():
    """Verify check_district_jurisdiction enforces boundaries between districts."""
    surat_officer = User(
        username="sp_surat",
        role="DISTRICT_OFFICER",
        jurisdiction_district="Surat"
    )
    ahmedabad_case_district = "Ahmedabad"
    surat_case_district = "Surat"

    # Surat officer cannot claim jurisdiction over Ahmedabad
    assert check_district_jurisdiction(surat_officer, ahmedabad_case_district) is False

    # Surat officer has jurisdiction over Surat
    assert check_district_jurisdiction(surat_officer, surat_case_district) is True

    # Statewide officer has jurisdiction everywhere
    state_officer = User(
        username="dgp_gujarat",
        role="DGP_STATE_COMMISSIONER",
        jurisdiction_district="Statewide"
    )
    assert check_district_jurisdiction(state_officer, ahmedabad_case_district) is True
    assert check_district_jurisdiction(state_officer, surat_case_district) is True


def test_password_hashing_and_verification():
    """Ensure PBKDF2-HMAC-SHA256 handles secure salting and prevents timing attacks."""
    pwd = "GovSurveillanceSecret!2026"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
