"""
GIVIN Tactical Pursuit Containment Perimeter & Intercept Matrix Engine.
Calculates 5-min, 10-min, and 15-min reachable isochrone boundary polygons,
identifies enclosed CCTV cameras, and nominates tactical police intercept chokepoints.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.orm import Camera
from backend.app.services.vehicle_tracker import (
    haversine_distance_km, bearing_deg, destination_point, VehicleTracker
)

# Strategic highway toll plazas and river chokepoints in Gujarat
STRATEGIC_CHECKPOINTS = [
    {
        "name": "Anand Toll Plaza (NE-1)",
        "district": "Anand",
        "lat": 22.5645,
        "lng": 72.9289,
        "type": "TOLL_PLAZA"
    },
    {
        "name": "Bareja Intercept Checkpoint (NH-48)",
        "district": "Ahmedabad",
        "lat": 22.8622,
        "lng": 72.5855,
        "type": "POLICE_CHOWKI"
    },
    {
        "name": "Vasad Expressway Chokepoint",
        "district": "Vadodara",
        "lat": 22.4512,
        "lng": 73.0721,
        "type": "TOLL_PLAZA"
    },
    {
        "name": "Vaishnodevi Circle Checkpost (SG Highway)",
        "district": "Gandhinagar",
        "lat": 23.1365,
        "lng": 72.5412,
        "type": "HIGHWAY_JUNCTION"
    },
    {
        "name": "Bopal Ring Road Junction",
        "district": "Ahmedabad",
        "lat": 23.0332,
        "lng": 72.4655,
        "type": "HIGHWAY_JUNCTION"
    },
    {
        "name": "Golden Bridge / Narmada River Chokepoint",
        "district": "Bharuch",
        "lat": 21.7051,
        "lng": 72.9959,
        "type": "INTERCEPT_BARRIER"
    },
    {
        "name": "Kamrej Toll Plaza (Surat North)",
        "district": "Surat",
        "lat": 21.2678,
        "lng": 72.9614,
        "type": "TOLL_PLAZA"
    },
    {
        "name": "Chotila Highway Intercept Post",
        "district": "Surendranagar",
        "lat": 22.4215,
        "lng": 71.1982,
        "type": "POLICE_CHOWKI"
    }
]

def generate_directional_isochrone_polygon(
    center_lat: float,
    center_lng: float,
    heading_deg: float,
    speed_kmh: float,
    duration_mins: float,
    num_points: int = 24
) -> Tuple[List[List[float]], float]:
    """
    Generates an oriented, directionally-biased isochrone perimeter polygon.
    Vehicles travel further along their confirmed heading corridor (major axis)
    and experience lateral turning friction (minor axis = 0.5 * major axis).
    """
    hours = duration_mins / 60.0
    forward_radius_km = max(1.5, speed_kmh * hours)
    lateral_radius_km = max(0.8, forward_radius_km * 0.55)
    reverse_radius_km = max(0.5, forward_radius_km * 0.25)

    # Shift ellipse focus slightly forward along vehicle heading
    focus_shift_km = forward_radius_km * 0.35
    f_lat, f_lng = destination_point(center_lat, center_lng, heading_deg, focus_shift_km)

    polygon: List[List[float]] = []
    heading_rad = math.radians(heading_deg)

    for i in range(num_points):
        theta = (2.0 * math.pi * i) / num_points
        # Check if point is in the forward or rear hemisphere
        if -math.pi / 2 <= (theta - heading_rad) <= math.pi / 2 or \
           (theta - heading_rad) >= 3 * math.pi / 2 or (theta - heading_rad) <= -3 * math.pi / 2:
            r = forward_radius_km
        else:
            r = reverse_radius_km

        # Parametric offset in local tangent plane (km)
        bearing = (math.degrees(theta) + 360) % 360
        # Compute distance considering lateral constriction
        angle_to_heading = abs((bearing - heading_deg + 180) % 360 - 180)
        eccentricity_factor = 1.0 - (0.45 * math.sin(math.radians(angle_to_heading)))
        effective_r = r * eccentricity_factor

        pt_lat, pt_lng = destination_point(f_lat, f_lng, bearing, effective_r)
        polygon.append([pt_lat, pt_lng])

    # Close the polygon loop
    if polygon:
        polygon.append(polygon[0])

    return polygon, forward_radius_km

class ContainmentService:
    """
    Tactical Pursuit Isochrone & Intercept Matrix Engine.
    """

    @classmethod
    def compute_containment(
        cls,
        db: Session,
        plate_number: str
    ) -> Optional[Dict[str, Any]]:
        # Obtain current predicted pursuit position
        pursuit = VehicleTracker.predict_live_position(db, plate_number)
        if not pursuit:
            return None

        origin_lat = pursuit.lat
        origin_lng = pursuit.lng
        heading = pursuit.heading_deg
        speed = max(40.0, pursuit.speed_kmh)

        isochrones = []
        max_15_min_radius = 0.0

        for minutes in [5, 10, 15]:
            poly, radius = generate_directional_isochrone_polygon(
                center_lat=origin_lat,
                center_lng=origin_lng,
                heading_deg=heading,
                speed_kmh=speed,
                duration_mins=minutes
            )
            if minutes == 15:
                max_15_min_radius = radius

            isochrones.append({
                "minutes": minutes,
                "radius_km": round(radius, 1),
                "polygon": poly
            })

        # Identify all active CCTV cameras inside the 15-minute pursuit zone
        active_cameras = db.query(Camera).filter(Camera.status == "ACTIVE").all()
        enclosed_cams = []
        for cam in active_cameras:
            dist = haversine_distance_km(origin_lat, origin_lng, cam.lat, cam.lng)
            if dist <= (max_15_min_radius * 1.15):
                enclosed_cams.append(cam)

        # Identify candidate interception chokepoints along vehicle heading
        candidates = []
        for cp in STRATEGIC_CHECKPOINTS:
            dist = haversine_distance_km(origin_lat, origin_lng, cp["lat"], cp["lng"])
            if dist <= (max_15_min_radius * 1.8):
                brg = bearing_deg(origin_lat, origin_lng, cp["lat"], cp["lng"])
                diff = min(abs(brg - heading), 360 - abs(brg - heading))

                # Higher intercept probability if chokepoint is directly within forward cone
                alignment_factor = max(0.1, math.cos(math.radians(diff)))
                prob = min(98.0, round((alignment_factor ** 1.5) * 100.0, 1))

                eta_sec = round((dist / speed) * 3600.0, 0) if speed > 0 else 999.0

                candidates.append({
                    "checkpoint_name": cp["name"],
                    "district": cp["district"],
                    "lat": cp["lat"],
                    "lng": cp["lng"],
                    "checkpoint_type": cp["type"],
                    "camera_id": None,
                    "distance_km": dist,
                    "eta_sec": eta_sec,
                    "interception_probability_pct": prob
                })

        candidates.sort(key=lambda x: x["interception_probability_pct"], reverse=True)
        top_checkpoints = candidates[:5]

        # Generate tactical recommendation text
        primary_cp = top_checkpoints[0]["checkpoint_name"] if top_checkpoints else "Next Toll Plaza"
        eta_min = round(top_checkpoints[0]["eta_sec"] / 60.0, 1) if top_checkpoints else 10.0
        recommendation = (
            f"Tactical Action: Deploy Barricade at {primary_cp} (ETA: {eta_min} min). "
            f"Alerting {len(enclosed_cams)} cameras in {pursuit.last_confirmed_district} perimeter."
        )

        return {
            "plate_number": pursuit.plate_number,
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
            "heading_deg": heading,
            "speed_kmh": speed,
            "isochrones": isochrones,
            "enclosed_camera_ids": [c.id for c in enclosed_cams],
            "enclosed_camera_count": len(enclosed_cams),
            "intercept_checkpoints": top_checkpoints,
            "tactical_recommendation": recommendation
        }

containment_service = ContainmentService()
