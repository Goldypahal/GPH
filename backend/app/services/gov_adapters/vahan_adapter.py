from typing import Dict, Any, Optional
from backend.app.services.gov_adapters.base import BaseGovAdapter

class VAHANAdapter(BaseGovAdapter):
    """
    Adapter for Ministry of Road Transport and Highways (MoRTH) - VAHAN 4.0.
    Returns vehicle ownership, chassis number, engine number, insurance, and stolen status.
    """

    def __init__(self):
        super().__init__("VAHAN National Vehicle Registry", "https://vahan.parivahan.gov.in/api/v4/vehicle")

    def query(self, plate_number: str) -> Dict[str, Any]:
        cleaned = plate_number.replace("-", "").upper()
        # Representative synthetic data contract
        return {
            "service": self.service_name,
            "registration_number": cleaned,
            "owner_name": "Rameshwar Sharma (Masked per DPDP Act)",
            "vehicle_class": "Motor Car (LMV)",
            "maker_model": "Maruti Suzuki Swift VXI",
            "fuel_type": "Petrol",
            "chassis_number": f"MA3EXXXXXX{cleaned[-4:]}",
            "engine_number": f"K12MXXXX{cleaned[-4:]}",
            "registration_date": "2022-04-14",
            "fitness_valid_until": "2037-04-13",
            "insurance_status": "ACTIVE",
            "pds_commercial_carrier": False,
            "stolen_flag": True if "01AB1234" in cleaned or "06XY9876" in cleaned else False,
            "rto_jurisdiction": "GJ-01 (Ahmedabad RTO)"
        }

vahan_adapter = VAHANAdapter()
