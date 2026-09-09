from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.orm import Camera, Department, CameraHealth
from backend.app.models.schema import CameraOut, CameraBase
from backend.app.services.feed_connector import FeedConnector

router = APIRouter(prefix="/cameras", tags=["Camera Registry & GIS"])

@router.get("", response_model=List[CameraOut])
def list_cameras(district: Optional[str] = None, department_id: Optional[str] = None, status: Optional[str] = None, vendor: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Camera)
    if district: query = query.filter(Camera.district.ilike(f"%{district}%"))
    if department_id: query = query.filter(Camera.department_id == department_id)
    if status: query = query.filter(Camera.status == status)
    if vendor: query = query.filter(Camera.vendor == vendor)
    results = []
    for c in query.all():
        out = CameraOut.from_orm(c)
        out.department_name = c.department.name if c.department else "Unknown Department"
        out.health_status = c.health.status if c.health else "ONLINE"
        out.latency_ms = c.health.latency_ms if c.health else 40
        results.append(out)
    return results

@router.get("/stats/summary")
def get_cameras_summary(db: Session = Depends(get_db)):
    cameras = db.query(Camera).all()
    total = len(cameras); online = sum(c.status == "ACTIVE" for c in cameras); degraded = sum(c.status == "DEGRADED" for c in cameras)
    districts = {}; vendors = {}
    for c in cameras:
        districts[c.district] = districts.get(c.district, 0) + 1
        vendors[c.vendor] = vendors.get(c.vendor, 0) + 1
    return {"total_onboarded": total, "online_count": online, "degraded_count": degraded, "offline_count": total-online-degraded, "districts_covered": len(districts), "district_breakdown": districts, "vendor_breakdown": vendors, "system_health_pct": round(online/max(1,total)*100,1)}

@router.get("/{camera_id}", response_model=CameraOut)
def get_camera_detail(camera_id: str, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter((Camera.id == camera_id) | (Camera.logical_camera_id == camera_id)).first()
    if not cam: raise HTTPException(status_code=404, detail="Camera not found")
    res = CameraOut.from_orm(cam); res.department_name = cam.department.name if cam.department else ""; res.health_status = cam.health.status if cam.health else "ONLINE"; res.latency_ms = cam.health.latency_ms if cam.health else 45
    return res

@router.post("", response_model=CameraOut)
def onboard_camera(cam_in: CameraBase, db: Session = Depends(get_db)):
    if db.query(Camera).filter(Camera.logical_camera_id == cam_in.logical_camera_id).first():
        raise HTTPException(status_code=409, detail="logical_camera_id already exists")
    cam_data = cam_in.model_dump()
    cam_data["status"] = cam_data.get("status") or "ACTIVE"
    new_cam = Camera(**cam_data)
    db.add(new_cam); db.flush()
    db.add(CameraHealth(camera_id=new_cam.id, latency_ms=42, packet_loss=0.1, cpu_usage=25.0, memory_usage=40.0, status="ONLINE"))
    db.commit(); db.refresh(new_cam)
    res = CameraOut.from_orm(new_cam); res.health_status = "ONLINE"; return res

from backend.app.core.security import get_current_user, require_permission
from backend.app.models.orm import User
from backend.app.models.schema import FederationRequestCreate, FederationRequestOut, FederationRequestAction
from backend.app.services.federation import federation_service
from backend.app.services.audit_service import audit_service

@router.get("/stream/{logical_id}")
def stream_camera_feed(
    logical_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cam = db.query(Camera).filter(Camera.logical_camera_id == logical_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Enforce multi-department federation policy
    allowed, reason = federation_service.can_user_access_camera(db, current_user, cam)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=reason
        )

    # Cryptographically audit camera feed observation
    audit_service.log_action(
        db=db,
        user_id=current_user.username if current_user else "ANONYMOUS",
        action="CAMERA_FEED_STREAM",
        resource=f"CAMERA:{cam.logical_camera_id}",
        details_json=f"Stream requested for {cam.name} ({cam.district})"
    )

    try:
        generator = FeedConnector.get_stream_generator(logical_id, cam.name, cam.district, cam.stream_url)
        return StreamingResponse(generator, media_type="multipart/x-mixed-replace; boundary=frame")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

# =====================================================================
# INTER-DEPARTMENTAL CAMERA FEDERATION ENDPOINTS
# =====================================================================

@router.post("/federation/request", response_model=FederationRequestOut)
def request_camera_federation(
    req_in: FederationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a formal request to access an un-federated camera feed belonging
    to another department, providing legal justification and FIR details.
    """
    try:
        req = federation_service.create_access_request(
            db=db,
            user=current_user,
            camera_id=req_in.camera_id,
            legal_justification=req_in.legal_justification,
            fir_number=req_in.fir_number,
            duration_hours=req_in.requested_duration_hours
        )
        return req
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/federation/requests", response_model=List[FederationRequestOut])
def list_federation_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists pending, approved, or historical camera federation requests."""
    return federation_service.list_requests(db, status=status)

@router.post("/federation/approve/{request_id}", response_model=FederationRequestOut)
def approve_federation_request(
    request_id: str,
    action: FederationRequestAction,
    db: Session = Depends(get_db),
    approver: User = Depends(require_permission("cameras:federation"))
):
    """
    Approves or rejects an inter-departmental feed sharing request.
    Requires 'cameras:federation' permission (Super Admin or DGP State Commissioner).
    """
    try:
        updated = federation_service.approve_access_request(
            db=db,
            request_id=request_id,
            approver_user=approver,
            status=action.status,
            duration_hours=action.approved_duration_hours,
            remarks=action.remarks
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

