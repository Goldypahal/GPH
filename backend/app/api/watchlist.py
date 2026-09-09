from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.orm import Watchlist, AuditLog
from backend.app.models.schema import WatchlistOut, WatchlistCreate
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.security import generate_sha256_hash

router = APIRouter(prefix="/watchlist", tags=["Watchlist Management"])

@router.get("", response_model=List[WatchlistOut])
def list_watchlist(
    status: Optional[str] = "ACTIVE",
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lists hotlisted suspect vehicles registered in eGujCop / VAHAN databases."""
    query = db.query(Watchlist)
    if status:
        query = query.filter(Watchlist.status == status)
    if risk_level:
        query = query.filter(Watchlist.risk_level == risk_level)
    if search:
        query = query.filter(
            (Watchlist.vehicle_number.ilike(f"%{search}%")) |
            (Watchlist.reason.ilike(f"%{search}%")) |
            (Watchlist.case_fir_number.ilike(f"%{search}%"))
        )

    return query.order_by(Watchlist.created_at.desc()).all()

@router.post("", response_model=WatchlistOut)
def add_to_watchlist(item: WatchlistCreate, db: Session = Depends(get_db)):
    """Adds a new suspect vehicle to the statewide hotlist."""
    norm_plate = ANPREngine.normalize_plate(item.vehicle_number)
    
    new_entry = Watchlist(
        list_name=item.list_name,
        entity_type=item.entity_type,
        vehicle_number=norm_plate,
        owner_name=item.owner_name,
        vehicle_make_model=item.vehicle_make_model,
        vehicle_color=item.vehicle_color,
        risk_level=item.risk_level,
        reason=item.reason,
        case_fir_number=item.case_fir_number,
        registered_authority=item.registered_authority,
        status="ACTIVE"
    )
    db.add(new_entry)
    db.flush()

    audit = AuditLog(
        user_id="OFFICER_CONTROL_ROOM",
        action="WATCHLIST_ADD",
        resource=f"VEHICLE:{norm_plate}",
        details_json=f"Added to watchlist. Reason: {item.reason} [FIR: {item.case_fir_number}]",
        signature_hash=generate_sha256_hash(norm_plate.encode())
    )
    db.add(audit)
    db.commit()
    db.refresh(new_entry)

    return new_entry

@router.delete("/{watchlist_id}")
def delete_from_watchlist(watchlist_id: str, db: Session = Depends(get_db)):
    """Deactivates a watchlist entry."""
    entry = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    
    entry.status = "INACTIVE"
    db.commit()
    return {"message": "Watchlist entry deactivated successfully", "id": watchlist_id}
