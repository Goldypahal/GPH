"""
NAFIS (National Automated Fingerprint Identification System) National Biometric Adapter.
Connects to NCRB (National Crime Records Bureau) centralized fingerprint repository.
"""

from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter, IntegrationMode


class NAFISAdapter(BaseGovAdapter):
    """National NAFIS NCRB Central Biometric Database Connector."""

    def __init__(self, mode: IntegrationMode = IntegrationMode.MOCK):
        super().__init__(
            service_name="National NAFIS NCRB Biometric Registry",
            endpoint_url="https://nafis.ncrb.gov.in/api/v1/fingerprint-search",
            mode=mode
        )

    def _fetch_data(self, clean_id: str) -> Dict[str, Any]:
        """Queries national biometric database by biometric token, suspect UID, or registered vehicle."""
        has_record = "MATCH" in clean_id or clean_id.startswith("GJ01")
        
        if has_record:
            return {
                "nafis_match": True,
                "npi_number": f"NPI-NCRB-2026-{clean_id[-4:]}",
                "biometric_confidence": 0.984,
                "suspect_name": "Ramesh K. Vaghela (Alias: Munna)",
                "prior_convictions_count": 2,
                "primary_charges": ["Organized Interstate Grand Auto Theft"],
                "last_arrest_district": "Surat City",
                "biometric_modality": "Ten-Print Friction Ridge + Iris"
            }

        return {
            "nafis_match": False,
            "npi_number": None,
            "biometric_confidence": 0.0,
            "prior_convictions_count": 0
        }


nafis_adapter = NAFISAdapter()
