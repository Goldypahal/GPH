from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.orm import VehicleSighting, Camera, AuditLog
from backend.app.models.schema import VehicleJourneySummary, VehicleSightingOut, LivePursuitPosition
from backend.app.services.vehicle_tracker import VehicleTracker
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.security import generate_sha256_hash

router = APIRouter(prefix="/tracking", tags=["Vehicle Tracking & Route Reconstruction"])

@router.get("/search", response_model=VehicleJourneySummary)
def search_and_reconstruct_vehicle_route(
    plate: str = Query(..., description="Target vehicle registration number (e.g. GJ01AB1234)"),
    db: Session = Depends(get_db)
):
    """
    Core Hackathon Evaluation Test Scenario:
    Accepts a designated vehicle registration number, searches the integrated CCTV network,
    identifies sightings across geographically dispersed cameras, and computes the
    complete timestamped, location-wise movement history with GIS trajectory coordinates.
    """
    journey = VehicleTracker.reconstruct_journey(db, plate)
    if not journey:
        raise HTTPException(
            status_code=404,
            detail=f"No sightings found for vehicle '{plate}' across the integrated CCTV network."
        )

    # Log search in audit trail for compliance
    audit = AuditLog(
        user_id="OFFICER_INVESTIGATION",
        action="VEHICLE_SEARCH",
        resource=f"PLATE:{plate.upper()}",
        details_json=f"Reconstructed route with {journey.total_sightings} sightings across districts: {', '.join(journey.districts_traversed)}",
        signature_hash=generate_sha256_hash(f"{plate}:{journey.total_sightings}".encode())
    )
    db.add(audit)
    db.commit()

    return journey


@router.get("/route/{plate}", response_model=VehicleJourneySummary)
def get_vehicle_route_by_plate(plate: str, db: Session = Depends(get_db)):
    """Convenience alias for route reconstruction by plate."""
    return search_and_reconstruct_vehicle_route(plate=plate, db=db)

@router.get("/live/{plate}", response_model=LivePursuitPosition)
def get_live_pursuit_position(
    plate: str,
    db: Session = Depends(get_db)
):
    """
    Live Pursuit Mode (GTA-style live map).

    GIVIN is a CCTV/ANPR network, not an in-vehicle GPS tracker, so a stolen
    vehicle's "live" position is a dead-reckoned projection: it takes the
    vehicle's last two confirmed camera sightings, derives heading + speed,
    and extrapolates a moving marker forward from the most recent confirmed
    checkpoint. It also nominates the nearest CCTV camera ahead on that
    heading so a controller knows which feed will most likely reconfirm it.
    Poll this endpoint every 1-3 seconds from the map to animate the blip;
    the position resets to a fresh dead-reckoning baseline every time a new
    ANPR sighting is recorded.
    """
    live_position = VehicleTracker.predict_live_position(db, plate)
    if not live_position:
        raise HTTPException(
            status_code=404,
            detail=f"No sightings found for vehicle '{plate}' — cannot start live pursuit."
        )

    # Note: intentionally not audit-logged per call (this is polled every
    # 1-3s by the live map); the initiating /tracking/search call already
    # records the investigation in the audit trail.
    return live_position

@router.get("/recent", response_model=List[VehicleSightingOut])
def get_recent_sightings(
    limit: int = Query(20, le=100),
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns the latest ANPR vehicle sightings across all active cameras."""
    query = db.query(VehicleSighting).join(Camera)
    if district:
        query = query.filter(Camera.district.ilike(f"%{district}%"))

    sightings = query.order_by(VehicleSighting.timestamp.desc()).limit(limit).all()
    results = []
    for s in sightings:
        item = VehicleSightingOut.from_orm(s)
        if s.camera:
            item.camera_name = s.camera.name
            item.district = s.camera.district
            item.location_name = s.camera.location_name
            item.lat = s.camera.lat
            item.lng = s.camera.lng
        results.append(item)

    return results

# =====================================================================
# PHASE C: CROSS-CAMERA INTELLIGENCE ENDPOINTS
# =====================================================================

from backend.app.models.schema import (
    ContainmentPerimeterOut, TravelAnomalyOut, ClonedPlateAlertOut, CameraGraphOut
)
from backend.app.services.containment import containment_service
from backend.app.services.anomaly_engine import travel_anomaly_engine
from backend.app.services.camera_graph import camera_network_graph

@router.get("/containment/{plate}", response_model=ContainmentPerimeterOut)
def get_pursuit_containment_perimeter(
    plate: str,
    db: Session = Depends(get_db)
):
    """
    Computes 5, 10, and 15-minute directional isochrone pursuit perimeters
    for target vehicle, enclosing surveillance cameras and recommending
    strategic chokepoints / toll plazas for tactical police interception.
    """
    containment = containment_service.compute_containment(db, plate)
    if not containment:
        raise HTTPException(
            status_code=404,
            detail=f"No active track or sightings found for vehicle '{plate}' — cannot compute containment."
        )
    return containment

@router.get("/anomalies/{plate}", response_model=List[TravelAnomalyOut])
def get_vehicle_travel_anomalies(
    plate: str,
    db: Session = Depends(get_db)
):
    """
    Detects spatial-temporal physics anomalies for the target registration:
    - Cloned Plates / Teleportation (simultaneous or impossible speed transit)
    - Excessive corridor point-to-point speeding (> 120 km/h)
    """
    anomalies = travel_anomaly_engine.evaluate_sightings_for_plate(db, plate, auto_raise_alert=True)
    return anomalies

@router.get("/cloned-plates", response_model=List[ClonedPlateAlertOut])
def get_statewide_cloned_plates(
    db: Session = Depends(get_db)
):
    """
    Returns statewide register of all detected cloned plate conflicts
    where the same license plate was sighted at distant cameras with
    impossible transit speed or dual simultaneous active sightings.
    """
    return travel_anomaly_engine.get_all_cloned_plate_conflicts(db)

@router.get("/camera-graph", response_model=CameraGraphOut)
def get_camera_network_graph(
    db: Session = Depends(get_db)
):
    """
    Returns the statewide camera spatial adjacency topology,
    corridor road links, and transition probabilities across Gujarat.
    """
    return camera_network_graph.get_topology_summary(db)

