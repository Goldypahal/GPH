from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.orm import Watchlist, Alert, VehicleSighting, Camera
from backend.app.services.anpr_engine import ANPREngine
from backend.app.core.config import settings
import datetime

class WatchlistMatcher:
    """
    Evaluates vehicle plate sightings against active Law Enforcement Watchlists
    (VAHAN Stolen Registry, eGujCop CCTNS Hotlist, Inter-State BOLO).
    """

    @classmethod
    def check_plate(
        cls,
        db: Session,
        sighting: VehicleSighting
    ) -> Optional[Tuple[Watchlist, str, float]]:
        """
        Performs dual-tier lookup:
        1. Exact match on normalized plate
        2. Fuzzy match (distance <= threshold) if exact fails
        Returns (matched_watchlist_entry, match_type, match_confidence) or None.
        """
        active_watchlists = db.query(Watchlist).filter(Watchlist.status == "ACTIVE").all()
        normalized_target = sighting.normalized_plate

        # Step 1: Exact Match
        for item in active_watchlists:
            norm_item = ANPREngine.normalize_plate(item.vehicle_number)
            if norm_item == normalized_target:
                return item, "EXACT", 1.0

        # Step 2: Fuzzy Match for partially obscured/dirty plates
        for item in active_watchlists:
            norm_item = ANPREngine.normalize_plate(item.vehicle_number)
            distance = ANPREngine.calculate_levenshtein(norm_item, normalized_target)
            if distance <= settings.FUZZY_MATCH_DISTANCE_THRESHOLD and len(normalized_target) >= 8:
                # Slight penalty on fuzzy match
                match_conf = max(0.70, 1.0 - (distance * 0.15))
                return item, f"FUZZY (dist={distance})", match_conf

        return None

    @classmethod
    def trigger_alert_if_matched(
        cls,
        db: Session,
        sighting: VehicleSighting
    ) -> Optional[Alert]:
        """
        Evaluates sighting and generates an Alert in the database if matched.
        """
        match_result = cls.check_plate(db, sighting)
        if not match_result:
            return None

        watchlist_item, match_type, match_conf = match_result
        
        # Check if an active alert for this sighting already exists
        existing = db.query(Alert).filter(Alert.sighting_id == sighting.id).first()
        if existing:
            return existing

        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        alert_uid = f"ALT-{now_str}-{sighting.id[:4].upper()}"

        camera = db.query(Camera).filter(Camera.id == sighting.camera_id).first()
        cam_loc = camera.location_name if camera else "Gujarat Highway Checkpoint"

        new_alert = Alert(
            alert_uid=alert_uid,
            watchlist_id=watchlist_item.id,
            sighting_id=sighting.id,
            camera_id=sighting.camera_id,
            plate_text=sighting.plate_text,
            risk_level=watchlist_item.risk_level,
            status="NEW",
            remarks=f"Match Type: {match_type} ({match_conf*100:.0f}% confidence). Reason: {watchlist_item.reason} [FIR: {watchlist_item.case_fir_number}] at {cam_loc}.",
            dispatched_unit=None,
            acknowledged_by=None
        )

        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert
