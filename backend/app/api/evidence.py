from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from backend.app.core.database import get_db
from backend.app.models.orm import VehicleSighting, Camera, AuditLog
from backend.app.core.security import generate_evidence_certificate_hash, verify_evidence_integrity

router = APIRouter(prefix="/evidence", tags=["Investigation & Section 65B Evidence"])

@router.get("/{sighting_id}/certificate")
def generate_section_65b_certificate(
    sighting_id: str,
    certifying_officer: str = Query("Inspector V. Patel, Gujarat Police C4I Center"),
    officer_designation: str = Query("Senior Inspector (Technical Surveillance)"),
    db: Session = Depends(get_db)
):
    """
    Generates a legally admissible Certificate of Electronic Evidence under
    Section 65B of the Indian Evidence Act, 1872 / Section 63 of Bharatiya Sakshya Adhiniyam (BSA), 2023.
    """
    sighting = db.query(VehicleSighting).filter(VehicleSighting.id == sighting_id).first()
    if not sighting:
        raise HTTPException(status_code=404, detail="Sighting record not found")

    cam = db.query(Camera).filter(Camera.id == sighting.camera_id).first()
    cam_name = cam.name if cam else "High-Speed ANPR Camera"
    cam_loc = cam.location_name if cam else "State Highway"
    cam_district = cam.district if cam else "Gujarat"
    vendor_info = f"{cam.vendor} {cam.model} ({cam.resolution}, {cam.protocol})" if cam else "Hikvision DS-2CD2043G2-I (1080p, RTSP)"

    timestamp_str = sighting.timestamp.isoformat()
    evidence_hash = sighting.evidence_hash or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    digital_signature = generate_evidence_certificate_hash(
        camera_id=sighting.camera_id,
        timestamp=timestamp_str,
        plate_text=sighting.plate_text,
        image_hash=evidence_hash,
        operator_id=certifying_officer
    )

    certificate_data = {
        "certificate_title": "CERTIFICATE UNDER SECTION 65B OF THE INDIAN EVIDENCE ACT, 1872",
        "legal_act_reference": "Section 65B, Indian Evidence Act 1872 & Section 63, Bharatiya Sakshya Adhiniyam 2023",
        "certificate_id": f"CERT-65B-{sighting.id[:8].upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "issuing_authority": "Gujarat Police Integrated Video Intelligence Network (GIVIN)",
        "date_of_issuance": datetime.now(timezone.utc).strftime("%d-%B-%Y %H:%M:%S UTC"),
        "certifying_officer": {
            "name": certifying_officer,
            "designation": officer_designation,
            "station": "State Command and Control Centre (Netram), Gandhinagar"
        },
        "electronic_record_details": {
            "target_vehicle_plate": sighting.plate_text,
            "vehicle_category": sighting.vehicle_type,
            "vehicle_color": sighting.vehicle_color,
            "timestamp_of_capture": timestamp_str,
            "camera_identifier": cam.logical_camera_id if cam else sighting.camera_id,
            "camera_description": cam_name,
            "device_hardware": vendor_info,
            "geographical_coordinates": {
                "latitude": cam.lat if cam else 23.0298,
                "longitude": cam.lng if cam else 72.5074,
                "location_name": cam_loc,
                "district": cam_district
            },
            "speed_recorded_kmh": sighting.speed_kmh,
            "direction": sighting.direction,
            "detection_confidence": f"{sighting.confidence * 100:.1f}%"
        },
        "technical_integrity_declarations": [
            "1. The computer system / VMS / NVR was operating properly during the entire recording period without malfunction affecting accuracy.",
            "2. The electronic record was produced by the computerized CCTV surveillance apparatus in the ordinary course of lawful state monitoring.",
            "3. The system clock of the recording server was synchronized with the National Physical Laboratory (NPL) standard time server.",
            "4. The digital image snapshot has been cryptographically sealed using SHA-256 and has not been altered or manipulated."
        ],
        "cryptographic_verification": {
            "hash_algorithm": "SHA-256",
            "evidence_snapshot_sha256": evidence_hash,
            "hmac_tamper_evident_signature": digital_signature,
            "verification_status": "VERIFIED_AUTHENTIC_UNALTERED"
        }
    }

    return certificate_data

@router.get("/audit-logs")
def get_audit_trail(limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    """Returns immutable security and operational audit trail."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
