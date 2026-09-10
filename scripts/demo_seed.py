"""
Deterministic Demo Seeder for GIVIN Platform (Task Group 24).
Sets up baseline state for live judge demonstration:
- Target suspect vehicle in Watchlist (GJ01AB1234)
- Verified active cameras on SG Highway corridor
- Demonstration investigator user and audit trail
"""

import sys
import os
import json
from datetime import datetime, timezone


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.orm import Camera, Watchlist, User, Department, AuditLog
from backend.app.core.security import hash_password

DEMO_PLATE = "GJ01AB1234"
DEMO_WATCHLIST_REASON = "RED_ALERT: Stolen Gold Fortuner wanted in FIR 402/2026 (Crime Branch)"


def seed_demo_environment():
    print("=== [GIVIN DEMO SEEDER] Initializing deterministic demonstration environment ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Ensure Police Department exists
        dept = db.query(Department).filter(Department.code == "HOME_POLICE").first()
        if not dept:
            dept = Department(
                name="Home Department (Gujarat Police)",
                code="HOME_POLICE",
                category="Law Enforcement & Traffic"
            )
            db.add(dept)
            db.commit()
            db.refresh(dept)
        print(f"[+] Department: {dept.name} ({dept.id})")

        # 2. Ensure Demo Investigator User exists
        investigator = db.query(User).filter(User.username == "demo_investigator").first()
        if not investigator:
            investigator = User(
                username="demo_investigator",
                email="investigator@police.gujarat.gov.in",
                full_name="Inspector R. K. Jadeja",
                password_hash=hash_password("GujaratPolice2026!"),
                role="INVESTIGATOR",
                department_code="HOME_POLICE",
                jurisdiction_district="Ahmedabad",
                is_active=True
            )
            db.add(investigator)
            db.commit()
        print(f"[+] Demo Investigator: {investigator.username} ({investigator.full_name})")


        # 3. Ensure Camera 1 (Iscon) and Camera 2 (Stadium) exist
        cam1 = db.query(Camera).filter(Camera.logical_camera_id == "CAM-GJ-AHM-01").first()
        if not cam1:
            cam1 = Camera(
                logical_camera_id="CAM-GJ-AHM-01",
                name="SG Highway - Iscon Crossroad ANPR",
                department_id=dept.id,
                district="Ahmedabad",
                location_name="SG Highway, Iscon Crossroad",
                lat=23.0298,
                lng=72.5074,
                vendor="Hikvision",
                vms_type="Milestone",
                protocol="RTSP",
                status="ACTIVE",
                resolution="1080p",
                stream_url="rtsp://localhost:8554/live/iscon"
            )
            db.add(cam1)

        cam2 = db.query(Camera).filter(Camera.logical_camera_id == "CAM-GJ-AHM-02").first()
        if not cam2:
            cam2 = Camera(
                logical_camera_id="CAM-GJ-AHM-02",
                name="C.G. Road - Stadium Circle PTZ",
                department_id=dept.id,
                district="Ahmedabad",
                location_name="Navrangpura, Stadium Circle",
                lat=23.0416,
                lng=72.5607,
                vendor="Dahua",
                vms_type="Genetec",
                protocol="RTSP",
                status="ACTIVE",
                resolution="1080p",
                stream_url="rtsp://localhost:8554/live/stadium"
            )
            db.add(cam2)
        db.commit()
        print("[+] Surveillance Nodes CAM-GJ-AHM-01 and CAM-GJ-AHM-02 ready.")

        # 4. Ensure Watchlist Entry for Suspect Vehicle
        w_entry = db.query(Watchlist).filter(Watchlist.vehicle_number == DEMO_PLATE).first()
        if not w_entry:
            w_entry = Watchlist(
                list_name="High Priority Stolen Vehicles Hotlist",
                entity_type="VEHICLE",
                vehicle_number=DEMO_PLATE,
                owner_name="Unknown Suspect",
                vehicle_make_model="Toyota Fortuner",
                vehicle_color="Gold",
                risk_level="CRITICAL",
                reason=DEMO_WATCHLIST_REASON,
                case_fir_number="FIR 402/2026 Crime Branch",
                registered_authority="Gujarat Police Crime Branch",
                status="ACTIVE",
                is_active=True
            )
            db.add(w_entry)
            db.commit()
            print(f"[+] Active Watchlist Target Enrolled: {DEMO_PLATE} (CRITICAL)")
        else:
            w_entry.is_active = True
            w_entry.status = "ACTIVE"
            db.commit()
            print(f"[+] Watchlist Target Re-activated: {DEMO_PLATE}")


        # 5. Record Audit Trail for Seeding
        import hashlib
        sig = hashlib.sha256(f"SYSTEM_DEMO_SEEDER:DEMO_SEED_COMPLETED:STATEWIDE_WATCHLIST:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
        audit = AuditLog(
            user_id="SYSTEM_DEMO_SEEDER",
            action="DEMO_SEED_COMPLETED",
            resource="STATEWIDE_WATCHLIST_AND_SURVEILLANCE",
            details_json=json.dumps({"message": f"Deterministic seed created for demonstration vehicle {DEMO_PLATE}"}),
            signature_hash=sig
        )
        db.add(audit)
        db.commit()

        print("=== [GIVIN DEMO SEEDER] Deterministic environment successfully primed ===")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
