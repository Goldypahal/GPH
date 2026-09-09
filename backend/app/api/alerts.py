import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.orm import Alert, VehicleSighting, Camera, Watchlist, AuditLog
from backend.app.models.schema import AlertOut, AlertAction
from backend.app.core.security import generate_sha256_hash

router = APIRouter(prefix="/alerts", tags=["Watchlist & Real-Time Alerting"])

@router.get("", response_model=List[AlertOut])
def get_alerts(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Returns real-time police alerts with camera metadata and risk priority."""
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if risk_level:
        query = query.filter(Alert.risk_level == risk_level)

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    results = []
    for a in alerts:
        cam = db.query(Camera).filter(Camera.id == a.camera_id).first()
        item = AlertOut.from_orm(a)
        if cam:
            item.camera_name = cam.name
            item.district = cam.district
            item.location_name = cam.location_name
            item.lat = cam.lat
            item.lng = cam.lng
        if a.sighting:
            item.vehicle_type = a.sighting.vehicle_type
            item.vehicle_color = a.sighting.vehicle_color
            item.evidence_uri = a.sighting.evidence_uri
        results.append(item)

    return results

@router.post("/{alert_id}/action", response_model=AlertOut)
def take_alert_action(
    alert_id: str,
    action: AlertAction,
    db: Session = Depends(get_db)
):
    """
    Updates alert lifecycle status: ACKNOWLEDGED, INVESTIGATING, RESOLVED, FALSE_POSITIVE.
    Dispatches police patrol units (e.g. PCR Vans, Highway Interceptors).
    """
    alert = db.query(Alert).filter((Alert.id == alert_id) | (Alert.alert_uid == alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = action.status
    if action.remarks:
        alert.remarks = f"{alert.remarks or ''} | {action.remarks}"
    if action.dispatched_unit:
        alert.dispatched_unit = action.dispatched_unit
    
    alert.acknowledged_by = action.operator_name
    alert.acknowledged_at = datetime.now(timezone.utc)
    
    # Audit trail
    audit = AuditLog(
        user_id=action.operator_name or "OPERATOR",
        action=f"ALERT_{action.status}",
        resource=f"ALERT:{alert.alert_uid}",
        details_json=f"Status changed to {action.status}. Unit: {action.dispatched_unit}. Remarks: {action.remarks}",
        signature_hash=generate_sha256_hash(f"{alert.alert_uid}:{action.status}".encode())
    )
    db.add(audit)
    db.commit()
    db.refresh(alert)

    cam = db.query(Camera).filter(Camera.id == alert.camera_id).first()
    res = AlertOut.from_orm(alert)
    if cam:
        res.camera_name = cam.name
        res.district = cam.district
        res.location_name = cam.location_name
        res.lat = cam.lat
        res.lng = cam.lng
    return res

@router.post("/simulate")
def simulate_live_detection_alert(
    plate: str = Query("GJ01AB1234", description="Vehicle plate to simulate detection"),
    camera_code: Optional[str] = Query(None, description="Camera logical code"),
    db: Session = Depends(get_db)
):
    """
    Simulates a live high-priority detection event on a camera feed, triggering
    instant ANPR OCR, watchlist matching, and WebSocket / audio alarm dispatch.
    """
    cam = None
    if camera_code:
        cam = db.query(Camera).filter(Camera.logical_camera_id == camera_code).first()
    if not cam:
        cam = db.query(Camera).first()

    now = datetime.now(timezone.utc)
    raw_crop = f"SIMULATED:{plate}:{cam.logical_camera_id}:{now.isoformat()}".encode()
    img_hash = generate_sha256_hash(raw_crop)

    sighting = VehicleSighting(
        plate_text=plate,
        normalized_plate=plate.replace("-", "").upper(),
        camera_id=cam.id,
        timestamp=now,
        confidence=0.98,
        vehicle_type="Car",
        vehicle_color="Red",
        speed_kmh=64.0,
        direction="Westbound",
        evidence_uri=f"/api/analytics/evidence/{img_hash[:16]}.jpg",
        evidence_hash=img_hash
    )
    db.add(sighting)
    db.flush()

    # Match watchlist
    wl = db.query(Watchlist).filter(Watchlist.vehicle_number == sighting.normalized_plate).first()
    risk = wl.risk_level if wl else "MEDIUM"
    reason = wl.reason if wl else "Automated Real-Time Surveillance Detection"

    alert_uid = f"ALT-{now.strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
    new_alert = Alert(
        alert_uid=alert_uid,
        watchlist_id=wl.id if wl else None,
        sighting_id=sighting.id,
        camera_id=cam.id,
        plate_text=plate,
        risk_level=risk,
        status="NEW",
        remarks=f"HOTLIST HIT! Detected at {cam.name} ({cam.district}). Reason: {reason}",
        dispatched_unit="Highway Patrol Team 04 - Intercept Alert Dispatched"
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    return {
        "status": "success",
        "message": f"Real-time alert triggered for plate {plate}",
        "alert_uid": new_alert.alert_uid,
        "camera": cam.name,
        "district": cam.district,
        "risk_level": risk,
        "timestamp": now.isoformat()
    }
