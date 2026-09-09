from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class AFISNAFISAdapter(BaseGovAdapter):
    """
    Adapter for National Automated Fingerprint Identification System (NAFIS)
    and Automated Facial Recognition System (AFIS) under NCRB / Gujarat CID.
    """
    def __init__(self):
        super().__init__("AFIS / NAFIS Biometric Identification", "https://ncrb.gov.in/nafis/api/v1/identify")

    def _fetch_data(self, clean_id: str) -> Dict[str, Any]:
        is_match = any(k in clean_id for k in ["01AB1234", "VIKRAM", "SHOOTER"])
        return {
            "query_target": clean_id,
            "biometric_reference_match": is_match,
            "suspect_alias": "Vikram @ Vicky Shooter" if is_match else None,
            "fingerprint_confidence": 0.94 if is_match else 0.0,
            "facial_reid_confidence": 0.89 if is_match else 0.0,
            "custody_history": "Previous arrest record: Gujarat State CID Crime (2023)" if is_match else "No prior arrests",
            "status": "RED_CORNER_NOTICE_STATEWIDE" if is_match else "CLEAR"
        }

afis_adapter = AFISNAFISAdapter()
