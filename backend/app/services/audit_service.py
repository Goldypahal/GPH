"""
GIVIN Blockchain-Style Cryptographic Audit Hash Chain Engine.
Secures every sensitive operational action (search, playback, alert resolution, export)
with immutable Section 65B-compliant digital hash chains to prevent administrative tampering.
"""

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.orm import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
_audit_lock = threading.Lock()

def _format_timestamp_for_hash(dt: datetime) -> str:
    """Canonical ISO-8601 UTC string for consistent hashing across platforms."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

class AuditService:
    """
    Cryptographically chained tamper-evident audit logging service.
    """

    @classmethod
    def compute_signature_hash(
        cls,
        prev_hash: str,
        user_id: str,
        action: str,
        resource: str,
        timestamp_str: str,
        details_json: Optional[str] = None
    ) -> str:
        """Computes SHA-256 digest of block header + body content."""
        canonical_str = f"{prev_hash}|{user_id}|{action}|{resource}|{timestamp_str}|{details_json or ''}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def log_action(
        cls,
        db: Session,
        user_id: str,
        action: str,
        resource: str,
        details_json: Optional[str] = None
    ) -> AuditLog:
        """
        Appends an immutable audit block linked to the latest chain head.
        Thread-safe to prevent branching forks during concurrent requests.
        """
        with _audit_lock:
            # Retrieve latest block in the chain
            latest = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).first()
            prev_hash = latest.signature_hash if (latest and latest.signature_hash) else GENESIS_HASH

            now = datetime.now(timezone.utc)
            ts_str = _format_timestamp_for_hash(now)

            sig_hash = cls.compute_signature_hash(
                prev_hash=prev_hash,
                user_id=user_id,
                action=action,
                resource=resource,
                timestamp_str=ts_str,
                details_json=details_json
            )

            audit_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                details_json=details_json,
                prev_signature_hash=prev_hash,
                signature_hash=sig_hash,
                timestamp=now
            )
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
            return audit_entry

    @classmethod
    def verify_chain(cls, db: Session) -> Dict[str, Any]:
        """
        Traverses the complete audit logs table from genesis to head,
        verifying every cryptographic hash pointer and row signature.
        """
        records = db.query(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc()).all()

        if not records:
            return {
                "status": "VERIFIED_INTACT",
                "total_records_verified": 0,
                "tampered_record_index": None,
                "compromised_record_id": None,
                "chain_head_hash": None,
                "message": "Audit chain is empty. Genesis state intact."
            }

        prev_hash = GENESIS_HASH

        for idx, rec in enumerate(records):
            # Check if block links to predecessor
            expected_prev = prev_hash
            actual_prev = rec.prev_signature_hash or GENESIS_HASH

            # If legacy record without prev_hash, allow genesis
            if rec.prev_signature_hash is not None and rec.prev_signature_hash != expected_prev:
                return {
                    "status": "TAMPERING_DETECTED",
                    "total_records_verified": idx,
                    "tampered_record_index": idx,
                    "compromised_record_id": rec.id,
                    "chain_head_hash": prev_hash,
                    "message": (
                        f"Hash pointer broken at block #{idx} (ID: {rec.id}). "
                        f"Expected prev_hash: {expected_prev[:12]}..., found: {actual_prev[:12]}..."
                    )
                }

            # Check if content was mutated (for records logged with new hash format)
            ts_str = _format_timestamp_for_hash(rec.timestamp)
            computed_hash = cls.compute_signature_hash(
                prev_hash=actual_prev,
                user_id=rec.user_id,
                action=rec.action,
                resource=rec.resource,
                timestamp_str=ts_str,
                details_json=rec.details_json
            )

            # If the record has a 64-char hex hash that doesn't match recomputation, flag it
            # (Note: for records created with the new engine)
            if len(rec.signature_hash) == 64 and rec.prev_signature_hash is not None:
                if rec.signature_hash != computed_hash:
                    return {
                        "status": "TAMPERING_DETECTED",
                        "total_records_verified": idx,
                        "tampered_record_index": idx,
                        "compromised_record_id": rec.id,
                        "chain_head_hash": prev_hash,
                        "message": f"Block content tampered in record #{idx} (ID: {rec.id}). Cryptographic hash signature invalid."
                    }

            prev_hash = rec.signature_hash

        return {
            "status": "VERIFIED_INTACT",
            "total_records_verified": len(records),
            "tampered_record_index": None,
            "compromised_record_id": None,
            "chain_head_hash": prev_hash,
            "message": f"All {len(records)} audit log entries verified against cryptographic hash chain."
        }

    @classmethod
    def get_audit_trail(
        cls,
        db: Session,
        limit: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None
    ) -> List[AuditLog]:
        """Queries filtered audit events for compliance review."""
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id.ilike(f"%{user_id}%"))
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource.ilike(f"%{resource}%"))

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

audit_service = AuditService()
