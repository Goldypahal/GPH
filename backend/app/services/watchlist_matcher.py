from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.models.orm import Watchlist, Alert, VehicleSighting, Camera
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.config import settings

class WatchlistMatcher:
    """Exact/fuzzy watchlist matching with confidence-aware alert deduplication."""

    @classmethod
    def check_plate(cls, db: Session, sighting: VehicleSighting) -> Optional[Tuple[Watchlist, str, float]]:
        target = ANPREngine.normalize_plate(sighting.normalized_plate)
        active = db.query(Watchlist).filter(Watchlist.status == "ACTIVE").all()
        for item in active:
            if ANPREngine.normalize_plate(item.vehicle_number) == target:
                return item, "EXACT", min(1.0, max(0.0, sighting.confidence))
        for item in active:
            candidate = ANPREngine.normalize_plate(item.vehicle_number)
            distance = ANPREngine.calculate_levenshtein(candidate, target)
            if distance <= settings.FUZZY_MATCH_DISTANCE_THRESHOLD and len(target) >= 8:
                return item, f"FUZZY (dist={distance})", max(0.70, sighting.confidence - distance * 0.15)
        return None

    @classmethod
    def trigger_alert_if_matched(cls, db: Session, sighting: VehicleSighting) -> Optional[Alert]:
        match = cls.check_plate(db, sighting)
        if not match:
            return None
        item, match_type, match_conf = match
        existing_for_sighting = db.query(Alert).filter(Alert.sighting_id == sighting.id).first()
        if existing_for_sighting:
            return existing_for_sighting

        # Collapse repeated frames from the same camera into one operational incident.
        window_start = (sighting.timestamp or datetime.now(timezone.utc)) - timedelta(seconds=30)
        recent = db.query(Alert).join(VehicleSighting, Alert.sighting_id == VehicleSighting.id).filter(
            Alert.camera_id == sighting.camera_id,
            Alert.plate_text == sighting.plate_text,
            Alert.status.in_(["NEW", "ACKNOWLEDGED", "INVESTIGATING"]),
            VehicleSighting.timestamp >= window_start,
        ).order_by(Alert.created_at.desc()).first()
        if recent:
            recent.remarks = (recent.remarks or "") + f" | Supporting detection {sighting.id[:8]} ({sighting.confidence:.0%})"
            db.commit(); db.refresh(recent)
            return recent

        camera = db.query(Camera).filter(Camera.id == sighting.camera_id).first()
        cam_loc = camera.location_name if camera else "Unknown location"
        alert_uid = f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{sighting.id[:4].upper()}"
        alert = Alert(
            alert_uid=alert_uid,
            watchlist_id=item.id,
            sighting_id=sighting.id,
            camera_id=sighting.camera_id,
            plate_text=sighting.plate_text,
            risk_level=item.risk_level,
            status="NEW",
            remarks=(f"Match={match_type}; confidence={match_conf:.0%}; source={item.registered_authority}; "
                     f"reason={item.reason}; FIR={item.case_fir_number}; location={cam_loc}"),
        )
        db.add(alert); db.commit(); db.refresh(alert)
        return alert
