from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.orm import Camera, Department, CameraHealth
from backend.app.models.schema import CameraOut, CameraBase
from backend.app.services.feed_connector import FeedConnector

router = APIRouter(prefix="/cameras", tags=["Camera Registry & GIS"])

@router.get("", response_model=List[CameraOut])
def list_cameras(
    district: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    vendor: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns all registered CCTV cameras across Gujarat with GIS coordinates,
    hardware vendor, protocol, and real-time operational health.
    """
    query = db.query(Camera)
    if district:
        query = query.filter(Camera.district.ilike(f"%{district}%"))
    if department_id:
        query = query.filter(Camera.department_id == department_id)
    if status:
        query = query.filter(Camera.status == status)
    if vendor:
        query = query.filter(Camera.vendor == vendor)

    cameras = query.all()
    results = []
    for c in cameras:
        dept_name = c.department.name if c.department else "Unknown Department"
        health_stat = c.health.status if c.health else "ONLINE"
        lat_ms = c.health.latency_ms if c.health else 40
        c_dict = CameraOut.from_orm(c)
        c_dict.department_name = dept_name
        c_dict.health_status = health_stat
        c_dict.latency_ms = lat_ms
        results.append(c_dict)

    return results

@router.get("/stats/summary")
def get_cameras_summary(db: Session = Depends(get_db)):
    """Summary counts for C4I executive dashboard overview."""
    total = db.query(Camera).count()
    online = db.query(Camera).filter(Camera.status == "ACTIVE").count()
    degraded = db.query(Camera).filter(Camera.status == "DEGRADED").count()
    offline = total - (online + degraded)
    
    # District distribution
    districts = {}
    for c in db.query(Camera).all():
        districts[c.district] = districts.get(c.district, 0) + 1
        
    # Vendor distribution
    vendors = {}
    for c in db.query(Camera).all():
        vendors[c.vendor] = vendors.get(c.vendor, 0) + 1

    return {
        "total_onboarded": total,
        "online_count": online,
        "degraded_count": degraded,
        "offline_count": offline,
        "districts_covered": len(districts),
        "district_breakdown": districts,
        "vendor_breakdown": vendors,
        "system_health_pct": round((online / max(1, total)) * 100, 1)
    }

@router.get("/{camera_id}", response_model=CameraOut)
def get_camera_detail(camera_id: str, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter((Camera.id == camera_id) | (Camera.logical_camera_id == camera_id)).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    res = CameraOut.from_orm(cam)
    res.department_name = cam.department.name if cam.department else ""
    res.health_status = cam.health.status if cam.health else "ONLINE"
    res.latency_ms = cam.health.latency_ms if cam.health else 45
    return res

@router.post("", response_model=CameraOut)
def onboard_camera(cam_in: CameraBase, db: Session = Depends(get_db)):
    """Onboards a new heterogeneous camera into the GIVIN Model 1 Asset Registry."""
    new_cam = Camera(
        name=cam_in.name,
        logical_camera_id=cam_in.logical_camera_id,
        department_id=cam_in.department_id,
        district=cam_in.district,
        location_name=cam_in.location_name,
        lat=cam_in.lat,
        lng=cam_in.lng,
        altitude=cam_in.altitude,
        fov_angle=cam_in.fov_angle,
        fov_range_m=cam_in.fov_range_m,
        vendor=cam_in.vendor,
        model=cam_in.model,
        camera_type=cam_in.camera_type,
        resolution=cam_in.resolution,
        fps=cam_in.fps,
        protocol=cam_in.protocol,
        stream_url=f"/api/cameras/stream/{cam_in.logical_camera_id}",
        vms_type=cam_in.vms_type,
        storage_type=cam_in.storage_type,
        retention_days=cam_in.retention_days,
        status="ACTIVE"
    )
    db.add(new_cam)
    db.flush()

    health = CameraHealth(
        camera_id=new_cam.id,
        latency_ms=42,
        packet_loss=0.1,
        cpu_usage=25.0,
        memory_usage=40.0,
        status="ONLINE"
    )
    db.add(health)
    db.commit()
    db.refresh(new_cam)

    res = CameraOut.from_orm(new_cam)
    res.health_status = "ONLINE"
    return res

@router.get("/stream/{logical_id}")
def stream_camera_feed(logical_id: str, db: Session = Depends(get_db)):
    """
    Simulated low-latency MJPEG stream with real-time AI bounding boxes
    and ANPR detection overlays for video wall viewing.
    """
    cam = db.query(Camera).filter(Camera.logical_camera_id == logical_id).first()
    cam_name = cam.name if cam else logical_id
    district = cam.district if cam else "Gujarat"

    return StreamingResponse(
        FeedConnector.get_stream_generator(logical_id, cam_name, district),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
