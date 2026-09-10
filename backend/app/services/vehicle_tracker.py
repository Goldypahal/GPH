import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.orm import VehicleSighting, Camera, Watchlist
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.config import settings
from backend.app.models.schema import (
    VehicleJourneySummary, VehicleTrajectoryPoint, WatchlistOut, LivePursuitPosition
)

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

def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0=N, 90=E, 180=S, 270=W) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360

def destination_point(lat: float, lon: float, bearing: float, distance_km: float) -> tuple:
    """Projects a new lat/lng given a start point, bearing (deg) and distance (km)."""
    R = 6371.0
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)
    theta = math.radians(bearing)
    delta = distance_km / R

    phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2)
    )
    return round(math.degrees(phi2), 6), round(math.degrees(lambda2), 6)

def _as_utc(dt: datetime) -> datetime:
    """Normalizes a possibly-naive datetime (e.g. round-tripped through SQLite) to aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

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
            implied_speed = None
            link_status = "VERIFIED_PLAUSIBLE"

            if prev_lat is not None and prev_lng is not None and prev_time is not None:
                dist_km = haversine_distance_km(prev_lat, prev_lng, lat, lng)
                total_distance += dist_km
                time_diff = (s.timestamp - prev_time).total_seconds() / 60.0
                delta_mins = round(time_diff, 1)
                
                # Impossible-speed / teleportation filter
                if time_diff > 0:
                    implied_speed = round(dist_km / (time_diff / 60.0), 1)
                    if implied_speed > settings.IMPOSSIBLE_SPEED_THRESHOLD_KMH:
                        link_status = "IMPOSSIBLE_SPEED"
                    elif implied_speed > settings.SUSPICIOUS_SPEED_THRESHOLD_KMH:
                        link_status = "LOW_CONFIDENCE_LINK"
                elif time_diff < 0:
                    # Scene loop discontinuity or backward PTS jump
                    link_status = "SCENE_DISCONTINUITY_RESET"
                    implied_speed = None
                    delta_mins = 0.0

            # Match method classification
            match_method = "PLATE_EXACT"
            if s.normalized_plate != normalized_query:
                dist = ANPREngine.calculate_levenshtein(s.normalized_plate, normalized_query)
                match_method = f"PLATE_FUZZY (dist={dist})" if dist <= 1 else "VISUAL_REID"

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
                    evidence_uri=s.evidence_uri,
                    match_method=match_method,
                    link_status=link_status,
                    implied_speed_kmh=implied_speed
                )
            )

            prev_lat = lat
            prev_lng = lng
            prev_time = s.timestamp

        first_seen = sightings[0].timestamp
        last_seen = sightings[-1].timestamp
        avg_speed = round(sum(s.speed_kmh for s in sightings) / len(sightings), 1)

        # Aggregate Route Confidence calculation
        has_impossible_speed = any(p.link_status == "IMPOSSIBLE_SPEED" for p in trajectory_points)
        avg_ocr_conf = sum(p.confidence for p in trajectory_points) / len(trajectory_points)
        
        # Base confidence from OCR + corroboration bonus
        corroboration_bonus = min(10.0, (len(trajectory_points) - 1) * 2.5)
        penalty = 35.0 if has_impossible_speed else 0.0
        route_conf = round(max(15.0, min(99.0, (avg_ocr_conf * 90.0) + corroboration_bonus - penalty)), 1)
        route_status = "FLAGGED_ANOMALY" if has_impossible_speed else "VERIFIED_CONTINUOUS"

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
            matched_watchlist=watchlist_out,
            route_confidence_pct=route_conf,
            route_status=route_status
        )

    # ------------------------------------------------------------------
    # LIVE PURSUIT / DEAD-RECKONING PREDICTED-POSITION ENGINE
    # ------------------------------------------------------------------
    # GIVIN has no in-vehicle GPS transponder to poll — a "live map" for a
    # stolen car is necessarily built from the CCTV/ANPR sightings it has
    # actually recorded. This engine turns the last two confirmed sightings
    # into a heading + speed vector and projects ("dead-reckons") a live
    # position forward every time it's called, similar to how a radar
    # controller extrapolates a contact between sweeps. The result is always
    # clearly labeled PREDICTED vs the CONFIRMED checkpoint it's based on,
    # and it also nominates the nearest CCTV camera ahead on that heading so
    # controllers know which feed is most likely to reconfirm the vehicle.
    STALE_AFTER_SEC = 600          # beyond this, freeze the marker & flag STALE
    MAX_LOOKAHEAD_KM = 120         # cap how far we'll project ahead of the last camera
    NEXT_CAMERA_CONE_DEG = 55      # how far off-heading a camera can be and still count as "ahead"
    NEXT_CAMERA_MAX_KM = 200

    @classmethod
    def predict_live_position(cls, db: Session, plate_number: str) -> Optional[LivePursuitPosition]:
        journey = cls.reconstruct_journey(db, plate_number)
        if not journey or not journey.trajectory:
            return None

        traj = journey.trajectory
        last = traj[-1]
        prev = traj[-2] if len(traj) >= 2 else None

        # Vector (heading + speed) the vehicle was last confirmed travelling on.
        if prev:
            heading = bearing_deg(prev.lat, prev.lng, last.lat, last.lng)
        else:
            heading = 0.0  # No prior fix — default heading, still shown as last-known point.
        speed_kmh = last.speed_kmh or (journey.average_speed_kmh or 50.0)

        last_confirmed_time = _as_utc(last.timestamp)
        now = datetime.now(timezone.utc)
        elapsed_sec = max(0.0, (now - last_confirmed_time).total_seconds())

        is_stale = elapsed_sec > cls.STALE_AFTER_SEC
        projection_sec = min(elapsed_sec, cls.STALE_AFTER_SEC)
        distance_km = min((speed_kmh * projection_sec / 3600.0), cls.MAX_LOOKAHEAD_KM)

        if distance_km > 0.01:
            live_lat, live_lng = destination_point(last.lat, last.lng, heading, distance_km)
        else:
            live_lat, live_lng = last.lat, last.lng

        # Nominate the most probable next CCTV checkpoint: nearest camera that
        # lies roughly within the vehicle's current heading cone.
        candidate_cameras = (
            db.query(Camera)
            .filter(Camera.id != last.camera_id, Camera.status == "ACTIVE")
            .all()
        )
        best_cam, best_dist = None, None
        for cam in candidate_cameras:
            d_km = haversine_distance_km(live_lat, live_lng, cam.lat, cam.lng)
            if d_km > cls.NEXT_CAMERA_MAX_KM:
                continue
            brg = bearing_deg(live_lat, live_lng, cam.lat, cam.lng)
            diff = min(abs(brg - heading), 360 - abs(brg - heading))
            if diff <= cls.NEXT_CAMERA_CONE_DEG and (best_dist is None or d_km < best_dist):
                best_cam, best_dist = cam, d_km

        predicted_next_camera = best_cam.name if best_cam else None
        predicted_next_district = best_cam.district if best_cam else None
        predicted_next_lat = best_cam.lat if best_cam else None
        predicted_next_lng = best_cam.lng if best_cam else None
        eta_sec = round((best_dist / speed_kmh) * 3600, 0) if (best_cam and speed_kmh > 0) else None

        trail_points = [[p.lat, p.lng] for p in traj[-6:]]

        watchlist = journey.matched_watchlist
        return LivePursuitPosition(
            plate_number=journey.plate_number,
            status="STALE" if is_stale else "LIVE_PREDICTED",
            lat=live_lat,
            lng=live_lng,
            heading_deg=round(heading, 1),
            speed_kmh=round(speed_kmh, 1),
            last_confirmed_camera=last.camera_name,
            last_confirmed_district=last.district,
            last_confirmed_time=last.timestamp,
            seconds_since_confirmed=round(elapsed_sec, 1),
            predicted_next_camera=predicted_next_camera,
            predicted_next_district=predicted_next_district,
            trail=trail_points,
            risk_level=watchlist.risk_level if watchlist else None,
            watchlist_reason=watchlist.reason if watchlist else None
        )

    @classmethod
    def validate_journey_physics(
        cls,
        cam1: Any,
        cam2: Any,
        time1: datetime,
        time2: datetime
    ) -> Dict[str, Any]:
        """Calculates distance, elapsed time, velocity, and impossible journey flag."""
        dist = haversine_distance_km(cam1.lat, cam1.lng, cam2.lat, cam2.lng)
        dt_sec = max(1.0, abs((_as_utc(time2) - _as_utc(time1)).total_seconds()))
        speed_kmh = round((dist / dt_sec) * 3600.0, 1)
        max_speed = getattr(settings, "IMPOSSIBLE_SPEED_THRESHOLD_KMH", 180.0)
        impossible = speed_kmh > max_speed
        return {
            "distance_km": dist,
            "calculated_speed_kmh": speed_kmh,
            "impossible": impossible,
            "provenance": "GEODESIC_ESTIMATE"
        }

    @classmethod
    def reconstruct_vehicle_route(
        cls,
        plate_number: str,
        db: Optional[Session] = None,
        time_window_hours: float = 24.0
    ) -> Dict[str, Any]:
        """Convenience wrapper to reconstruct journey as dictionary."""
        close_db = False
        if db is None:
            from backend.app.core.database import SessionLocal
            db = SessionLocal()
            close_db = True
        try:
            summary = cls.reconstruct_journey(db, plate_number)
            if not summary:
                return {"plate_number": plate_number, "trajectory": []}
            return summary.dict() if hasattr(summary, "dict") else summary.model_dump()
        finally:
            if close_db:
                db.close()


vehicle_tracker = VehicleTracker()

