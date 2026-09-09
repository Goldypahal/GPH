from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class AFISNAFISAdapter(BaseGovAdapter):
    """
    Adapter for National Automated Fingerprint Identification System (NAFIS)
    and Automated Facial Recognition System (AFIS) under NCRB / Gujarat CID.
    """
    def __init__(self):
        super().__init__("AFIS / NAFIS Biometric Identification", "https://ncrb.gov.in/nafis/api/v1/identify")

    def query(self, suspect_id_or_plate: str) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "query_target": suspect_id_or_plate,
            "biometric_reference_match": True if "GJ01AB1234" in suspect_id_or_plate else False,
            "suspect_alias": "Vikram @ Vicky Shooter" if "GJ01AB1234" in suspect_id_or_plate else None,
            "fingerprint_confidence": 0.94 if "GJ01AB1234" in suspect_id_or_plate else 0.0,
            "facial_reid_confidence": 0.89 if "GJ01AB1234" in suspect_id_or_plate else 0.0,
            "custody_history": "Previous arrest record: Gujarat State CID Crime (2023)",
            "status": "RED_CORNER_NOTICE_STATEWIDE" if "GJ01AB1234" in suspect_id_or_plate else "CLEAR"
        }

afis_adapter = AFISNAFISAdapter()
