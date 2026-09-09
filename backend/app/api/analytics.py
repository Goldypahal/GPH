import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.core.database import get_db
from backend.app.models.orm import VehicleSighting, Camera
from backend.app.services.anpr_engine import ANPREngine
from backend.app.services.watchlist_matcher import WatchlistMatcher
from backend.app.services.vision_pipeline import vision_pipeline, VisionPipelineError
from backend.app.core.realtime import alert_broadcaster
from backend.app.core.security import generate_sha256_hash

router = APIRouter(prefix="/analytics", tags=["AI Video Analytics & Ingestion"])
EVIDENCE_DIR = Path(os.getenv("GIVIN_EVIDENCE_DIR", "data/evidence"))
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/process-frame")
async def process_video_frame(
    file: UploadFile = File(...),
    camera_id: Optional[str] = Form(None),
    plate_override: Optional[str] = Form(None),
    vehicle_type: Optional[str] = Form("Unknown"),
    vehicle_color: Optional[str] = Form("Unknown"),
    speed_kmh: Optional[float] = Form(0.0),
    db: Session = Depends(get_db)
):
    """Process one real camera frame through detection + OCR + watchlist.

    plate_override is retained only as an explicit test/demo hook. Normal
    operation performs YOLO vehicle detection and PaddleOCR through the vision
    pipeline and never fabricates a plate when real mode is unavailable.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty frame")
    img_hash = generate_sha256_hash(contents)

    detections = []
    if plate_override:
        corrected, confidence, valid = ANPREngine.validate_and_correct(plate_override)
        detections = [{
            "plate_text": corrected, "ocr_confidence": confidence,
            "bbox": None, "detector_confidence": 1.0,
            "vehicle_type": vehicle_type or "Unknown",
            "vehicle_color": vehicle_color or "Unknown", "source": "explicit-test-override"
        }]
        is_valid = valid
    else:
        try:
            detections = [d.to_dict() for d in vision_pipeline.detect(contents)]
        except VisionPipelineError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if not detections:
            raise HTTPException(status_code=422, detail="No vehicle/plate detection in frame")
        is_valid = True

    cam = None
    if camera_id:
        cam = db.query(Camera).filter((Camera.id == camera_id) | (Camera.logical_camera_id == camera_id)).first()
    if not cam:
        cam = db.query(Camera).first()
    if not cam:
        raise HTTPException(status_code=404, detail="No camera is registered")

    # Persist the original frame, never a generated evidence placeholder.
    suffix = Path(file.filename or "frame.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    evidence_path = EVIDENCE_DIR / f"{img_hash}{suffix}"
    evidence_path.write_bytes(contents)

    results = []
    for detection in detections:
        plate = detection["plate_text"]
        normalized = ANPREngine.normalize_plate(plate)
        confidence = float(detection.get("ocr_confidence", 0.0))
        sighting = VehicleSighting(
            plate_text=plate,
            normalized_plate=normalized,
            camera_id=cam.id,
            timestamp=datetime.now(timezone.utc),
            confidence=confidence,
            vehicle_type=detection.get("vehicle_type") or vehicle_type or "Unknown",
            vehicle_color=detection.get("vehicle_color") or vehicle_color or "Unknown",
            speed_kmh=speed_kmh or 0.0,
            direction="Forward",
            bbox_json=str(detection.get("bbox")) if detection.get("bbox") else None,
            evidence_uri=f"/api/analytics/evidence/{evidence_path.name}",
            evidence_hash=img_hash,
        )
        db.add(sighting)
        db.flush()
        alert = WatchlistMatcher.trigger_alert_if_matched(db, sighting)
        if alert:
            await alert_broadcaster.broadcast({
                "event": "WATCHLIST_ALERT",
                "alert_uid": alert.alert_uid,
                "risk_level": alert.risk_level,
                "plate_text": alert.plate_text,
                "camera_id": cam.logical_camera_id,
                "district": cam.district,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        results.append({
            "detected_plate": plate,
            "is_valid_format": is_valid,
            "ocr_confidence": confidence,
            "watchlist_match": bool(alert),
            "alert_uid": alert.alert_uid if alert else None,
            "risk_level": alert.risk_level if alert else "NORMAL",
            "bbox": detection.get("bbox"),
            "detector_confidence": detection.get("detector_confidence"),
            "source": detection.get("source"),
        })

    return {
        "status": "success",
        "camera_id": cam.logical_camera_id,
        "camera_name": cam.name,
        "district": cam.district,
        "detections": results,
        "evidence_hash": img_hash,
        "evidence_uri": f"/api/analytics/evidence/{evidence_path.name}",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/evidence/{filename}")
def get_evidence_image(filename: str):
    """Serve the exact captured evidence frame after hash-addressed storage."""
    safe_name = Path(filename).name
    path = EVIDENCE_DIR / safe_name
    if not path.is_file() or not all(c in "0123456789abcdef" for c in path.stem.lower()):
        raise HTTPException(status_code=404, detail="Evidence not found")
    if len(path.stem) != 64:
        raise HTTPException(status_code=400, detail="Invalid evidence identifier")
    # Verify the object has not changed since ingestion.
    if hashlib.sha256(path.read_bytes()).hexdigest() != path.stem:
        raise HTTPException(status_code=409, detail="Evidence integrity check failed")
    return FileResponse(path)
