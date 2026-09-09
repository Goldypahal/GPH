"""
GIVIN Unified Government Intelligence Bundle Service.
Aggregates VAHAN, SARTHI, eGujCop/CCTNS, and AFIS/NAFIS into a single
cryptographically signed National Intelligence Dossier with composite risk scoring.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
from backend.app.core.config import settings
from backend.app.services.gov_adapters.vahan_adapter import vahan_adapter
from backend.app.services.gov_adapters.sarathi_adapter import sarathi_adapter
from backend.app.services.gov_adapters.egujcop_adapter import egujcop_adapter
from backend.app.services.gov_adapters.afis_adapter import afis_adapter

class GovIntelBundleService:
    """
    Unified Government Data Aggregation & Risk Scoring Engine.
    """

    @classmethod
    def query_intel_bundle(cls, plate_number: str) -> Dict[str, Any]:
        """
        Executes parallel multi-database query across national and state registries.
        """
        vahan_data = vahan_adapter.query(plate_number)
        sarathi_data = sarathi_adapter.query(plate_number)
        egujcop_data = egujcop_adapter.query(plate_number)
        afis_data = afis_adapter.query(plate_number)

        # Calculate composite risk score
        score = 15.0
        if vahan_data.get("stolen_flag"):
            score += 40.0
        if egujcop_data.get("cctns_registered_match"):
            score += 25.0
        if "NON_BAILABLE" in egujcop_data.get("warrant_status", ""):
            score += 15.0
        if afis_data.get("biometric_reference_match"):
            score += 15.0

        composite_score = min(99.0, max(5.0, score))

        if composite_score >= 80.0:
            assessment = "CRITICAL_THREAT_FUGITIVE — Immediate Intercept Authorized"
        elif composite_score >= 50.0:
            assessment = "HIGH_RISK_STOLEN_OR_WARRANT — Monitor & Barricade Ahead"
        elif composite_score >= 30.0:
            assessment = "MODERATE_RISK — Unpaid Traffic Challans or Expired Fitness"
        else:
            assessment = "CLEARED_ROUTINE — No Outstanding Warrants or Thefts"

        now = datetime.now(timezone.utc)
        payload = {
            "plate_number": plate_number.upper(),
            "vahan": vahan_data,
            "sarathi": sarathi_data,
            "egujcop": egujcop_data,
            "afis": afis_data,
            "composite_risk_score": composite_score,
            "risk_assessment": assessment,
            "retrieved_at": now.isoformat()
        }

        # Cryptographic Section 65B signature of the complete bundle
        canonical = json.dumps(payload, sort_keys=True)
        sig = hashlib.sha256(f"{settings.SECRET_KEY}:BUNDLE:{canonical}".encode()).hexdigest()
        payload["source_signature_hash"] = sig
        payload["retrieved_at"] = now # datetime object for schema validation

        return payload

gov_intel_bundle_service = GovIntelBundleService()
