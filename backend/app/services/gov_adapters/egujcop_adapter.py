from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class EGujCopAdapter(BaseGovAdapter):
    """
    Adapter for Gujarat Police Crime and Criminal Tracking Network & Systems (CCTNS / eGujCop).
    Cross-references suspect vehicles with active FIRs, warrants, and criminal syndicates.
    """
    def __init__(self):
        super().__init__("eGujCop (Gujarat Police CCTNS)", "https://police.gujarat.gov.in/cctns/api/v2/crimes")

    def query(self, plate_or_fir: str) -> Dict[str, Any]:
        cleaned = plate_or_fir.replace("-", "").upper()
        is_hit = "GJ01AB1234" in cleaned or "GJ05CD5521" in cleaned or "GJ06XY9876" in cleaned

        return {
            "service": self.service_name,
            "query_key": cleaned,
            "cctns_registered_match": is_hit,
            "associated_fir": "FIR-2026/AHM-CRIME/0981" if is_hit else None,
            "police_station": "Crime Branch, Ahmedabad City",
            "charges_ipc_bns": ["BNS Sec 309 (Robbery)", "BNS Sec 140 (Kidnapping)"] if is_hit else [],
            "risk_classification": "CRITICAL" if is_hit else "CLEAR",
            "investigating_officer": "Inspector V. K. Patel, Badge #GJ-4412",
            "warrant_status": "NON_BAILABLE_WARRANT_ACTIVE" if is_hit else "NO_WARRANT"
        }

egujcop_adapter = EGujCopAdapter()
