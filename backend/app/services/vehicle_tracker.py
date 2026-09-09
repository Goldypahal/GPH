import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.orm import VehicleSighting, Camera, Watchlist
from backend.app.services.anpr_engine import ANPREngine
from backend.app.models.schema import VehicleJourneySummary, VehicleTrajectoryPoint, WatchlistOut

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0 # Earth's radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

class VehicleTracker:
    """
    Cross-Camera Temporal-Spatial Vehicle Trajectory and Route Reconstruction Engine.
    """

    @classmethod
    def reconstruct_journey(
        cls,
        db: Session,
        plate_number: str
    ) -> Optional[VehicleJourneySummary]:
        normalized_query = ANPREngine.normalize_plate(plate_number)
        if not normalized_query:
            return None

        # Fetch sightings matching plate chronologically
        sightings = (
            db.query(VehicleSighting)
            .filter(VehicleSighting.normalized_plate == normalized_query)
            .order_by(VehicleSighting.timestamp.asc())
            .all()
        )

        if not sightings:
            # Fallback: Check if partial or fuzzy match exists
            all_sightings = db.query(VehicleSighting).order_by(VehicleSighting.timestamp.asc()).all()
            sightings = [
                s for s in all_sightings
                if ANPREngine.calculate_levenshtein(s.normalized_plate, normalized_query) <= 1
            ]

        if not sightings:
            return None

        trajectory_points: List[VehicleTrajectoryPoint] = []
        total_distance = 0.0
        districts_seen = set()
        prev_lat = None
        prev_lng = None
        prev_time = None

        for idx, s in enumerate(sightings):
            cam = db.query(Camera).filter(Camera.id == s.camera_id).first()
            cam_name = cam.name if cam else f"Camera {s.camera_id[:6]}"
            district = cam.district if cam else "Gujarat"
            loc_name = cam.location_name if cam else "State Highway"
            lat = cam.lat if cam else 23.0225
            lng = cam.lng if cam else 72.5714
            districts_seen.add(district)

            delta_mins = None
            dist_km = None

            if prev_lat is not None and prev_lng is not None and prev_time is not None:
                dist_km = haversine_distance_km(prev_lat, prev_lng, lat, lng)
                total_distance += dist_km
                time_diff = (s.timestamp - prev_time).total_seconds() / 60.0
                delta_mins = round(time_diff, 1)

            trajectory_points.append(
                VehicleTrajectoryPoint(
                    sequence=idx + 1,
                    camera_id=s.camera_id,
                    camera_name=cam_name,
                    district=district,
                    location_name=loc_name,
                    lat=lat,
                    lng=lng,
                    timestamp=s.timestamp,
                    speed_kmh=s.speed_kmh,
                    confidence=s.confidence,
                    time_delta_mins=delta_mins,
                    distance_km=dist_km,
                    evidence_uri=s.evidence_uri
                )
            )

            prev_lat = lat
            prev_lng = lng
            prev_time = s.timestamp

        first_seen = sightings[0].timestamp
        last_seen = sightings[-1].timestamp
        avg_speed = round(sum(s.speed_kmh for s in sightings) / len(sightings), 1)

        # Check watchlist match
        watchlist_match = (
            db.query(Watchlist)
            .filter(Watchlist.vehicle_number.ilike(f"%{normalized_query}%"))
            .first()
        )
        watchlist_out = WatchlistOut.from_orm(watchlist_match) if watchlist_match else None

        return VehicleJourneySummary(
            plate_number=sightings[0].plate_text,
            total_sightings=len(sightings),
            first_seen=first_seen,
            last_seen=last_seen,
            districts_traversed=sorted(list(districts_seen)),
            total_estimated_distance_km=round(total_distance, 1),
            average_speed_kmh=avg_speed,
            trajectory=trajectory_points,
            matched_watchlist=watchlist_out
        )
