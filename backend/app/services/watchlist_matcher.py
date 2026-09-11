from typing import Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.models.orm import Watchlist, Alert, VehicleSighting, Camera
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.config import settings

import time
import threading

class CachedWatchlistEntry:
    def __init__(self, id: str, vehicle_number: str, risk_level: str, registered_authority: str, reason: str, case_fir_number: str):
        self.id = id
        self.vehicle_number = vehicle_number
        self.risk_level = risk_level
        self.registered_authority = registered_authority
        self.reason = reason
        self.case_fir_number = case_fir_number


class WatchlistMatcher:
    """Exact/fuzzy watchlist matching with confidence-aware alert deduplication."""

    _cached_active: list = []
    _last_cache_time: float = 0.0
    _CACHE_TTL_SEC: float = 2.0
    _cache_lock = threading.Lock()

    @classmethod
    def invalidate_cache(cls):
        with cls._cache_lock:
            cls._cached_active = []
            cls._last_cache_time = 0.0

    @classmethod
    def get_active_watchlist(cls, db: Session) -> list:
        now = time.time()
        with cls._cache_lock:
            if cls._cached_active and (now - cls._last_cache_time) < cls._CACHE_TTL_SEC:
                return cls._cached_active
        # Refresh outside lock to avoid holding lock during I/O
        fresh = db.query(Watchlist).filter(Watchlist.status == "ACTIVE").all()
        cached = [
            CachedWatchlistEntry(
                id=item.id,
                vehicle_number=item.vehicle_number,
                risk_level=item.risk_level,
                registered_authority=item.registered_authority,
                reason=item.reason,
                case_fir_number=item.case_fir_number
            )
            for item in fresh
        ]
        with cls._cache_lock:
            cls._cached_active = cached
            cls._last_cache_time = time.time()
            return cls._cached_active

    @classmethod
    def check_plate(cls, db: Session, sighting: VehicleSighting) -> Optional[Tuple[Any, str, float]]:
        target = ANPREngine.normalize_plate(sighting.normalized_plate)
        active = cls.get_active_watchlist(db)
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
        cached_item, match_type, match_conf = match
        # Ensure item is attached to the current active DB session
        attached_item = db.query(Watchlist).filter(Watchlist.id == cached_item.id).first()
        item = attached_item if attached_item else cached_item
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
        if not sighting.id:
            import uuid
            sighting.id = f"sight-{uuid.uuid4().hex[:8]}"
            db.add(sighting)
            db.flush()
        import uuid
        alert_uid = f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
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
