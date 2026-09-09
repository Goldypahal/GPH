from typing import Dict, Any
from backend.app.services.gov_adapters.base import BaseGovAdapter

class VAHANAdapter(BaseGovAdapter):
    """
    Adapter for Ministry of Road Transport and Highways (MoRTH) - VAHAN 4.0.
    Returns vehicle ownership, chassis number, engine number, insurance, and stolen status.
    """

    def __init__(self):
        super().__init__("VAHAN National Vehicle Registry", "https://vahan.parivahan.gov.in/api/v4/vehicle")

    def _fetch_data(self, clean_id: str) -> Dict[str, Any]:
        is_stolen = any(k in clean_id for k in ["01AB1234", "06XY9876", "CLONE", "THEFT"])
        return {
            "registration_number": clean_id,
            "owner_name": "Rameshwar Sharma (Masked per DPDP Act)",
            "vehicle_class": "Motor Car (LMV)",
            "maker_model": "Maruti Suzuki Swift VXI",
            "fuel_type": "Petrol",
            "chassis_number": f"MA3EXXXXXX{clean_id[-4:] if len(clean_id) >= 4 else '0000'}",
            "engine_number": f"K12MXXXX{clean_id[-4:] if len(clean_id) >= 4 else '0000'}",
            "registration_date": "2022-04-14",
            "fitness_valid_until": "2037-04-13",
            "insurance_status": "ACTIVE",
            "pds_commercial_carrier": False,
            "stolen_flag": is_stolen,
            "rto_jurisdiction": "GJ-01 (Ahmedabad RTO)"
        }

vahan_adapter = VAHANAdapter()
