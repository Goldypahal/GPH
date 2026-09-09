from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class SARATHIAdapter(BaseGovAdapter):
    """
    Adapter for MoRTH - SARTHI Driving License & Driver Registry.
    """
    def __init__(self):
        super().__init__("SARTHI Driver License Database", "https://sarathi.parivahan.gov.in/api/v1/license")

    def query(self, dl_or_plate: str) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "license_number": f"GJ01-20200019283",
            "license_holder": "K. V. Raman",
            "valid_from": "2020-01-10",
            "valid_to": "2040-01-09",
            "authorized_vehicle_classes": ["LMV", "MCWG"],
            "traffic_challan_pending_count": 2,
            "license_status": "ACTIVE_UNRESTRICTED"
        }

sarathi_adapter = SARATHIAdapter()
