"""
High-Throughput Sighting Event Generator for GIVIN 80,000 Scale Testing.
Generates synthetic ANPR sightings with Gujarat vehicle registration formatting:
- Normal load: 1,000 events/sec
- Busy period: 10,000 events/sec
- Major incident / festival: 50,000 events/sec
- Worst burst: 100,000 events/sec
"""

import time
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Iterator, List, Optional
from scale_testing.camera_profiles.district_fleet import GUJARAT_DISTRICTS_33


class SightingGenerator:
    """Generates synthetic canonical vehicle sightings across 80,000 virtual cameras."""

    VEHICLE_TYPES = ["car", "suv", "motorcycle", "auto_rickshaw", "truck", "bus"]
    PLATE_LETTERS = ["AB", "BC", "CD", "EF", "GH", "JK", "LM", "NP", "RS", "ST", "UV", "WX", "YZ"]

    # Pre-defined hotlist plates for alert generation verification
    HOTLIST_PLATES = [
        "GJ01AB1234", "GJ05CD5678", "GJ06EF9012", "GJ03GH3456",
        "GJ18JK7890", "GJ12LM2345", "GJ04NP6789", "GJ10RS0123"
    ]

    @classmethod
    def generate_plate(cls, rto_code: str = "GJ01", is_hotlist: bool = False) -> str:
        """Generates standard Indian High Security Registration Plate (HSRP) format."""
        if is_hotlist:
            return random.choice(cls.HOTLIST_PLATES)
        letters = random.choice(cls.PLATE_LETTERS)
        digits = f"{random.randint(1000, 9999)}"
        return f"{rto_code}{letters}{digits}"

    @classmethod
    def iter_sightings(
        cls,
        count: int = 10000,
        hotlist_rate: float = 0.01,
        camera_pool: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Lazily generates canonical sighting events.
        hotlist_rate: fraction of events matching watchlist (default: 1%)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        pts_base = time.time() * 1000.0

        for i in range(count):
            if camera_pool:
                cam = camera_pool[i % len(camera_pool)]
                district = cam["district"]
                rto = cam.get("rto_code", "GJ01")
                cam_id = cam["camera_id"]
                lat = cam.get("lat", 23.0225)
                lng = cam.get("lng", 72.5714)
            else:
                dist_meta = GUJARAT_DISTRICTS_33[i % len(GUJARAT_DISTRICTS_33)]
                district = dist_meta["district"]
                rto = dist_meta["rto"]
                cam_id = f"GJ-{dist_meta['code']}-{((i * 17) % dist_meta['cameras']) + 1:06d}"
                lat = dist_meta["lat"]
                lng = dist_meta["lng"]

            is_hot = (random.random() < hotlist_rate)
            plate = cls.generate_plate(rto_code=rto, is_hotlist=is_hot)
            vehicle_type = cls.VEHICLE_TYPES[i % len(cls.VEHICLE_TYPES)]
            confidence = round(0.85 + (random.random() * 0.14), 2)
            speed = round(20.0 + (random.random() * 70.0), 1)

            yield {
                "event_id": f"evt-{uuid.uuid4().hex[:12]}",
                "camera_id": cam_id,
                "district": district,
                "timestamp": now_iso,
                "pts_timestamp_ms": pts_base + (i * 10),
                "plate_text": plate,
                "confidence": confidence,
                "vehicle_type": vehicle_type,
                "speed_kmh": speed,
                "lat": lat,
                "lng": lng,
                "is_hotlist_target": is_hot,
                "provenance": "SIMULATION_SCALE_TEST"
            }

    @classmethod
    def generate_batch(
        cls,
        batch_size: int = 1000,
        hotlist_rate: float = 0.01,
        camera_pool: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Generates an in-memory batch of canonical sightings."""
        return list(cls.iter_sightings(count=batch_size, hotlist_rate=hotlist_rate, camera_pool=camera_pool))
