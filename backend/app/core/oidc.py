"""
Enterprise OpenID Connect (OIDC) & Attribute-Based Access Control (ABAC) Module.
Integrates with Gujarat State Single Sign-On (SSO) and Keycloak IAM clusters.
Enforces cryptographic token verification, multi-departmental federation,
jurisdictional fences, and clearance-level security.
"""

import time
import json
import logging
import urllib.request
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

from backend.app.core.config import settings

logger = logging.getLogger("givin.oidc")
security_bearer = HTTPBearer(auto_error=False)


class ABACUserClaims(BaseModel):
    sub: str
    preferred_username: str
    email: Optional[str] = None
    department_code: str = "HOME_POLICE"
    jurisdiction_district: str = "Statewide"
    security_clearance: str = "CONFIDENTIAL"  # UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET
    badge_number: Optional[str] = None
    roles: List[str] = ["OFFICER"]
    is_dev_bypass: bool = False


class OIDCAuthManager:
    """
    Validates Keycloak/State SSO OIDC bearer tokens with cryptographic signature verification,
    JWKS key caching, and computes dynamic ABAC policy decisions.
    """

    _jwks_client: Optional[PyJWKClient] = None
    _jwks_uri: Optional[str] = None
    _jwks_uri_cached_at: float = 0.0
    _test_public_keys: Dict[str, Any] = {}

    @classmethod
    def register_test_key(cls, kid: str, public_key_or_pem: Any) -> None:
        """Allows test suites to register in-memory public keys for offline cryptographic validation."""
        cls._test_public_keys[kid] = public_key_or_pem

    @classmethod
    def clear_test_keys(cls) -> None:
        cls._test_public_keys.clear()

    @classmethod
    def discover_jwks_uri(cls) -> str:
        """
        Discovers the JWKS URI from OIDC_ISSUER_URL/.well-known/openid-configuration.
        Falls back to configured OIDC_JWKS_URL if discovery fails or if explicitly configured.
        """
        if settings.OIDC_JWKS_URL:
            return settings.OIDC_JWKS_URL

        now = time.time()
        if cls._jwks_uri and (now - cls._jwks_uri_cached_at) < 3600:
            return cls._jwks_uri

        discovery_url = f"{settings.OIDC_ISSUER_URL.rstrip('/')}/.well-known/openid-configuration"
        try:
            req = urllib.request.Request(
                discovery_url,
                headers={"User-Agent": "GIVIN-OIDC-Client/1.2"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                config = json.loads(response.read().decode("utf-8"))
                jwks_uri = config.get("jwks_uri")
                if jwks_uri:
                    cls._jwks_uri = jwks_uri
                    cls._jwks_uri_cached_at = now
                    return jwks_uri
        except Exception as e:
            logger.warning(f"OIDC discovery failed from {discovery_url}: {e}")

        # Fallback default Keycloak path if discovery cannot be reached directly
        return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/certs"

    @classmethod
    def get_jwks_client(cls) -> PyJWKClient:
        """Initializes or returns cached PyJWKClient instance."""
        if cls._jwks_client is None:
            jwks_uri = cls.discover_jwks_uri()
            cls._jwks_client = PyJWKClient(jwks_uri, cache_keys=True, max_cached_keys=32)
        return cls._jwks_client

    @classmethod
    def resolve_signing_key(cls, token: str) -> Any:
        """
        Inspects unverified JWT header to extract 'kid' and 'alg',
        then selects the corresponding public key from JWKS or registered test keys.
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid JWT header format: {str(e)}")

        alg = unverified_header.get("alg")
        if alg not in settings.OIDC_ALLOWED_ALGORITHMS:
            raise HTTPException(
                status_code=401,
                detail=f"Disallowed or insecure JWT algorithm '{alg}'. Permitted: {settings.OIDC_ALLOWED_ALGORITHMS}"
            )

        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing mandatory 'kid' in header")

        # Check registered in-memory test keys first
        if kid in cls._test_public_keys:
            return cls._test_public_keys[kid]

        # Fetch from remote Keycloak JWKS endpoint
        try:
            jwks_client = cls.get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return signing_key.key
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Unable to retrieve public key for kid '{kid}' from OIDC JWKS: {str(e)}"
            )

    @classmethod
    def decode_and_validate_token(cls, token: str) -> ABACUserClaims:
        """
        Cryptographically validates JWT claims against OIDC issuer configuration:
        - Signature verification via public key (RS256/ES256)
        - Issuer validation
        - Audience validation
        - Expiry (exp) and Not-Before (nbf) validation
        - Extracts ABAC claims (department, district, clearance, badge, roles)
        """
        signing_key = cls.resolve_signing_key(token)

        try:
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=settings.OIDC_ALLOWED_ALGORITHMS,
                issuer=settings.OIDC_ISSUER_URL,
                audience=settings.OIDC_CLIENT_ID,
                options={
                    "verify_signature": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "require": ["exp", "iss", "aud", "sub"]
                }
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="OIDC bearer token has expired")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=401, detail=f"OIDC token issuer mismatch. Expected '{settings.OIDC_ISSUER_URL}'")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail=f"OIDC token audience mismatch. Expected '{settings.OIDC_CLIENT_ID}'")
        except jwt.ImmatureSignatureError:
            raise HTTPException(status_code=401, detail="OIDC token not yet valid (nbf constraint)")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=401, detail="Cryptographic signature verification failed for OIDC token")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid OIDC bearer token: {str(e)}")

        # Extract roles from Keycloak resource_access, realm_access, or root roles
        extracted_roles = set()
        if "resource_access" in claims and settings.OIDC_CLIENT_ID in claims["resource_access"]:
            extracted_roles.update(claims["resource_access"][settings.OIDC_CLIENT_ID].get("roles", []))
        if "realm_access" in claims:
            extracted_roles.update(claims["realm_access"].get("roles", []))
        if "roles" in claims and isinstance(claims["roles"], list):
            extracted_roles.update(claims["roles"])

        final_roles = list(extracted_roles) if extracted_roles else ["OFFICER"]

        return ABACUserClaims(
            sub=claims.get("sub", "unknown-officer"),
            preferred_username=claims.get("preferred_username") or claims.get("username") or claims.get("sub", "officer"),
            email=claims.get("email"),
            department_code=claims.get("department_code", "HOME_POLICE"),
            jurisdiction_district=claims.get("jurisdiction_district", "Statewide"),
            security_clearance=claims.get("security_clearance", "CONFIDENTIAL"),
            badge_number=claims.get("badge_number"),
            roles=final_roles,
            is_dev_bypass=False
        )

    @classmethod
    def evaluate_abac_policy(
        cls,
        claims: ABACUserClaims,
        resource_department: str,
        resource_district: Optional[str] = None,
        required_clearance: str = "CONFIDENTIAL"
    ) -> bool:
        """
        Enforces dynamic Attribute-Based Access Control:
        1. Clearance hierarchy: TOP_SECRET > SECRET > CONFIDENTIAL > UNCLASSIFIED.
        2. Department boundary: Exact match or active federation grant or SUPER_ADMIN role.
        3. District fence: 'Statewide' clearance or exact district match.
        """
        CLEARANCE_HIERARCHY = {
            "UNCLASSIFIED": 1,
            "CONFIDENTIAL": 2,
            "SECRET": 3,
            "TOP_SECRET": 4
        }

        # 1. Super admin / State police chief override
        if "SUPER_ADMIN" in claims.roles or "STATE_POLICE_CHIEF" in claims.roles:
            return True

        # 2. Check clearance level
        user_level = CLEARANCE_HIERARCHY.get(claims.security_clearance, 1)
        req_level = CLEARANCE_HIERARCHY.get(required_clearance, 2)
        if user_level < req_level:
            return False

        # 3. Check department domain
        if claims.department_code != "HOME_POLICE" and claims.department_code != resource_department:
            return False

        # 4. Check jurisdictional district fence
        if claims.jurisdiction_district != "Statewide" and resource_district:
            if claims.jurisdiction_district.lower() != resource_district.lower():
                return False

        return True


def get_current_abac_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> ABACUserClaims:
    """
    FastAPI Dependency for OIDC token extraction and ABAC identity hydration.
    In Production (ENVIRONMENT=production):
      - Missing or invalid token ALWAYS returns 401 Unauthorized.
      - Zero anonymous or default super-admin fallback.
    In Non-Production (ENVIRONMENT!=production):
      - Missing token returns 401 UNLESS explicit header 'X-Dev-Bypass-Token' is provided
        matching DEV_BYPASS_TOKEN, which returns a sandboxed standard officer identity (not super-admin).
    """
    if auth and auth.credentials:
        return OIDCAuthManager.decode_and_validate_token(auth.credentials)

    # If no token provided:
    is_prod = settings.ENVIRONMENT == "production"

    if is_prod:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Missing OIDC bearer token in production environment"
        )

    # In development/staging environments, require explicit developer bypass header
    dev_header = request.headers.get("X-Dev-Bypass-Token")
    if dev_header and dev_header == settings.DEV_BYPASS_TOKEN:
        return ABACUserClaims(
            sub="dev-officer-local",
            preferred_username="Dev Officer (Local Sandbox)",
            department_code="HOME_POLICE",
            jurisdiction_district="Statewide",
            security_clearance="CONFIDENTIAL",
            badge_number="DEV-GJ-POL-001",
            roles=["OFFICER", "PRIMARY_INVESTIGATOR"],
            is_dev_bypass=True
        )

    # In non-production, if neither a valid token nor the dev bypass token is provided:
    raise HTTPException(
        status_code=401,
        detail="Authentication required: Provide a valid OIDC Bearer token or development bypass header"
    )
