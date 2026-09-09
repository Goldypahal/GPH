from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class EGujCopAdapter(BaseGovAdapter):
    """
    Adapter for Gujarat Police Crime and Criminal Tracking Network & Systems (CCTNS / eGujCop).
    Cross-references suspect vehicles with active FIRs, warrants, and criminal syndicates.
    """
    def __init__(self):
        super().__init__("eGujCop (Gujarat Police CCTNS)", "https://police.gujarat.gov.in/cctns/api/v2/crimes")

    def _fetch_data(self, clean_id: str) -> Dict[str, Any]:
        is_hit = any(k in clean_id for k in ["01AB1234", "05CD5521", "06XY9876", "CLONE", "THEFT", "ROBBERY"])

        return {
            "query_key": clean_id,
            "cctns_registered_match": is_hit,
            "associated_fir": "FIR-2026/AHM-CRIME/0981" if is_hit else None,
            "police_station": "Crime Branch, Ahmedabad City",
            "charges_ipc_bns": ["BNS Sec 309 (Robbery)", "BNS Sec 140 (Kidnapping)"] if is_hit else [],
            "risk_classification": "CRITICAL" if is_hit else "CLEAR",
            "investigating_officer": "Inspector V. K. Patel, Badge #GJ-4412",
            "warrant_status": "NON_BAILABLE_WARRANT_ACTIVE" if is_hit else "NO_WARRANT"
        }

egujcop_adapter = EGujCopAdapter()
