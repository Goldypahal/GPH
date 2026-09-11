import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.orm import Department, Camera, CameraHealth, VehicleSighting, Watchlist, Alert, AuditLog, User, Case, CaseTimelineEntry, CaseEvidence
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.security import generate_sha256_hash, generate_evidence_certificate_hash, hash_password

# 26 Gujarat Government Departments
DEPARTMENTS_DATA = [
    {"name": "Home Department (Gujarat Police)", "code": "HOME_POLICE", "category": "Law Enforcement & Traffic"},
    {"name": "Food, Civil Supplies & Consumer Affairs", "code": "FCSCA", "category": "Godowns & PDS Distribution"},
    {"name": "Ports and Transport Department (RTO)", "code": "RTO_TRANS", "category": "Checkpoints & Testing Tracks"},
    {"name": "Ahmedabad Municipal Corporation", "code": "AMC", "category": "Urban Governance"},
    {"name": "Surat Municipal Corporation", "code": "SMC", "category": "Urban Governance"},
    {"name": "Vadodara Municipal Corporation", "code": "VMC", "category": "Urban Governance"},
    {"name": "Rajkot Municipal Corporation", "code": "RMC", "category": "Urban Governance"},
    {"name": "Gujarat Maritime Board (Ports)", "code": "GMB", "category": "Port & Coastal Security"},
    {"name": "Forest and Environment Department", "code": "FOREST", "category": "Wildlife & Forest Checkpoints"},
    {"name": "Mines and Minerals Department", "code": "MINES", "category": "Mining Surveillance & Weighbridges"},
    {"name": "Roads and Buildings Department (R&B)", "code": "R_AND_B", "category": "State Highways & Bridges"},
    {"name": "Gujarat State Road Transport Corp (GSRTC)", "code": "GSRTC", "category": "Bus Stations & Depots"},
    {"name": "Health & Family Welfare Department", "code": "HEALTH", "category": "Civil Hospitals & Clinics"},
    {"name": "Education Department", "code": "EDU", "category": "Universities & Examination Centers"},
    {"name": "Energy & Petrochemicals Department", "code": "ENERGY", "category": "Substations & Refineries"},
    {"name": "Revenue Department", "code": "REVENUE", "category": "Collectorates & Taluka Offices"},
    {"name": "Tourism Corporation of Gujarat (TCGL)", "code": "TOURISM", "category": "Heritage & Pilgrimage Sites"},
    {"name": "Agriculture, Farmers Welfare & Co-operation", "code": "AGRI", "category": "APMC Markets"},
    {"name": "Industries and Mines Department", "code": "GIDC", "category": "Industrial Estates (GIDC)"},
    {"name": "Urban Development & Urban Housing", "code": "UDD", "category": "Smart Cities"},
    {"name": "Panchayat, Rural Housing & Development", "code": "RURAL", "category": "Gram Panchayats"},
    {"name": "Water Resources Department (Narmada)", "code": "WATER", "category": "Canals & Dam Sites"},
    {"name": "Tribal Development Department", "code": "TRIBAL", "category": "Border District Hostels"},
    {"name": "Labour, Skill Development & Employment", "code": "LABOUR", "category": "ITI & Skill Centers"},
    {"name": "Science & Technology Department", "code": "DST", "category": "GIFT City & Science City"},
    {"name": "Gujarat State Disaster Management (GSDMA)", "code": "GSDMA", "category": "Emergency Operations"}
]

# 50 Geographically Distributed Heterogeneous Cameras across Gujarat
CAMERAS_DATA = [
    # Ahmedabad District (6 Cameras)
    {"code": "CAM-GJ-AHM-01", "name": "SG Highway - Iscon Crossroad ANPR", "dept": "HOME_POLICE", "district": "Ahmedabad", "loc": "SG Highway, Iscon Crossroad", "lat": 23.0298, "lng": 72.5074, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-AHM-02", "name": "C.G. Road - Stadium Circle PTZ", "dept": "HOME_POLICE", "district": "Ahmedabad", "loc": "Navrangpura, Stadium Circle", "lat": 23.0416, "lng": 72.5607, "vendor": "Dahua", "vms": "Genetec", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-AHM-03", "name": "Kalupur Railway Station Plaza", "dept": "AMC", "district": "Ahmedabad", "loc": "Kalupur Central Gate", "lat": 23.0245, "lng": 72.5997, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-AHM-04", "name": "RTO Subhash Bridge Test Track", "dept": "RTO_TRANS", "district": "Ahmedabad", "loc": "RTO Compound, Subhash Bridge", "lat": 23.0642, "lng": 72.5852, "vendor": "Axis", "vms": "Nx Witness", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-AHM-05", "name": "Sanand GIDC Toll Gate West", "dept": "GIDC", "district": "Ahmedabad", "loc": "Sanand GIDC Gate 2", "lat": 22.9867, "lng": 72.3789, "vendor": "Honeywell", "vms": "Qognify", "proto": "VMS-API", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-AHM-06", "name": "Bavla PDS Central Food Godown", "dept": "FCSCA", "district": "Ahmedabad", "loc": "State Warehouse, Bavla Road", "lat": 22.8361, "lng": 72.3611, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Gandhinagar District (4 Cameras)
    {"code": "CAM-GJ-GND-01", "name": "CH-0 Circle Highway Surveillance", "dept": "HOME_POLICE", "district": "Gandhinagar", "loc": "CH-0 Circle, Gandhinagar", "lat": 23.1895, "lng": 72.6358, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-GND-02", "name": "Infocity IT Park Outer Ring ANPR", "dept": "DST", "district": "Gandhinagar", "loc": "Infocity Gate 1, Kudasan", "lat": 23.1952, "lng": 72.6288, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-GND-03", "name": "GIFT City Access Tollway South", "dept": "DST", "district": "Gandhinagar", "loc": "GIFT City Gate 3", "lat": 23.1610, "lng": 72.6842, "vendor": "Hanwha", "vms": "Milestone", "proto": "ONVIF", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-GND-04", "name": "Sector 10 State Secretariat Entrance", "dept": "HOME_POLICE", "district": "Gandhinagar", "loc": "New Sachivalaya Gate 4", "lat": 23.2185, "lng": 72.6591, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},

    # Vadodara District (5 Cameras)
    {"code": "CAM-GJ-BRC-01", "name": "Golden Crossroads NH-48 ANPR", "dept": "HOME_POLICE", "district": "Vadodara", "loc": "NH-48 Golden Chowkdi", "lat": 22.3482, "lng": 73.2341, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BRC-02", "name": "Sayajigunj Station Roundabout", "dept": "VMC", "district": "Vadodara", "loc": "Sayajigunj Circle", "lat": 22.3089, "lng": 73.1892, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BRC-03", "name": "Makarpura GIDC Checkpoint", "dept": "GIDC", "district": "Vadodara", "loc": "Makarpura Industrial Gate", "lat": 22.2536, "lng": 73.1947, "vendor": "Dahua", "vms": "Nx Witness", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BRC-04", "name": "Chhani PDS Food Distribution Center", "dept": "FCSCA", "district": "Vadodara", "loc": "Chhani PDS Depot", "lat": 22.3612, "lng": 73.1764, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "DEGRADED", "res": "720p"},
    {"code": "CAM-GJ-BRC-05", "name": "Vadodara RTO Vehicle Inspection Track", "dept": "RTO_TRANS", "district": "Vadodara", "loc": "Warasiya Ring Road", "lat": 22.3274, "lng": 73.2201, "vendor": "Honeywell", "vms": "Qognify", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},

    # Surat District (5 Cameras)
    {"code": "CAM-GJ-SRT-01", "name": "Kamrej Toll Plaza NH-48", "dept": "HOME_POLICE", "district": "Surat", "loc": "Kamrej Toll Plaza North", "lat": 21.2721, "lng": 72.9612, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-SRT-02", "name": "Ring Road Textile Market Crossing", "dept": "SMC", "district": "Surat", "loc": "Ring Road, Sahara Darwaja", "lat": 21.1963, "lng": 72.8427, "vendor": "Dahua", "vms": "Genetec", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-SRT-03", "name": "Hazira Port Heavy Vehicle Weighbridge", "dept": "GMB", "district": "Surat", "loc": "Hazira Port Ingate 1", "lat": 21.1092, "lng": 72.6358, "vendor": "Axis", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-SRT-04", "name": "Surat RTO Pal Commercial Counter", "dept": "RTO_TRANS", "district": "Surat", "loc": "Pal, Adajan RTO", "lat": 21.1891, "lng": 72.7789, "vendor": "Hanwha", "vms": "Nx Witness", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-SRT-05", "name": "Olpad PDS Regional Grain Godown", "dept": "FCSCA", "district": "Surat", "loc": "Olpad Taluka Godown", "lat": 21.3321, "lng": 72.7543, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Valsad District - Border Checkpoint (4 Cameras)
    {"code": "CAM-GJ-VLS-01", "name": "Bhilad Interstate Border Checkpost (MH)", "dept": "HOME_POLICE", "district": "Valsad", "loc": "NH-48 Bhilad Border Post", "lat": 20.2789, "lng": 72.9156, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-VLS-02", "name": "Vapi GIDC Char Rasta Traffic ANPR", "dept": "HOME_POLICE", "district": "Valsad", "loc": "Vapi Town Center", "lat": 20.3712, "lng": 72.9105, "vendor": "Dahua", "vms": "Genetec", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-VLS-03", "name": "Valsad Port Terminal Gate", "dept": "GMB", "district": "Valsad", "loc": "Valsad Coastal Jetty", "lat": 20.6123, "lng": 72.9056, "vendor": "Honeywell", "vms": "Local NVR", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-VLS-04", "name": "Umbergaon Coastal Forest Checkpoint", "dept": "FOREST", "district": "Valsad", "loc": "Umbergaon Border Post", "lat": 20.1892, "lng": 72.7612, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Dahod District - MP Border Checkpoints (4 Cameras)
    {"code": "CAM-GJ-DHD-01", "name": "Jhalod Interstate Border Checkpost (MP)", "dept": "HOME_POLICE", "district": "Dahod", "loc": "SH-14 Jhalod Post", "lat": 22.9512, "lng": 74.1567, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-DHD-02", "name": "Dahod APMC Grain Mandi Gate", "dept": "AGRI", "district": "Dahod", "loc": "APMC Yard Dahod", "lat": 22.8345, "lng": 74.2541, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-DHD-03", "name": "Dahod Railway Loco Shed Crossing", "dept": "HOME_POLICE", "district": "Dahod", "loc": "Loco Workshop Road", "lat": 22.8291, "lng": 74.2689, "vendor": "Dahua", "vms": "Local NVR", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-DHD-04", "name": "Limkheda PDS Tribal Food Depot", "dept": "FCSCA", "district": "Dahod", "loc": "Limkheda Sub-Depot", "lat": 22.8312, "lng": 73.9876, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Rajkot District (5 Cameras)
    {"code": "CAM-GJ-RAJ-01", "name": "Kuvadva Road NH-27 Entrance Toll", "dept": "HOME_POLICE", "district": "Rajkot", "loc": "Kuvadva Chowkdi", "lat": 22.3412, "lng": 70.8512, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-RAJ-02", "name": "Trikon Baug Central City Intersection", "dept": "RMC", "district": "Rajkot", "loc": "Trikon Baug Junction", "lat": 22.3005, "lng": 70.8021, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-RAJ-03", "name": "Shapar-Veraval Industrial Estate Gate", "dept": "GIDC", "district": "Rajkot", "loc": "Shapar Main Entry", "lat": 22.1895, "lng": 70.7612, "vendor": "Dahua", "vms": "Nx Witness", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-RAJ-04", "name": "Rajkot RTO Kasturbadham Test Track", "dept": "RTO_TRANS", "district": "Rajkot", "loc": "Bhavnagar Highway RTO", "lat": 22.2512, "lng": 70.8912, "vendor": "Honeywell", "vms": "Qognify", "proto": "VMS-API", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-RAJ-05", "name": "Gondal Road PDS Storage Godown", "dept": "FCSCA", "district": "Rajkot", "loc": "Gondal Bypass Warehouse", "lat": 22.2612, "lng": 70.7912, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Bhavnagar District (3 Cameras)
    {"code": "CAM-GJ-BHV-01", "name": "Alang Ship Breaking Yard In-Gate ANPR", "dept": "GMB", "district": "Bhavnagar", "loc": "Alang Gate Plot 12", "lat": 21.4123, "lng": 72.1895, "vendor": "Axis", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BHV-02", "name": "Nari Chowkdi Ahmedabad Highway Entry", "dept": "HOME_POLICE", "district": "Bhavnagar", "loc": "Nari Chowkdi Bypass", "lat": 21.7891, "lng": 72.0912, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BHV-03", "name": "Bhavnagar Old Port Jetty Weighbridge", "dept": "GMB", "district": "Bhavnagar", "loc": "Port Jetty Ingress", "lat": 21.7612, "lng": 72.1512, "vendor": "Dahua", "vms": "Local NVR", "proto": "ONVIF", "ret": 15, "stat": "ACTIVE", "res": "1080p"},

    # Jamnagar District (4 Cameras)
    {"code": "CAM-GJ-JAM-01", "name": "Reliance Refinery Gate Highway Post", "dept": "ENERGY", "district": "Jamnagar", "loc": "Motikhavdi NH-947", "lat": 22.3789, "lng": 69.8512, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-JAM-02", "name": "Digjam Circle Central City ANPR", "dept": "HOME_POLICE", "district": "Jamnagar", "loc": "Digjam Bypass Junction", "lat": 22.4512, "lng": 70.0612, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-JAM-03", "name": "Bedi Port Mineral Loading Terminal", "dept": "MINES", "district": "Jamnagar", "loc": "Bedi Wharf Gate", "lat": 22.5012, "lng": 70.0412, "vendor": "Honeywell", "vms": "Local NVR", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-JAM-04", "name": "Jamnagar RTO Lalpur Road Depot", "dept": "RTO_TRANS", "district": "Jamnagar", "loc": "Lalpur Bypass RTO", "lat": 22.4112, "lng": 70.0123, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Dwarka District (Devbhumi Dwarka) (3 Cameras)
    {"code": "CAM-GJ-DWK-01", "name": "Dwarkadhish Temple Main Perimeter Gate", "dept": "TOURISM", "district": "Dwarka", "loc": "Dwarkadhish Temple Gate", "lat": 22.2378, "lng": 68.9678, "vendor": "Hanwha", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-DWK-02", "name": "Okha Marine Jetty Port Checkpoint", "dept": "GMB", "district": "Dwarka", "loc": "Okha Ferry Terminal", "lat": 22.4678, "lng": 69.0712, "vendor": "Axis", "vms": "Genetec", "proto": "ONVIF", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-DWK-03", "name": "Kuranga Mineral Weighbridge SH-6", "dept": "MINES", "district": "Dwarka", "loc": "Kuranga SH-6 Post", "lat": 22.1123, "lng": 69.1895, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "1080p"},

    # Somnath District (Gir Somnath) (3 Cameras)
    {"code": "CAM-GJ-SMN-01", "name": "Somnath Temple Promenade Security Gate", "dept": "TOURISM", "district": "Somnath", "loc": "Somnath Temple Access Road", "lat": 20.8880, "lng": 70.4012, "vendor": "Axis", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-SMN-02", "name": "Veraval Harbor Fishing Vessel Dock", "dept": "GMB", "district": "Somnath", "loc": "Veraval Port Wharf", "lat": 20.9012, "lng": 70.3689, "vendor": "Dahua", "vms": "Local NVR", "proto": "RTSP", "ret": 15, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-SMN-03", "name": "Talala Gir Lion Sanctuary Forest Post", "dept": "FOREST", "district": "Somnath", "loc": "Talala Gir Ingress Checkpoint", "lat": 21.0512, "lng": 70.5212, "vendor": "CP Plus", "vms": "Local NVR", "proto": "RTSP", "ret": 7, "stat": "ACTIVE", "res": "720p"},

    # Kutch / Bhuj Border District (3 Cameras)
    {"code": "CAM-GJ-BHJ-01", "name": "Surajbari Toll Plaza (Kutch Gateway NH-41)", "dept": "HOME_POLICE", "district": "Bhuj", "loc": "NH-41 Surajbari Bridge", "lat": 23.2189, "lng": 70.7312, "vendor": "Hikvision", "vms": "Milestone", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-BHJ-02", "name": "Kandla Deendayal Port North Terminal", "dept": "GMB", "district": "Bhuj", "loc": "Kandla Cargo Gate 5", "lat": 23.0123, "lng": 70.2189, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"},
    {"code": "CAM-GJ-BHJ-03", "name": "Khavda Great Rann Border Outpost", "dept": "HOME_POLICE", "district": "Bhuj", "loc": "Khavda SH-45 Checkpost", "lat": 23.8412, "lng": 69.7212, "vendor": "Hanwha", "vms": "Local NVR", "proto": "ONVIF", "ret": 30, "stat": "ACTIVE", "res": "1080p"},
    {"code": "CAM-GJ-AHM-07", "name": "Sardar Vallabhbhai Patel Airport Ingress ANPR", "dept": "HOME_POLICE", "district": "Ahmedabad", "loc": "Airport Terminal 2 Access Road", "lat": 23.0734, "lng": 72.6266, "vendor": "Axis", "vms": "Genetec", "proto": "RTSP", "ret": 30, "stat": "ACTIVE", "res": "4K"}
]

# Active Representative Watchlists
WATCHLIST_DATA = [
    {
        "vehicle_number": "GJ01AB1234",
        "owner_name": "Reported: Rameshwar Sharma",
        "vehicle_make_model": "Maruti Suzuki Swift (Red)",
        "vehicle_color": "Red",
        "risk_level": "CRITICAL",
        "reason": "Vehicle involved in Inter-District Armed Robbery & Kidnapping",
        "case_fir_number": "FIR-2026/AHM-CRIME/0981",
        "registered_authority": "Gujarat Police Crime Branch / eGujCop"
    },
    {
        "vehicle_number": "GJ06XY9876",
        "owner_name": "Reported: Hardik M. Patel",
        "vehicle_make_model": "Hyundai Creta (White)",
        "vehicle_color": "White",
        "risk_level": "HIGH",
        "reason": "Stolen Luxury SUV - Serial Car Theft Syndicate Alert",
        "case_fir_number": "FIR-2026/VAD/0412",
        "registered_authority": "Vadodara City Police / VAHAN Stolen Database"
    },
    {
        "vehicle_number": "GJ05CD5521",
        "owner_name": "Alias: Vikram Builder Syndicate",
        "vehicle_make_model": "Mahindra Scorpio (Black)",
        "vehicle_color": "Black",
        "risk_level": "CRITICAL",
        "reason": "Extortion Gang Escape Vehicle - Wanted under GUJCTOC Act",
        "case_fir_number": "FIR-2026/SRT-CRIME/1105",
        "registered_authority": "Surat Police Commissionerate / eGujCop"
    },
    {
        "vehicle_number": "GJ27EF8890",
        "owner_name": "PDS Carrier: Jay Somnath Logistics",
        "vehicle_make_model": "Eicher Heavy Truck (Blue)",
        "vehicle_color": "Blue",
        "risk_level": "HIGH",
        "reason": "Diverted PDS Subsidized Grain Smuggling across State Borders",
        "case_fir_number": "FIR-2026/FCS-ENF/0074",
        "registered_authority": "Food & Civil Supplies Enforcement Cell"
    },
    {
        "vehicle_number": "GJ18ZZ4321",
        "owner_name": "Unknown Driver",
        "vehicle_make_model": "Tata Nexon (Dark Blue)",
        "vehicle_color": "Blue",
        "risk_level": "HIGH",
        "reason": "Fatal Hit-and-Run on CH-0 Highway - Evading Arrest",
        "case_fir_number": "FIR-2026/GND/0663",
        "registered_authority": "Gandhinagar Traffic Police"
    },
    {
        "vehicle_number": "GJ03KL6654",
        "owner_name": "Kantilal Sand Suppliers",
        "vehicle_make_model": "Tata Tipper Dumper (Yellow)",
        "vehicle_color": "Yellow",
        "risk_level": "HIGH",
        "reason": "Illegal Sand Mining from Bhadar Riverbed - Evaded Checkpost",
        "case_fir_number": "FIR-2026/MINES-RAJ/0219",
        "registered_authority": "Mines & Geology Department, Rajkot"
    },
    {
        "vehicle_number": "GJ10MN7711",
        "owner_name": "Bedi Transports",
        "vehicle_make_model": "Toyota Innova (Silver)",
        "vehicle_color": "Silver",
        "risk_level": "MEDIUM",
        "reason": "Commercial Vehicle Tax Default & Forged Registration Plate",
        "case_fir_number": "RTO-JAM-NOTICE/2026-881",
        "registered_authority": "RTO Jamnagar Enforcement Wing"
    }
]

def seed_database():
    """Seeds the database with all 26 departments, 50 cameras, watchlists, and vehicle journeys."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Ensure all tables created
        Base.metadata.create_all(bind=engine)

        # Check if users need seeding
        if db.query(User).count() == 0:
            print("Seeding RBAC Users...")
            default_users = [
                {
                    "username": "admin",
                    "email": "admin@gujarat.gov.in",
                    "full_name": "State Command Director",
                    "role": "SUPER_ADMIN",
                    "jurisdiction_district": None,
                    "department_code": "HOME_POLICE",
                    "password": "password123"
                },
                {
                    "username": "inspector_patel",
                    "email": "v.patel@gujaratpolice.gov.in",
                    "full_name": "Inspector Vikram Patel",
                    "role": "INVESTIGATOR",
                    "jurisdiction_district": "Ahmedabad",
                    "department_code": "HOME_POLICE",
                    "password": "password123"
                },
                {
                    "username": "operator_shah",
                    "email": "p.shah@gujaratpolice.gov.in",
                    "full_name": "Operator Priya Shah",
                    "role": "CONTROL_ROOM_OPERATOR",
                    "jurisdiction_district": "Ahmedabad",
                    "department_code": "HOME_POLICE",
                    "password": "password123"
                },
                {
                    "username": "sp_surat",
                    "email": "sp.surat@gujaratpolice.gov.in",
                    "full_name": "SP R.K. Mehta",
                    "role": "DISTRICT_OFFICER",
                    "jurisdiction_district": "Surat",
                    "department_code": "HOME_POLICE",
                    "password": "password123"
                },
                {
                    "username": "auditor_desai",
                    "email": "auditor@gujarat.gov.in",
                    "full_name": "Dr. K. Desai (Home Dept Vigilance)",
                    "role": "AUDITOR",
                    "jurisdiction_district": None,
                    "department_code": "HOME_POLICE",
                    "password": "password123"
                }
            ]
            for u in default_users:
                user_obj = User(
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    jurisdiction_district=u["jurisdiction_district"],
                    department_code=u["department_code"],
                    password_hash=hash_password(u["password"]),
                    is_active=True
                )
                db.add(user_obj)
            db.commit()
            print("RBAC Users seeded successfully.")

        # Check if cases need seeding
        if db.query(Case).count() == 0:
            print("Seeding Sample Investigation Case...")
            sample_case = Case(
                case_number="CASE-2026-GJ-0042",
                title="Silver Swift Interstate Interception & Grand Larceny",
                fir_number="CR-I/2026/0491",
                status="INVESTIGATING",
                priority="CRITICAL",
                assigned_investigator="Inspector Vikram Patel",
                jurisdiction_district="Ahmedabad",
                target_vehicle_plate="GJ01AB1234",
                created_from_alert_id="ALT-SEED-01",
                description="Vehicle flagged at multiple NH-48 checkposts. Trajectory verified from SG Highway to Bhilad Interstate Border."
            )
            db.add(sample_case)
            db.flush()

            sample_entries = [
                ("INVESTIGATION_INITIATED", "Case opened following real-time alert trigger at SG Highway ANPR."),
                ("ROUTE_VERIFIED", "Cross-camera multi-hop trajectory confirmed: Ahmedabad -> Vadodara -> Surat -> Valsad (Bhilad Checkpost). Implied speed within legal thresholds (avg 78.4 km/h)."),
                ("GOV_INTEL_FETCHED", "eGujCop criminal record match verified: 2 previous vehicle theft priors linked to target.")
            ]
            for title, note in sample_entries:
                tl = CaseTimelineEntry(
                    case_id=sample_case.id,
                    entry_type="NOTE",
                    title=title,
                    content=note,
                    created_by="Inspector Vikram Patel"
                )
                db.add(tl)
            db.commit()
            print("Sample Case seeded successfully.")

        # Check if already seeded base data
        # 1. Departments
        dept_map = {d.code: d.id for d in db.query(Department).all()}
        if not dept_map:
            print("=== Seeding 26 Gujarat Government Departments ===")
            for d in DEPARTMENTS_DATA:
                dept = Department(
                    name=d["name"],
                    code=d["code"],
                    category=d["category"],
                    contact_email=f"cctv.{d['code'].lower()}@gujarat.gov.in",
                    contact_phone="+91-79-23250000"
                )
                db.add(dept)
                db.flush()
                dept_map[d["code"]] = dept.id
            db.commit()

        # 2. Cameras
        cam_code_map = {c.logical_camera_id: c.id for c in db.query(Camera).all()}
        if not cam_code_map:
            print("=== Seeding 50 Heterogeneous Cameras ===")
            for c in CAMERAS_DATA:
                dept_id = dept_map.get(c["dept"], list(dept_map.values())[0])
                cam = Camera(
                    logical_camera_id=c["code"],
                    name=c["name"],
                    department_id=dept_id,
                    district=c["district"],
                    location_name=c["loc"],
                    lat=c["lat"],
                    lng=c["lng"],
                    altitude=18.5,
                    fov_angle=90.0,
                    fov_range_m=120.0,
                    vendor=c["vendor"],
                    model=f"{c['vendor']}-PRO-{c['res']}",
                    camera_type="IP ANPR High-Speed",
                    resolution=c["res"],
                    fps=25,
                    protocol=c["proto"],
                    stream_url=f"/api/cameras/stream/{c['code']}",
                    vms_type=c["vms"],
                    storage_type="Local NVR / Edge Buffer",
                    retention_days=c["ret"],
                    status=c["stat"],
                    is_public_domain=True
                )
                db.add(cam)
                db.flush()
                cam_code_map[c["code"]] = cam.id

                # Create Camera Health record
                health = CameraHealth(
                    camera_id=cam.id,
                    last_seen=datetime.now(timezone.utc),
                    latency_ms=38 if c["stat"] == "ACTIVE" else 145,
                    packet_loss=0.1 if c["stat"] == "ACTIVE" else 2.5,
                    cpu_usage=28.0 if c["stat"] == "ACTIVE" else 88.0,
                    memory_usage=44.0,
                    status="ONLINE" if c["stat"] == "ACTIVE" else "DEGRADED"
                )
                db.add(health)
            db.commit()

        # 3. Watchlists
        wl_map = {w.vehicle_number: w for w in db.query(Watchlist).all()}
        if len(wl_map) < len(WATCHLIST_DATA):
            print("=== Seeding Representative Watchlists ===")
            for w in WATCHLIST_DATA:
                if w["vehicle_number"] not in wl_map:
                    wl = Watchlist(
                        list_name="State Police Central Hotlist",
                        entity_type="VEHICLE",
                        vehicle_number=w["vehicle_number"],
                        owner_name=w["owner_name"],
                        vehicle_make_model=w["vehicle_make_model"],
                        vehicle_color=w["vehicle_color"],
                        risk_level=w["risk_level"],
                        reason=w["reason"],
                        case_fir_number=w["case_fir_number"],
                        registered_authority=w["registered_authority"],
                        status="ACTIVE"
                    )
                    db.add(wl)
                    db.flush()
                    wl_map[w["vehicle_number"]] = wl
            db.commit()

        # 4. Multi-Camera Journey for GJ01AB1234
        if db.query(VehicleSighting).filter(VehicleSighting.plate_text == "GJ01AB1234").count() < 5:
            print("=== Seeding Multi-Camera Journey for Designated Test Vehicle (GJ01AB1234) ===")
            # Scenario: Robbery vehicle GJ01AB1234 travelled from Ahmedabad through Gandhinagar, Vadodara, Surat to Valsad border
            now = datetime.now(timezone.utc)
            test_journey_cams = [
                ("CAM-GJ-AHM-01", now - timedelta(hours=4, minutes=45), 54.0, "Car", "Red"),
                ("CAM-GJ-GND-01", now - timedelta(hours=3, minutes=50), 68.0, "Car", "Red"),
                ("CAM-GJ-BRC-01", now - timedelta(hours=2, minutes=30), 78.0, "Car", "Red"),
                ("CAM-GJ-SRT-01", now - timedelta(hours=1, minutes=15), 82.0, "Car", "Red"),
                ("CAM-GJ-VLS-01", now - timedelta(minutes=18), 71.0, "Car", "Red")
            ]

            stolen_wl = wl_map.get("GJ01AB1234")
            last_sighting_id = None

            for cam_code, s_time, speed, vtype, color in test_journey_cams:
                cam_id = cam_code_map.get(cam_code)
                if not cam_id:
                    continue

                raw_crop_data = f"PLATE:GJ01AB1234:{cam_code}:{s_time.isoformat()}".encode()
                img_hash = generate_sha256_hash(raw_crop_data)
                
                sighting = VehicleSighting(
                    plate_text="GJ01AB1234",
                    normalized_plate="GJ01AB1234",
                    camera_id=cam_id,
                    timestamp=s_time,
                    confidence=0.96,
                    vehicle_type=vtype,
                    vehicle_color=color,
                    speed_kmh=speed,
                    direction="Southbound (towards Mumbai)",
                    evidence_uri=f"/api/analytics/evidence/{img_hash[:16]}.jpg",
                    evidence_hash=img_hash
                )
                db.add(sighting)
                db.flush()
                last_sighting_id = sighting.id

            # Also seed other normal traffic sightings for rich demonstration
            extra_vehicles = [
                ("GJ06XY9876", "CAM-GJ-BRC-01", now - timedelta(hours=1, minutes=10), 65.0, "SUV", "White", "HIGH"),
                ("GJ05CD5521", "CAM-GJ-SRT-02", now - timedelta(minutes=42), 52.0, "SUV", "Black", "CRITICAL"),
                ("GJ27EF8890", "CAM-GJ-DHD-01", now - timedelta(hours=2, minutes=5), 45.0, "Truck", "Blue", "HIGH"),
                ("GJ18ZZ4321", "CAM-GJ-GND-02", now - timedelta(minutes=30), 60.0, "Car", "Blue", "HIGH"),
                ("GJ03KL6654", "CAM-GJ-RAJ-01", now - timedelta(hours=3, minutes=12), 40.0, "Truck", "Yellow", "HIGH"),
                # Normal innocent vehicles:
                ("GJ01KJ9988", "CAM-GJ-AHM-02", now - timedelta(minutes=15), 48.0, "Car", "Silver", None),
                ("GJ05RT1122", "CAM-GJ-SRT-01", now - timedelta(minutes=8), 75.0, "Car", "White", None),
                ("GJ10AB4455", "CAM-GJ-JAM-01", now - timedelta(minutes=5), 62.0, "SUV", "Grey", None),
                ("GJ11QQ7890", "CAM-GJ-SMN-01", now - timedelta(minutes=2), 35.0, "Car", "Red", None)
            ]

            for plate, cam_code, s_time, speed, vtype, color, risk in extra_vehicles:
                cam_id = cam_code_map.get(cam_code)
                if not cam_id:
                    continue

                raw_crop = f"PLATE:{plate}:{cam_code}:{s_time.isoformat()}".encode()
                h = generate_sha256_hash(raw_crop)
                norm = ANPREngine.normalize_plate(plate)

                sighting = VehicleSighting(
                    plate_text=plate,
                    normalized_plate=norm,
                    camera_id=cam_id,
                    timestamp=s_time,
                    confidence=0.94,
                    vehicle_type=vtype,
                    vehicle_color=color,
                    speed_kmh=speed,
                    direction="In-Transit",
                    evidence_uri=f"/api/analytics/evidence/{h[:16]}.jpg",
                    evidence_hash=h
                )
                db.add(sighting)
                db.flush()

                # If it's a watchlist vehicle, create an active Alert
                if risk and plate in wl_map:
                    matched_wl = wl_map[plate]
                    alert_uid = f"ALT-{s_time.strftime('%Y%m%d%H%M%S')}-{sighting.id[:4].upper()}"
                    alert = Alert(
                        alert_uid=alert_uid,
                        watchlist_id=matched_wl.id,
                        sighting_id=sighting.id,
                        camera_id=cam_id,
                        plate_text=plate,
                        risk_level=risk,
                        status="NEW",
                        remarks=f"Real-time ANPR Match against eGujCop / VAHAN Hotlist. Reason: {matched_wl.reason} [FIR: {matched_wl.case_fir_number}]",
                        dispatched_unit=None
                    )
                    db.add(alert)

            # Create alert for the last sighting of designated test vehicle GJ01AB1234
            if last_sighting_id and stolen_wl:
                alert_uid = f"ALT-{now.strftime('%Y%m%d%H%M%S')}-VLS1"
                vls_cam_id = cam_code_map.get("CAM-GJ-VLS-01", list(cam_code_map.values())[0])
                desig_alert = Alert(
                    alert_uid=alert_uid,
                    watchlist_id=stolen_wl.id,
                    sighting_id=last_sighting_id,
                    camera_id=vls_cam_id,
                    plate_text="GJ01AB1234",
                    risk_level="CRITICAL",
                    status="NEW",
                    remarks="SUSPECT DETECTED AT BORDER CHECKPOINT! Moving Southbound on NH-48 towards Maharashtra border.",
                    dispatched_unit="PCR Van 12 (Bhilad Outpost)"
                )
                db.add(desig_alert)

            db.commit()


        # Create Default RBAC Users
        print("Seeding RBAC Users...")
        default_users = [
            {
                "username": "admin",
                "email": "admin@gujarat.gov.in",
                "full_name": "State Command Director",
                "role": "SUPER_ADMIN",
                "jurisdiction_district": None,
                "department_code": "HOME_POLICE",
                "password": "password123"
            },
            {
                "username": "inspector_patel",
                "email": "v.patel@gujaratpolice.gov.in",
                "full_name": "Inspector Vikram Patel",
                "role": "INVESTIGATOR",
                "jurisdiction_district": "Ahmedabad",
                "department_code": "HOME_POLICE",
                "password": "password123"
            },
            {
                "username": "operator_shah",
                "email": "p.shah@gujaratpolice.gov.in",
                "full_name": "Operator Priya Shah",
                "role": "CONTROL_ROOM_OPERATOR",
                "jurisdiction_district": "Ahmedabad",
                "department_code": "HOME_POLICE",
                "password": "password123"
            },
            {
                "username": "sp_surat",
                "email": "sp.surat@gujaratpolice.gov.in",
                "full_name": "SP R.K. Mehta",
                "role": "DISTRICT_OFFICER",
                "jurisdiction_district": "Surat",
                "department_code": "HOME_POLICE",
                "password": "password123"
            },
            {
                "username": "auditor_desai",
                "email": "auditor@gujarat.gov.in",
                "full_name": "Dr. K. Desai (Home Dept Vigilance)",
                "role": "AUDITOR",
                "jurisdiction_district": None,
                "department_code": "HOME_POLICE",
                "password": "password123"
            }
        ]

        for u in default_users:
            existing_user = db.query(User).filter(User.username == u["username"]).first()
            if not existing_user:
                user_obj = User(
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    jurisdiction_district=u["jurisdiction_district"],
                    department_code=u["department_code"],
                    password_hash=hash_password(u["password"]),
                    is_active=True
                )
                db.add(user_obj)

        # Create Sample Investigation Case
        print("Seeding Sample Investigation Case...")
        existing_case = db.query(Case).filter(Case.case_number == "CASE-2026-GJ-0042").first()
        if not existing_case:
            sample_case = Case(
                case_number="CASE-2026-GJ-0042",
                title="Silver Swift Interstate Interception & Grand Larceny",
                fir_number="CR-I/2026/0491",
                status="INVESTIGATING",
                priority="CRITICAL",
                assigned_investigator="Inspector Vikram Patel",
                jurisdiction_district="Ahmedabad",
                target_vehicle_plate="GJ01AB1234",
                created_from_alert_id="ALT-SEED-01",
                description="Vehicle flagged at multiple NH-48 checkposts. Trajectory verified from SG Highway to Bhilad Interstate Border."
            )
            db.add(sample_case)
            db.flush()

            # Add Timeline Entries to Case
            sample_entries = [
                ("INVESTIGATION_INITIATED", "Case opened following real-time alert trigger at SG Highway ANPR."),
                ("ROUTE_VERIFIED", "Cross-camera multi-hop trajectory confirmed: Ahmedabad -> Vadodara -> Surat -> Valsad (Bhilad Checkpost). Implied speed within legal thresholds (avg 78.4 km/h)."),
                ("GOV_INTEL_FETCHED", "eGujCop criminal record match verified: 2 previous vehicle theft priors linked to target.")
            ]
            for title, note in sample_entries:
                tl = CaseTimelineEntry(
                    case_id=sample_case.id,
                    entry_type="NOTE",
                    title=title,
                    content=note,
                    created_by="Inspector Vikram Patel"
                )
                db.add(tl)

        # Create Audit Log of Database Ingestion
        audit = AuditLog(
            user_id="SYSTEM_BOOTSTRAP",
            action="INITIAL_SEED",
            resource="DATABASE",
            details_json="{'status': 'Initialized 26 departments, 50 cameras, users, and cases'}",
            signature_hash=generate_sha256_hash(b"SYSTEM_BOOTSTRAP_COMPLETE")
        )
        db.add(audit)

        db.commit()
        print("=== Database Seeding Completed Successfully! ===")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
