"""
Sentinel Camera Catalogue Ingestion Contract API.
Contract Endpoint: GET /api/ingest
Provides dynamic camera discovery for the Sentinel Camera Grid.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.sentinel_catalogue import sentinel_catalogue

router = APIRouter(tags=["Sentinel Ingestion"])

@router.get("/ingest")
def get_camera_ingest_catalogue(
    district: Optional[str] = Query(None, description="Optional district filter (e.g. Ahmedabad, Surat)"),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Section 39.1: Authoritative Sentinel Camera Catalogue Contract.
    Discovers all available live cameras with their stream endpoints (RTSP TCP, WebRTC, HLS),
    codecs, resolutions, declared FPS, and stream capabilities.
    """
    catalogue = sentinel_catalogue.get_catalogue(db, district=district)
    if catalogue.get("status") == "CATALOGUE_UNAVAILABLE":
        if response:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return catalogue
