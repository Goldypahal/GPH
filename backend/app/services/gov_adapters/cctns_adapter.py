"""
CCTNS (Crime and Criminal Tracking Network & Systems) National Integration Adapter.
Connects Gujarat Police to interstate FIR records, criminal profiles, and wanted persons registers.
"""

from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter, IntegrationMode


class CCTNSAdapter(BaseGovAdapter):
    """Interstate CCTNS National Database Connector."""

    def __init__(self, mode: IntegrationMode = IntegrationMode.MOCK):
        super().__init__(
            service_name="National CCTNS Interoperability Portal",
            endpoint_url="https://cctns.gov.in/api/v2/criminal-records",
            mode=mode
        )

    def _fetch_data(self, clean_id: str) -> Dict[str, Any]:
        """Queries national criminal records database by vehicle plate, suspect name, or FIR ID."""
        is_known_suspect = clean_id.startswith("GJ01") or "CRIME" in clean_id or clean_id.startswith("FIR")
        
        if is_known_suspect:
            return {
                "cctns_id": f"CCTNS-NAT-2026-{clean_id[-4:]}",
                "national_crime_record_found": True,
                "fir_number": f"FIR/AHM/2026/088",
                "police_station": "SG Highway Precinct 1, Ahmedabad",
                "offense_sections": ["IPC 379", "IPC 411", "BNS 303(2)"],
                "wanted_status": "ACTIVE_WARRANT",
                "interstate_flag": True,
                "registered_state": "Gujarat",
                "coordinating_agency": "CID Crime Gujarat"
            }
        
        return {
            "cctns_id": None,
            "national_crime_record_found": False,
            "wanted_status": "CLEAN",
            "interstate_flag": False
        }


cctns_adapter = CCTNSAdapter()
