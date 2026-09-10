import hashlib
import hmac
import json
import base64
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """PBKDF2-HMAC-SHA256 password hasher with 100,000 iterations."""
    if not salt:
        salt = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plain password against its hashed salt$key representation."""
    try:
        salt, key_hex = hashed.split("$", 1)
        recomputed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(recomputed.hex(), key_hex)
    except Exception:
        return False

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Standard cryptographically-signed JWT representation using HMAC-SHA256."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = int(expire.timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    
    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64_encode(json.dumps(to_encode, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    
    signature = hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64_encode(signature)}"

def decode_access_token(token: str) -> Optional[dict]:
    """Validates JWT signature and expiration, returns decoded payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        signing_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
        actual_sig = _b64_decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64_decode(parts[1]).decode())
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency extracting authenticated User from Authorization Bearer token.
    Falls back to a default control room operator if unauthenticated in dev/demo mode.
    """
    from backend.app.models.orm import User
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.username == payload["sub"]).first()
            if user and user.is_active:
                return user
    
    # Strict production enforcement: Never allow anonymous or fallback access in production
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Valid bearer token mandatory in production environment"
        )

    # Fallback dev/demo default operator for local non-production environments
    user = db.query(User).filter(User.role == "SUPER_ADMIN").first()
    if not user:
        user = db.query(User).first()
    return user

# =====================================================================
# 5-TIER HIERARCHICAL RBAC & GRANULAR SCOPES MATRIX
# =====================================================================

ROLE_DESCRIPTIONS = {
    "SUPER_ADMIN": "Statewide System Administrator with full infrastructure and override authority",
    "DGP_STATE_COMMISSIONER": "State Director General / Commissioner with statewide surveillance and federation clearance",
    "SP_DISTRICT_CHIEF": "District Superintendent of Police with district surveillance and case administration",
    "FIELD_OFFICER": "Field Police Officer with pursuit, ANPR query, and alert dispatch response",
    "AUDITOR_COMPLIANCE": "Judicial / Vigilance Auditor with tamper-evidence verification authority"
}

ROLE_SCOPES: Dict[str, List[str]] = {
    "SUPER_ADMIN": ["*"],
    "DGP_STATE_COMMISSIONER": [
        "cameras:read", "cameras:stream", "cameras:federation",
        "tracking:search", "tracking:pursuit", "tracking:containment",
        "alerts:read", "alerts:dispatch", "alerts:resolve",
        "watchlist:read", "watchlist:write",
        "cases:read", "cases:write",
        "audit:read"
    ],
    "STATE_COMMAND": [ # synonym
        "cameras:read", "cameras:stream", "cameras:federation",
        "tracking:search", "tracking:pursuit", "tracking:containment",
        "alerts:read", "alerts:dispatch", "alerts:resolve",
        "watchlist:read", "watchlist:write",
        "cases:read", "cases:write",
        "audit:read"
    ],
    "SP_DISTRICT_CHIEF": [
        "cameras:read", "cameras:write", "cameras:stream",
        "tracking:search", "tracking:pursuit", "tracking:containment",
        "alerts:read", "alerts:dispatch", "alerts:resolve",
        "watchlist:read", "watchlist:write",
        "cases:read", "cases:write"
    ],
    "DISTRICT_OFFICER": [ # synonym
        "cameras:read", "cameras:write", "cameras:stream",
        "tracking:search", "tracking:pursuit", "tracking:containment",
        "alerts:read", "alerts:dispatch", "alerts:resolve",
        "watchlist:read", "watchlist:write",
        "cases:read", "cases:write"
    ],
    "FIELD_OFFICER": [
        "cameras:read", "cameras:stream",
        "tracking:search", "tracking:pursuit",
        "alerts:read", "alerts:acknowledge",
        "watchlist:read",
        "cases:read"
    ],
    "INVESTIGATOR": [ # synonym
        "cameras:read", "cameras:stream",
        "tracking:search", "tracking:pursuit", "tracking:containment",
        "alerts:read", "alerts:acknowledge",
        "watchlist:read",
        "cases:read", "cases:write"
    ],
    "CONTROL_ROOM_OPERATOR": [ # synonym
        "cameras:read", "cameras:stream",
        "tracking:search", "tracking:pursuit",
        "alerts:read", "alerts:acknowledge",
        "watchlist:read",
        "cases:read"
    ],
    "AUDITOR_COMPLIANCE": [
        "audit:read", "audit:verify", "evidence:verify", "system:read"
    ],
    "AUDITOR": [ # synonym
        "audit:read", "audit:verify", "evidence:verify", "system:read"
    ]
}

def get_scopes_for_role(role: str) -> List[str]:
    """Resolves authorized permissions for a given role name."""
    return ROLE_SCOPES.get(role, ["cameras:read", "tracking:search"])

def require_role(*allowed_roles: str):
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""
    def role_checker(user = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if user.role != "SUPER_ADMIN" and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. User role '{user.role}' lacks required permissions: {allowed_roles}"
            )
        return user
    return role_checker

def require_permission(*required_scopes: str):
    """Fine-grained OAuth2/JWT scope verification dependency."""
    def permission_checker(user = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        user_scopes = get_scopes_for_role(user.role)
        if "*" in user_scopes:
            return user
        for req in required_scopes:
            if req not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: required '{req}', granted scopes: {user_scopes}"
                )
        return user
    return permission_checker

def check_district_jurisdiction(user, district: Optional[str]) -> bool:
    """Verifies whether officer holds jurisdiction over specified district."""
    if not district or not user.jurisdiction_district:
        return True # Statewide officer or statewide resource
    if user.role in ("SUPER_ADMIN", "DGP_STATE_COMMISSIONER", "STATE_COMMAND"):
        return True
    return user.jurisdiction_district.strip().lower() == district.strip().lower()


def generate_sha256_hash(data: bytes) -> str:
    """Generate SHA-256 cryptographic hash of evidence or data."""
    return hashlib.sha256(data).hexdigest()

def generate_evidence_certificate_hash(
    camera_id: str,
    timestamp: str,
    plate_text: str,
    image_hash: str,
    operator_id: str
) -> str:
    """
    Computes an immutable HMAC-SHA256 digital signature conforming to
    Section 65B of the Indian Evidence Act (Certificate of Authenticity).
    """
    payload = f"{camera_id}:{timestamp}:{plate_text}:{image_hash}:{operator_id}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_evidence_integrity(
    camera_id: str,
    timestamp: str,
    plate_text: str,
    image_hash: str,
    operator_id: str,
    expected_signature: str
) -> bool:
    """Verify whether digital evidence was tampered with."""
    recomputed = generate_evidence_certificate_hash(
        camera_id, timestamp, plate_text, image_hash, operator_id
    )
    return hmac.compare_digest(recomputed, expected_signature)
