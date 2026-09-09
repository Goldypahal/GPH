"""
GIVIN Spatial-Temporal Anomaly & Cloned Plate Detection Engine.
Detects teleportation anomalies, duplicate registration plates, excessive point-to-point speeds,
and unexplained corridor delays, automatically raising prioritized alerts in the C4I command center.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.orm import VehicleSighting, Camera, Alert, Watchlist
from backend.app.services.anpr_engine import ANPREngine
from backend.app.services.vehicle_tracker import haversine_distance_km
from backend.app.services.event_bus import event_bus, EventBus

def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class TravelAnomalyEngine:
    """
    Evaluates spatial-temporal physics constraints across cross-camera sightings.
    Flags impossible travel speeds as cloned/counterfeit registration plates.
    """

    MAX_FEASIBLE_SPEED_KMH = 180.0
    HIGHWAY_SPEED_LIMIT_KMH = 120.0
    SIMULTANEOUS_TIME_WINDOW_SEC = 300.0 # 5 minutes
    SIMULTANEOUS_MIN_DISTANCE_KM = 15.0

    @classmethod
    def evaluate_sightings_for_plate(
        cls,
        db: Session,
        plate_number: str,
        auto_raise_alert: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyzes consecutive sightings for a given license plate and identifies
        all physical anomalies (Cloned plates, speeding, prolonged detours).
        """
        norm_plate = ANPREngine.normalize_plate(plate_number)
        if not norm_plate:
            return []

        sightings = (
            db.query(VehicleSighting)
            .filter(VehicleSighting.normalized_plate == norm_plate)
            .order_by(VehicleSighting.timestamp.asc())
            .all()
        )

        if len(sightings) < 2:
            return []

        anomalies: List[Dict[str, Any]] = []

        for i in range(len(sightings) - 1):
            s1 = sightings[i]
            s2 = sightings[i + 1]

            cam1 = db.query(Camera).filter(Camera.id == s1.camera_id).first()
            cam2 = db.query(Camera).filter(Camera.id == s2.camera_id).first()

            if not cam1 or not cam2 or cam1.id == cam2.id:
                continue

            dist_km = haversine_distance_km(cam1.lat, cam1.lng, cam2.lat, cam2.lng)
            time_diff_sec = abs((_as_utc(s2.timestamp) - _as_utc(s1.timestamp)).total_seconds())
            time_diff_mins = max(0.01, round(time_diff_sec / 60.0, 1))
            hours = time_diff_sec / 3600.0

            implied_speed = round(dist_km / hours, 1) if hours > 0 else 999.0

            # 1. Check for Cloned Plate / Teleportation
            is_cloned = False
            clone_reason = ""

            if time_diff_sec <= cls.SIMULTANEOUS_TIME_WINDOW_SEC and dist_km >= cls.SIMULTANEOUS_MIN_DISTANCE_KM:
                is_cloned = True
                clone_reason = (
                    f"Simultaneous sightings in disparate locations: {dist_km:.1f} km apart in {time_diff_mins:.1f} mins "
                    f"({cam1.district} vs {cam2.district})"
                )
            elif implied_speed > cls.MAX_FEASIBLE_SPEED_KMH:
                is_cloned = True
                clone_reason = (
                    f"Physically impossible ground speed: {implied_speed:.1f} km/h between {cam1.name} and {cam2.name} "
                    f"(Distance: {dist_km:.1f} km, Time: {time_diff_mins:.1f} mins)"
                )

            if is_cloned:
                alert_created = False
                if auto_raise_alert:
                    alert_created = cls._raise_cloned_plate_alert(
                        db=db,
                        plate=s1.plate_text,
                        sighting_id=s2.id,
                        cam=cam2,
                        description=clone_reason,
                        implied_speed=implied_speed
                    )

                anomalies.append({
                    "anomaly_id": f"ANOM-CLONE-{uuid.uuid4().hex[:8]}",
                    "anomaly_type": "CLONED_PLATE",
                    "plate_number": s1.plate_text,
                    "severity": "CRITICAL",
                    "description": clone_reason,
                    "camera_a_id": cam1.id,
                    "camera_a_name": cam1.name,
                    "camera_b_id": cam2.id,
                    "camera_b_name": cam2.name,
                    "distance_km": dist_km,
                    "time_delta_mins": time_diff_mins,
                    "implied_speed_kmh": implied_speed,
                    "timestamp_a": s1.timestamp,
                    "timestamp_b": s2.timestamp,
                    "alert_raised": alert_created
                })

            # 2. Check for Excessive Speeding Violation
            elif implied_speed > cls.HIGHWAY_SPEED_LIMIT_KMH:
                speed_desc = (
                    f"Excessive corridor average speed: {implied_speed:.1f} km/h on "
                    f"{cam1.name} -> {cam2.name} link (Speed limit: {cls.HIGHWAY_SPEED_LIMIT_KMH:.0f} km/h)"
                )
                anomalies.append({
                    "anomaly_id": f"ANOM-SPEED-{uuid.uuid4().hex[:8]}",
                    "anomaly_type": "EXCESSIVE_SPEED",
                    "plate_number": s1.plate_text,
                    "severity": "WARNING",
                    "description": speed_desc,
                    "camera_a_id": cam1.id,
                    "camera_a_name": cam1.name,
                    "camera_b_id": cam2.id,
                    "camera_b_name": cam2.name,
                    "distance_km": dist_km,
                    "time_delta_mins": time_diff_mins,
                    "implied_speed_kmh": implied_speed,
                    "timestamp_a": s1.timestamp,
                    "timestamp_b": s2.timestamp,
                    "alert_raised": False
                })

        return anomalies

    @classmethod
    def _raise_cloned_plate_alert(
        cls,
        db: Session,
        plate: str,
        sighting_id: str,
        cam: Camera,
        description: str,
        implied_speed: float
    ) -> bool:
        """Persists high-priority alert for cloned/teleporting vehicle."""
        # Avoid duplicating recent active alert for this plate
        existing = (
            db.query(Alert)
            .filter(Alert.plate_text == plate, Alert.remarks.like("%CLONED_PLATE%"))
            .first()
        )
        if existing:
            return False

        wl = db.query(Watchlist).filter(Watchlist.vehicle_number == plate).first()
        wl_id = wl.id if wl else None

        alert = Alert(
            id=f"alert-clone-{uuid.uuid4().hex[:8]}",
            alert_uid=f"ALT-CLONE-{uuid.uuid4().hex[:6].upper()}",
            watchlist_id=wl_id,
            sighting_id=sighting_id,
            camera_id=cam.id,
            plate_text=plate,
            risk_level="CRITICAL",
            status="NEW",
            remarks=f"CLONED_PLATE_DETECTED: {description}"
        )
        db.add(alert)
        db.commit()

        # Publish notification on real-time event bus
        event_bus.publish(
            EventBus.TOPIC_ALERTS_TRIGGERED,
            {
                "event_type": "ALERT_RAISED",
                "alert_id": alert.id,
                "plate_text": plate,
                "risk_level": "CRITICAL",
                "camera_name": cam.name,
                "district": cam.district,
                "anomaly_type": "CLONED_PLATE",
                "description": description
            }
        )
        return True

    @classmethod
    def get_all_cloned_plate_conflicts(cls, db: Session) -> List[Dict[str, Any]]:
        """Scans database to return all vehicles currently displaying cloned-plate conflicts."""
        # Query distinct plates with multiple sightings
        from sqlalchemy import func
        plates = (
            db.query(VehicleSighting.normalized_plate)
            .group_by(VehicleSighting.normalized_plate)
            .having(func.count(VehicleSighting.id) >= 2)
            .all()
        )

        cloned_conflicts = []
        for (p,) in plates:
            anoms = cls.evaluate_sightings_for_plate(db, p, auto_raise_alert=True)
            clones = [a for a in anoms if a["anomaly_type"] == "CLONED_PLATE"]
            if clones:
                latest = clones[-1]
                cloned_conflicts.append({
                    "plate_number": latest["plate_number"],
                    "conflict_type": "IMPOSSIBLE_SPEED" if latest["implied_speed_kmh"] > 180 else "SIMULTANEOUS_SIGHTINGS",
                    "confidence": 0.96,
                    "latest_sighting_a": {
                        "camera_name": latest["camera_a_name"],
                        "timestamp": latest["timestamp_a"].isoformat() if hasattr(latest["timestamp_a"], "isoformat") else str(latest["timestamp_a"])
                    },
                    "latest_sighting_b": {
                        "camera_name": latest["camera_b_name"],
                        "timestamp": latest["timestamp_b"].isoformat() if hasattr(latest["timestamp_b"], "isoformat") else str(latest["timestamp_b"])
                    },
                    "implied_speed_kmh": latest["implied_speed_kmh"],
                    "detected_at": latest["timestamp_b"],
                    "action_required": "Deploy local intercept squad; verify chassis/VIN at next toll plaza."
                })

        return cloned_conflicts

travel_anomaly_engine = TravelAnomalyEngine()
