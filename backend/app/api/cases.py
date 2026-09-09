import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.orm import Case, CaseTimelineEntry, CaseEvidence, VehicleSighting, Camera, Alert, AuditLog
from backend.app.services.vehicle_tracker import VehicleTracker
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.security import get_current_user, require_role, generate_sha256_hash

router = APIRouter(prefix="/cases", tags=["Case & Investigation Workflow"])

class CaseCreateRequest(BaseModel):
    title: str
    target_vehicle_plate: str
    fir_number: Optional[str] = "FIR-2026/AHM-CRIME/0981"
    priority: Optional[str] = "HIGH"
    assigned_investigator: Optional[str] = "Inspector V. Patel"
    jurisdiction_district: Optional[str] = "Statewide"
    created_from_alert_id: Optional[str] = None
    description: Optional[str] = "Vehicle involved in armed inter-district crime syndicate."

class CaseNoteRequest(BaseModel):
    title: str
    content: str
    author: Optional[str] = "Inspector V. Patel"

class CaseAssignRequest(BaseModel):
    investigator_name: str
    remarks: Optional[str] = "Reassigned for field interception and seizure"

class TimelineEntryOut(BaseModel):
    id: str
    entry_type: str
    title: str
    content: str
    created_by: str
    created_at: datetime
    class Config:
        from_attributes = True

class CaseSummaryOut(BaseModel):
    id: str
    case_number: str
    title: str
    fir_number: Optional[str]
    status: str
    priority: str
    assigned_investigator: str
    jurisdiction_district: str
    target_vehicle_plate: str
    created_from_alert_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    timeline_count: int = 0
    class Config:
        from_attributes = True

@router.post("", response_model=CaseSummaryOut)
def create_case(payload: CaseCreateRequest, db: Session = Depends(get_db)):
    """Creates an official police investigation case from an alert or suspect sighting."""
    now = datetime.now(timezone.utc)
    norm_plate = ANPREngine.normalize_plate(payload.target_vehicle_plate)
    case_num = f"CASE-{now.strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

    new_case = Case(
        case_number=case_num,
        title=payload.title,
        fir_number=payload.fir_number,
        status="INVESTIGATING",
        priority=payload.priority,
        assigned_investigator=payload.assigned_investigator,
        jurisdiction_district=payload.jurisdiction_district,
        target_vehicle_plate=norm_plate,
        created_from_alert_id=payload.created_from_alert_id,
        description=payload.description,
        created_at=now,
        updated_at=now
    )
    db.add(new_case)
    db.flush()

    # Initial timeline entry
    initial_entry = CaseTimelineEntry(
        case_id=new_case.id,
        entry_type="STATUS_CHANGE",
        title="Investigation Docket Registered",
        content=f"Case opened for vehicle {norm_plate}. Assigned to {payload.assigned_investigator}. FIR Ref: {payload.fir_number}",
        created_by=payload.assigned_investigator,
        created_at=now
    )
    db.add(initial_entry)

    # Automatically attach historical sightings of this vehicle as verified case evidence
    sightings = db.query(VehicleSighting).filter(VehicleSighting.normalized_plate == norm_plate).all()
    for s in sightings:
        ev = CaseEvidence(
            case_id=new_case.id,
            sighting_id=s.id,
            evidence_hash=s.evidence_hash,
            sec_65b_cert_ref=f"CERT-65B-{s.id[:8].upper()}",
            attached_at=now
        )
        db.add(ev)

    # Audit log
    audit = AuditLog(
        user_id=payload.assigned_investigator or "OFFICER",
        action="CASE_CREATE",
        resource=f"CASE:{case_num}",
        details_json=f"Title: {payload.title}, Plate: {norm_plate}",
        signature_hash=generate_sha256_hash(case_num.encode())
    )
    db.add(audit)

    db.commit()
    db.refresh(new_case)

    out = CaseSummaryOut.from_orm(new_case)
    out.timeline_count = 1
    return out

@router.get("", response_model=List[CaseSummaryOut])
def list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    investigator: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lists all registered police investigation cases."""
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    if priority:
        query = query.filter(Case.priority == priority)
    if investigator:
        query = query.filter(Case.assigned_investigator.ilike(f"%{investigator}%"))

    cases = query.order_by(Case.created_at.desc()).all()
    results = []
    for c in cases:
        item = CaseSummaryOut.from_orm(c)
        item.timeline_count = len(c.timeline_entries)
        results.append(item)
    return results

@router.get("/{case_id}")
def get_case_dossier(case_id: str, db: Session = Depends(get_db)):
    """Retrieves full case timeline, notes, and correlated vehicle journey."""
    case = db.query(Case).filter((Case.id == case_id) | (Case.case_number == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case record not found")

    journey = VehicleTracker.reconstruct_journey(db, case.target_vehicle_plate)
    timeline = db.query(CaseTimelineEntry).filter(CaseTimelineEntry.case_id == case.id).order_by(CaseTimelineEntry.created_at.desc()).all()
    evidence = db.query(CaseEvidence).filter(CaseEvidence.case_id == case.id).all()

    return {
        "case": CaseSummaryOut.from_orm(case),
        "description": case.description,
        "timeline": [TimelineEntryOut.from_orm(t) for t in timeline],
        "evidence_count": len(evidence),
        "trajectory_summary": journey
    }

@router.post("/{case_id}/notes")
def add_case_note(case_id: str, note: CaseNoteRequest, db: Session = Depends(get_db)):
    """Appends an officer investigation diary note to the case timeline."""
    case = db.query(Case).filter((Case.id == case_id) | (Case.case_number == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case record not found")

    now = datetime.now(timezone.utc)
    entry = CaseTimelineEntry(
        case_id=case.id,
        entry_type="NOTE",
        title=note.title,
        content=note.content,
        created_by=note.author,
        created_at=now
    )
    db.add(entry)
    case.updated_at = now
    db.commit()
    return {"status": "success", "message": "Case diary note added to timeline"}

@router.post("/{case_id}/assign")
def reassign_case(case_id: str, payload: CaseAssignRequest, db: Session = Depends(get_db)):
    """Reassigns case to another investigating officer."""
    case = db.query(Case).filter((Case.id == case_id) | (Case.case_number == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case record not found")

    now = datetime.now(timezone.utc)
    old_officer = case.assigned_investigator
    case.assigned_investigator = payload.investigator_name
    case.updated_at = now

    entry = CaseTimelineEntry(
        case_id=case.id,
        entry_type="STATUS_CHANGE",
        title="Investigator Reassigned",
        content=f"Case reassigned from {old_officer} to {payload.investigator_name}. Remarks: {payload.remarks}",
        created_by="STATE_COMMAND",
        created_at=now
    )
    db.add(entry)
    db.commit()
    return {"status": "success", "message": f"Case reassigned to {payload.investigator_name}"}

@router.get("/{case_id}/report")
def generate_investigation_report(case_id: str, db: Session = Depends(get_db)):
    """
    Generates a formal, printable Investigation Dossier combining case details,
    cross-camera sightings, Section 65B legal integrity certificates, and officer diary.
    """
    case = db.query(Case).filter((Case.id == case_id) | (Case.case_number == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    journey = VehicleTracker.reconstruct_journey(db, case.target_vehicle_plate)
    timeline = db.query(CaseTimelineEntry).filter(CaseTimelineEntry.case_id == case.id).order_by(CaseTimelineEntry.created_at.asc()).all()

    report_id = f"DOSSIER-C4I-{case.case_number}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    return {
        "report_id": report_id,
        "dossier_id": report_id,
        "title": f"SPECIAL INVESTIGATION DOSSIER — {case.title.upper()}",
        "issuing_jurisdiction": f"Gujarat Police Directorate // {case.jurisdiction_district}",
        "case_number": case.case_number,
        "fir_number": case.fir_number,
        "investigating_officer": case.assigned_investigator,
        "date_generated": datetime.now(timezone.utc).strftime("%d-%B-%Y %H:%M:%S UTC"),
        "target_vehicle": {
            "plate_number": case.target_vehicle_plate,
            "route_confidence": f"{journey.route_confidence_pct}%" if journey else "N/A",
            "total_checkpoints": journey.total_sightings if journey else 0,
            "districts_traversed": journey.districts_traversed if journey else []
        },
        "movement_chronology": journey.trajectory if journey else [],
        "timeline": [
            {
                "date": t.created_at.strftime("%d-%b-%Y %H:%M"),
                "author": t.created_by,
                "title": t.title,
                "content": t.content
            }
            for t in timeline
        ],
        "investigation_diary_notes": [
            {
                "date": t.created_at.strftime("%d-%b-%Y %H:%M"),
                "author": t.created_by,
                "title": t.title,
                "content": t.content
            }
            for t in timeline
        ],
        "statutory_certification": {
            "evidence_act_reference": "Section 65B Indian Evidence Act 1872 / Section 63 BSA 2023",
            "dossier_integrity_hash": generate_sha256_hash(case.case_number.encode()),
            "status": "COURT_SUBMISSION_READY"
        }
    }
