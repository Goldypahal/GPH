"""
33-District Partitioning & Fleet Allocation for GIVIN Statewide Scale Validation.
Distributes exactly 80,000 virtual cameras across Gujarat's 33 administrative districts:
- High-Density Metros: Ahmedabad (8,000), Surat (7,000), Vadodara (5,000), Rajkot (4,000)
- Regional Hubs & Industrial Corridors: 2,000 - 3,300 cameras
- Rural & Border Districts: 700 - 1,900 cameras
- Total = Exactly 80,000 cameras.
"""

from typing import Dict, Any, List

GUJARAT_DISTRICTS_33: List[Dict[str, Any]] = [
    {"district": "Ahmedabad", "code": "AHM", "rto": "GJ01", "region": "Ahmedabad North Hub", "lat": 23.0225, "lng": 72.5714, "cameras": 8000, "gateway_subnet": "10.240.1.0/24"},
    {"district": "Surat", "code": "SUR", "rto": "GJ05", "region": "Surat South Hub", "lat": 21.1702, "lng": 72.8311, "cameras": 7000, "gateway_subnet": "10.240.2.0/24"},
    {"district": "Vadodara", "code": "BRD", "rto": "GJ06", "region": "Vadodara Central Hub", "lat": 22.3072, "lng": 73.1812, "cameras": 5000, "gateway_subnet": "10.240.3.0/24"},
    {"district": "Rajkot", "code": "RJK", "rto": "GJ03", "region": "Rajkot Saurashtra Hub", "lat": 22.3039, "lng": 70.8022, "cameras": 4000, "gateway_subnet": "10.240.4.0/24"},
    {"district": "Gandhinagar", "code": "GND", "rto": "GJ18", "region": "Ahmedabad North Hub", "lat": 23.2156, "lng": 72.6369, "cameras": 3300, "gateway_subnet": "10.240.5.0/24"},
    {"district": "Kutch", "code": "KTC", "rto": "GJ12", "region": "Rajkot Saurashtra Hub", "lat": 23.2420, "lng": 69.6669, "cameras": 3200, "gateway_subnet": "10.240.6.0/24"},
    {"district": "Bhavnagar", "code": "BHV", "rto": "GJ04", "region": "Rajkot Saurashtra Hub", "lat": 21.7645, "lng": 72.1519, "cameras": 3000, "gateway_subnet": "10.240.7.0/24"},
    {"district": "Jamnagar", "code": "JAM", "rto": "GJ10", "region": "Rajkot Saurashtra Hub", "lat": 22.4707, "lng": 70.0577, "cameras": 2600, "gateway_subnet": "10.240.8.0/24"},
    {"district": "Junagadh", "code": "JUN", "rto": "GJ11", "region": "Rajkot Saurashtra Hub", "lat": 21.5222, "lng": 70.4579, "cameras": 2500, "gateway_subnet": "10.240.9.0/24"},
    {"district": "Bharuch", "code": "BHR", "rto": "GJ16", "region": "Surat South Hub", "lat": 21.7051, "lng": 72.9959, "cameras": 2500, "gateway_subnet": "10.240.10.0/24"},
    {"district": "Anand", "code": "AND", "rto": "GJ23", "region": "Vadodara Central Hub", "lat": 22.5645, "lng": 72.9289, "cameras": 2300, "gateway_subnet": "10.240.11.0/24"},
    {"district": "Banaskantha", "code": "BNK", "rto": "GJ08", "region": "Ahmedabad North Hub", "lat": 24.1724, "lng": 72.4346, "cameras": 2300, "gateway_subnet": "10.240.12.0/24"},
    {"district": "Mehsana", "code": "MEH", "rto": "GJ02", "region": "Ahmedabad North Hub", "lat": 23.5880, "lng": 72.3693, "cameras": 2200, "gateway_subnet": "10.240.13.0/24"},
    {"district": "Valsad", "code": "VLS", "rto": "GJ15", "region": "Surat South Hub", "lat": 20.5992, "lng": 72.9342, "cameras": 2200, "gateway_subnet": "10.240.14.0/24"},
    {"district": "Kheda", "code": "KHD", "rto": "GJ07", "region": "Vadodara Central Hub", "lat": 22.7547, "lng": 72.6836, "cameras": 2200, "gateway_subnet": "10.240.15.0/24"},
    {"district": "Devbhumi Dwarka", "code": "DWD", "rto": "GJ37", "region": "Rajkot Saurashtra Hub", "lat": 22.2442, "lng": 68.9685, "cameras": 2200, "gateway_subnet": "10.240.16.0/24"},
    {"district": "Navsari", "code": "NVS", "rto": "GJ21", "region": "Surat South Hub", "lat": 20.9467, "lng": 72.9520, "cameras": 2000, "gateway_subnet": "10.240.17.0/24"},
    {"district": "Morbi", "code": "MRB", "rto": "GJ36", "region": "Rajkot Saurashtra Hub", "lat": 22.8120, "lng": 70.8370, "cameras": 2000, "gateway_subnet": "10.240.18.0/24"},
    {"district": "Surendranagar", "code": "SRN", "rto": "GJ13", "region": "Rajkot Saurashtra Hub", "lat": 22.7278, "lng": 71.6370, "cameras": 1900, "gateway_subnet": "10.240.19.0/24"},
    {"district": "Panchmahal", "code": "PNM", "rto": "GJ17", "region": "Vadodara Central Hub", "lat": 22.7750, "lng": 73.6149, "cameras": 1900, "gateway_subnet": "10.240.20.0/24"},
    {"district": "Sabarkantha", "code": "SBK", "rto": "GJ09", "region": "Ahmedabad North Hub", "lat": 23.6041, "lng": 72.9644, "cameras": 1800, "gateway_subnet": "10.240.21.0/24"},
    {"district": "Dahod", "code": "DHD", "rto": "GJ20", "region": "Vadodara Central Hub", "lat": 22.8340, "lng": 74.2550, "cameras": 1800, "gateway_subnet": "10.240.22.0/24"},
    {"district": "Amreli", "code": "AMR", "rto": "GJ14", "region": "Rajkot Saurashtra Hub", "lat": 21.6032, "lng": 71.2221, "cameras": 1700, "gateway_subnet": "10.240.23.0/24"},
    {"district": "Gir Somnath", "code": "GSM", "rto": "GJ32", "region": "Rajkot Saurashtra Hub", "lat": 20.9042, "lng": 70.3667, "cameras": 1600, "gateway_subnet": "10.240.24.0/24"},
    {"district": "Patan", "code": "PTN", "rto": "GJ24", "region": "Ahmedabad North Hub", "lat": 23.8493, "lng": 72.1266, "cameras": 1500, "gateway_subnet": "10.240.25.0/24"},
    {"district": "Aravalli", "code": "ARV", "rto": "GJ31", "region": "Ahmedabad North Hub", "lat": 23.5414, "lng": 73.1678, "cameras": 1400, "gateway_subnet": "10.240.26.0/24"},
    {"district": "Porbandar", "code": "PBR", "rto": "GJ25", "region": "Rajkot Saurashtra Hub", "lat": 21.6417, "lng": 69.6293, "cameras": 1300, "gateway_subnet": "10.240.27.0/24"},
    {"district": "Mahisagar", "code": "MHS", "rto": "GJ35", "region": "Vadodara Central Hub", "lat": 23.1667, "lng": 73.5500, "cameras": 1300, "gateway_subnet": "10.240.28.0/24"},
    {"district": "Tapi", "code": "TAP", "rto": "GJ26", "region": "Surat South Hub", "lat": 21.1167, "lng": 73.4000, "cameras": 1200, "gateway_subnet": "10.240.29.0/24"},
    {"district": "Narmada", "code": "NRM", "rto": "GJ22", "region": "Surat South Hub", "lat": 21.8700, "lng": 73.5000, "cameras": 1200, "gateway_subnet": "10.240.30.0/24"},
    {"district": "Chhota Udaipur", "code": "CHU", "rto": "GJ34", "region": "Vadodara Central Hub", "lat": 22.3108, "lng": 74.0125, "cameras": 1100, "gateway_subnet": "10.240.31.0/24"},
    {"district": "Botad", "code": "BTD", "rto": "GJ33", "region": "Rajkot Saurashtra Hub", "lat": 22.1700, "lng": 71.6600, "cameras": 1100, "gateway_subnet": "10.240.32.0/24"},
    {"district": "Dang", "code": "DNG", "rto": "GJ30", "region": "Surat South Hub", "lat": 20.8000, "lng": 73.7000, "cameras": 700, "gateway_subnet": "10.240.33.0/24"},
]

DISTRICT_CAMERA_DISTRIBUTION: Dict[str, int] = {
    d["district"]: d["cameras"] for d in GUJARAT_DISTRICTS_33
}

TOTAL_STATEWIDE_CAMERAS = sum(DISTRICT_CAMERA_DISTRIBUTION.values())
assert TOTAL_STATEWIDE_CAMERAS == 80000, f"Expected 80000 cameras, got {TOTAL_STATEWIDE_CAMERAS}"
assert len(GUJARAT_DISTRICTS_33) == 33, f"Expected 33 districts, got {len(GUJARAT_DISTRICTS_33)}"
