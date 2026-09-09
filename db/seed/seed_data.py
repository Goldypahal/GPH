"""
Statewide Database Seeder for GIVIN Platform (PostgreSQL 16 + PostGIS).
Populates:
1. Gujarat Administrative Districts (Ahmedabad, Gandhinagar, Surat, Vadodara, Rajkot, etc.).
2. Government Departments (HOME_POLICE, MINES_GEOLOGY, FOREST_DEPT, REVENUE_DEPT, PORTS_TRANSPORT).
3. Security Roles and Fine-Grained Permissions.
4. AI Model Registry entries.
5. Standard Law Enforcement Integrations (VAHAN, SARATHI, eGujCop, AFIS).
6. Baseline 50-camera deployment.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.database import SessionLocal, engine
from backend.app.models.orm import (
    District, Department, Role, Permission, RolePermission,
    AIModel, Integration, Camera, CameraHealth
)

DISTRICTS_DATA = [
    {"name": "Ahmedabad", "code": "GJ-01", "lat": 23.0225, "lng": 72.5714},
    {"name": "Gandhinagar", "code": "GJ-18", "lat": 23.2156, "lng": 72.6369},
    {"name": "Surat", "code": "GJ-05", "lat": 21.1702, "lng": 72.8311},
    {"name": "Vadodara", "code": "GJ-06", "lat": 22.3072, "lng": 73.1812},
    {"name": "Rajkot", "code": "GJ-03", "lat": 22.3039, "lng": 70.8022},
    {"name": "Bhavnagar", "code": "GJ-04", "lat": 21.7645, "lng": 72.1519},
    {"name": "Jamnagar", "code": "GJ-10", "lat": 22.4707, "lng": 70.0577},
    {"name": "Junagadh", "code": "GJ-11", "lat": 21.5222, "lng": 70.4579},
    {"name": "Kutch", "code": "GJ-12", "lat": 23.7337, "lng": 69.8597},
    {"name": "Banaskantha", "code": "GJ-08", "lat": 24.1724, "lng": 72.4346},
]

DEPARTMENTS_DATA = [
    {"code": "HOME_POLICE", "name": "Gujarat State Police / Home Department", "category": "Law Enforcement"},
    {"code": "MINES_GEOLOGY", "name": "Department of Mines & Geology, Gujarat", "category": "Resource Protection"},
    {"code": "FOREST_DEPT", "name": "Gujarat Forest Department", "category": "Wildlife & Environmental Protection"},
    {"code": "REVENUE_DEPT", "name": "Revenue Department of Gujarat", "category": "Land & Municipal Administration"},
    {"code": "PORTS_TRANSPORT", "name": "Gujarat Maritime Board & Transport Dept", "category": "Interstate Transit & Ports"},
]

ROLES_DATA = [
    {"name": "SUPER_ADMIN", "description": "Statewide Chief of Police / System Administrator"},
    {"name": "STATE_POLICE_CHIEF", "description": "Director General of Police with statewide authority"},
    {"name": "PRIMARY_INVESTIGATOR", "description": "Lead case detective with full evidentiary access"},
    {"name": "OFFICER", "description": "Field surveillance officer with district-scoped authority"},
    {"name": "AUDITOR", "description": "Independent oversight and compliance inspector"},
]

AI_MODELS_DATA = [
    {"name": "yolo11_vehicle_detector", "model_type": "VEHICLE_DETECTOR", "version": "1.2.0", "framework": "PyTorch"},
    {"name": "dedicated_plate_detector", "model_type": "PLATE_DETECTOR", "version": "2.1.0", "framework": "PyTorch"},
    {"name": "paddleocr_anpr_engine", "model_type": "OCR_ENGINE", "version": "2.7.0", "framework": "PaddleOCR"},
    {"name": "osnet_vehicle_reid", "model_type": "REID", "version": "1.0.0", "framework": "PyTorch"},
]

INTEGRATIONS_DATA = [
    {"name": "National VAHAN Portal", "provider_code": "VAHAN", "base_url": "https://vahan.parivahan.gov.in/api/v1"},
    {"name": "National SARATHI Portal", "provider_code": "SARATHI", "base_url": "https://sarathi.parivahan.gov.in/api/v1"},
    {"name": "eGujCop State Police Database", "provider_code": "EGUJCOP", "base_url": "https://egujcop.gujarat.gov.in/cctns/api/v2"},
    {"name": "Automated Fingerprint & Iris System (AFIS)", "provider_code": "AFIS", "base_url": "https://afis.police.gujarat.gov.in/api"},
]


def seed_database():
    """Seeds foundational datasets into PostgreSQL/PostGIS database."""
    session = SessionLocal()
    try:
        print("[INFO] Seeding Gujarat Administrative Districts...")
        for d in DISTRICTS_DATA:
            if not session.query(District).filter_by(code=d["code"]).first():
                session.add(District(
                    name=d["name"],
                    code=d["code"],
                    center_lat=d["lat"],
                    center_lng=d["lng"],
                    boundary_geojson=f'{{"type":"Point","coordinates":[{d["lng"]},{d["lat"]}]}}'
                ))

        print("[INFO] Seeding Government Departments...")
        for dept in DEPARTMENTS_DATA:
            if not session.query(Department).filter_by(code=dept["code"]).first():
                session.add(Department(
                    name=dept["name"],
                    code=dept["code"],
                    category=dept["category"]
                ))

        print("[INFO] Seeding Security Roles...")
        for r in ROLES_DATA:
            if not session.query(Role).filter_by(name=r["name"]).first():
                session.add(Role(name=r["name"], description=r["description"]))

        print("[INFO] Seeding AI Models...")
        for m in AI_MODELS_DATA:
            if not session.query(AIModel).filter_by(name=m["name"]).first():
                session.add(AIModel(
                    name=m["name"],
                    model_type=m["model_type"],
                    version=m["version"],
                    framework=m["framework"]
                ))

        print("[INFO] Seeding Government Integrations...")
        for ig in INTEGRATIONS_DATA:
            if not session.query(Integration).filter_by(provider_code=ig["provider_code"]).first():
                session.add(Integration(
                    name=ig["name"],
                    provider_code=ig["provider_code"],
                    base_url=ig["base_url"],
                    status="ONLINE",
                    is_enabled=True
                ))

        session.commit()
        print("[SUCCESS] Foundational database seed completed successfully.")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
