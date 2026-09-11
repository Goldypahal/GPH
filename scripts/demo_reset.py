"""
Deterministic Demo Reset Tool for GIVIN Platform (Task Group 24).
Safely purges demonstration alerts, sightings, cases, and evidence generated during demo runs.
Preserves base infrastructure, cameras, and system configuration.
"""

import sys
import os
from datetime import datetime, timezone


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.orm import VehicleSighting, Alert, Case, CaseEvidence, CaseTimelineEntry, AuditLog

DEMO_PLATE = "GJ01AB1234"


def reset_demo_data():
    print("=== [GIVIN DEMO RESET] Purging demonstration runtime state ===")
    db = SessionLocal()
    try:
        # 1. Purge demo cases and attached timeline/evidence
        demo_cases = db.query(Case).filter(Case.title.like(f"%{DEMO_PLATE}%")).all()
        c_count = len(demo_cases)
        for c in demo_cases:
            db.query(CaseTimelineEntry).filter(CaseTimelineEntry.case_id == c.id).delete()
            db.query(CaseEvidence).filter(CaseEvidence.case_id == c.id).delete()
            db.delete(c)
        db.commit()
        print(f"[+] Purged {c_count} demonstration cases.")

        # 2. Purge demo alerts and alert events
        alerts = db.query(Alert).filter(Alert.plate_text == DEMO_PLATE).all()
        a_count = len(alerts)
        for a in alerts:
            db.delete(a)
        db.commit()
        print(f"[+] Purged {a_count} demonstration alerts.")

        # 3. Purge demo sightings and any dependent alerts/evidence
        sighting_ids = [
            s.id for s in db.query(VehicleSighting.id).filter(
                (VehicleSighting.id.like("sight-%")) | 
                (VehicleSighting.processing_provenance == "MEASURED_DEMO_STREAM")
            ).all()
        ]
        s_count = len(sighting_ids)
        if sighting_ids:
            db.query(CaseEvidence).filter(CaseEvidence.sighting_id.in_(sighting_ids)).delete(synchronize_session=False)
            db.query(Alert).filter(Alert.sighting_id.in_(sighting_ids)).delete(synchronize_session=False)
            db.query(VehicleSighting).filter(VehicleSighting.id.in_(sighting_ids)).delete(synchronize_session=False)
            db.commit()
        print(f"[+] Purged {s_count} demonstration vehicle sightings and dependent records.")


        # 4. Record audit log
        import hashlib, json
        sig = hashlib.sha256(f"SYSTEM_DEMO_RESET:DEMO_PURGE_COMPLETED:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
        audit = AuditLog(
            user_id="SYSTEM_DEMO_RESET",
            action="DEMO_PURGE_COMPLETED",
            resource="STATEWIDE_DEMO_RECORDS",
            details_json=json.dumps({"message": f"Demo state for vehicle {DEMO_PLATE} cleaned successfully."}),
            signature_hash=sig
        )
        db.add(audit)
        db.commit()


        print("=== [GIVIN DEMO RESET] Reset complete. System returned to pristine state. ===")
    finally:
        db.close()


if __name__ == "__main__":
    reset_demo_data()
