"""
GIVIN Camera Network Topology & Spatial Adjacency Graph Engine.
Builds directional road corridors, camera transition matrices P(C_j | C_i),
and downstream trajectory prediction with calibrated ETAs across Gujarat.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from backend.app.models.orm import Camera
from backend.app.services.vehicle_tracker import haversine_distance_km, bearing_deg

# Major highway speed profiles (km/h) across Gujarat
CORRIDOR_PROFILES = {
    "NE-1 Ahmedabad-Vadodara Expressway": {"speed_kmh": 100.0, "type": "EXPRESSWAY"},
    "SG Highway Corridor": {"speed_kmh": 60.0, "type": "URBAN_ARTERIAL"},
    "NH-48 Golden Corridor (Vadodara-Surat)": {"speed_kmh": 80.0, "type": "NATIONAL_HIGHWAY"},
    "Sardar Patel Ring Road": {"speed_kmh": 65.0, "type": "RING_ROAD"},
    "Saurashtra Corridor (Rajkot-Jamnagar)": {"speed_kmh": 75.0, "type": "STATE_HIGHWAY"},
    "North Gujarat Corridor (Mehsana-Palanpur)": {"speed_kmh": 70.0, "type": "STATE_HIGHWAY"},
    "Intra-District Link": {"speed_kmh": 50.0, "type": "URBAN_ROAD"}
}

def determine_corridor(cam1: Camera, cam2: Camera) -> str:
    """Classifies the primary connecting highway corridor between two CCTV cameras."""
    locs = (cam1.location_name + " " + cam2.location_name).lower()
    districts = {cam1.district.lower(), cam2.district.lower()}

    if "expressway" in locs or ("ahmedabad" in districts and "vadodara" in districts):
        return "NE-1 Ahmedabad-Vadodara Expressway"
    elif "sg highway" in locs or "s.g." in locs or ("ahmedabad" in districts and "gandhinagar" in districts):
        return "SG Highway Corridor"
    elif "ring road" in locs:
        return "Sardar Patel Ring Road"
    elif "surat" in districts or "bharuch" in districts or "navsari" in districts:
        return "NH-48 Golden Corridor (Vadodara-Surat)"
    elif "rajkot" in districts or "jamnagar" in districts:
        return "Saurashtra Corridor (Rajkot-Jamnagar)"
    elif "mehsana" in districts or "palanpur" in districts or "banaskantha" in districts:
        return "North Gujarat Corridor (Mehsana-Palanpur)"
    return "Intra-District Link"

class CameraNetworkGraph:
    """
    Statewide Camera Topology Graph.
    Nodes: CCTV cameras across all 26 departments.
    Edges: Arterial road links with calibrated distances and travel time bounds.
    """

    def __init__(self):
        self._cached_db_id = None
        self._adjacency_map: Dict[str, List[Dict[str, Any]]] = {}
        self._all_edges: List[Dict[str, Any]] = []
        self._all_corridors: set = set()

    def build_graph(self, db: Session, max_hop_distance_km: float = 65.0) -> None:
        """Constructs camera adjacency matrix from registered active cameras."""
        cameras = db.query(Camera).filter(Camera.status == "ACTIVE").all()
        self._adjacency_map.clear()
        self._all_edges.clear()
        self._all_corridors.clear()

        for c in cameras:
            self._adjacency_map[c.id] = []

        # Connect cameras that lie within reasonable continuous travel range
        for i, c1 in enumerate(cameras):
            for j, c2 in enumerate(cameras):
                if i == j:
                    continue
                dist = haversine_distance_km(c1.lat, c1.lng, c2.lat, c2.lng)
                if dist <= max_hop_distance_km:
                    corridor = determine_corridor(c1, c2)
                    profile = CORRIDOR_PROFILES.get(corridor, CORRIDOR_PROFILES["Intra-District Link"])
                    speed = profile["speed_kmh"]
                    travel_time_min = round((dist / speed) * 60.0, 1)
                    bearing = bearing_deg(c1.lat, c1.lng, c2.lat, c2.lng)

                    edge = {
                        "from_camera_id": c1.id,
                        "from_camera_name": c1.name,
                        "from_lat": c1.lat,
                        "from_lng": c1.lng,
                        "to_camera_id": c2.id,
                        "to_camera_name": c2.name,
                        "to_lat": c2.lat,
                        "to_lng": c2.lng,
                        "distance_km": dist,
                        "bearing_deg": round(bearing, 1),
                        "typical_travel_time_min": travel_time_min,
                        "corridor": corridor,
                        # Initial baseline transition weight inversely proportional to distance
                        "transition_weight": max(0.05, round(1.0 / (1.0 + (dist / 10.0)), 3))
                    }
                    self._adjacency_map[c1.id].append(edge)
                    self._all_edges.append(edge)
                    self._all_corridors.add(corridor)

        # Normalize outgoing transition probabilities per camera
        for cam_id, edges in self._adjacency_map.items():
            total_weight = sum(e["transition_weight"] for e in edges)
            if total_weight > 0:
                for e in edges:
                    e["transition_probability"] = round(e["transition_weight"] / total_weight, 3)

    def get_downstream_cameras(
        self,
        db: Session,
        current_camera_id: str,
        current_heading_deg: Optional[float] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Ranks the most probable downstream cameras reachable from the current camera.
        Filters and weights candidates by vehicle heading alignment.
        """
        if not self._adjacency_map or current_camera_id not in self._adjacency_map:
            self.build_graph(db)

        outgoing = self._adjacency_map.get(current_camera_id, [])
        if not outgoing:
            return []

        scored_candidates = []
        for edge in outgoing:
            score = edge["transition_probability"]

            if current_heading_deg is not None:
                # Heading deviation penalty
                diff = min(
                    abs(edge["bearing_deg"] - current_heading_deg),
                    360 - abs(edge["bearing_deg"] - current_heading_deg)
                )
                if diff < 45.0:
                    score *= 2.5 # Forward corridor alignment bonus
                elif diff < 90.0:
                    score *= 1.2
                else:
                    score *= 0.1 # Significant reverse or perpendicular turn penalty

            scored_candidates.append({
                "camera_id": edge["to_camera_id"],
                "camera_name": edge["to_camera_name"],
                "lat": edge["to_lat"],
                "lng": edge["to_lng"],
                "distance_km": edge["distance_km"],
                "bearing_deg": edge["bearing_deg"],
                "typical_travel_time_min": edge["typical_travel_time_min"],
                "corridor": edge["corridor"],
                "confidence_score": round(score, 3)
            })

        scored_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
        return scored_candidates[:top_k]

    def get_topology_summary(self, db: Session) -> Dict[str, Any]:
        """Returns statewide graph stats for frontend visualization and system telemetry."""
        if not self._adjacency_map:
            self.build_graph(db)

        total_cameras = db.query(Camera).filter(Camera.status == "ACTIVE").count()
        return {
            "total_cameras": total_cameras,
            "total_corridor_edges": len(self._all_edges),
            "active_corridors": sorted(list(self._all_corridors)),
            "edges": [
                {
                    "from_camera_id": e["from_camera_id"],
                    "from_camera_name": e["from_camera_name"],
                    "to_camera_id": e["to_camera_id"],
                    "to_camera_name": e["to_camera_name"],
                    "distance_km": e["distance_km"],
                    "typical_travel_time_min": e["typical_travel_time_min"],
                    "transition_probability": e.get("transition_probability", 0.0),
                    "corridor": e["corridor"]
                }
                for e in self._all_edges[:100] # Return representative primary edges
            ]
        }

camera_network_graph = CameraNetworkGraph()
