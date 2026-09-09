import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from backend.app.core.config import settings

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
