"""
Camera Fleet Generator for GIVIN 80,000 Scale Testing.
Generates realistic, heterogeneous camera client definitions across all 33 Gujarat districts:
- Memory-efficient iterator / generator
- Configurable scale: 50 -> 100 -> 500 -> 1,000 -> 5,000 -> 10,000 -> 25,000 -> 80,000
- Deterministic IDs and spatial coordinates
"""

import json
import csv
import math
from typing import Dict, Any, Iterator, List, Optional
from scale_testing.camera_profiles.district_fleet import GUJARAT_DISTRICTS_33, TOTAL_STATEWIDE_CAMERAS


class CameraGenerator:
    """Generates heterogeneous camera fleet specifications across Gujarat."""

    RESOLUTIONS = ["1920x1080", "1280x720", "2560x1440", "3840x2160"]
    CODECS = ["H.264", "H.265"]
    FRAME_RATES = [25, 20, 15]

    @classmethod
    def iter_fleet(cls, limit: int = TOTAL_STATEWIDE_CAMERAS) -> Iterator[Dict[str, Any]]:
        """
        Lazily yields virtual camera profiles up to `limit`.
        Memory footprint is O(1) per yielded camera.
        """
        produced = 0
        scale_factor = min(1.0, limit / float(TOTAL_STATEWIDE_CAMERAS))

        for district_meta in GUJARAT_DISTRICTS_33:
            dist_total = district_meta["cameras"]
            # Scale proportionally if limit < 80000
            if limit < TOTAL_STATEWIDE_CAMERAS:
                dist_target = max(1, int(round(dist_total * scale_factor)))
            else:
                dist_target = dist_total

            for idx in range(1, dist_target + 1):
                if produced >= limit:
                    return

                cam_num = f"{idx:06d}"
                camera_id = f"GJ-{district_meta['code']}-{cam_num}"
                
                # Heterogeneous property distribution
                res_idx = (idx * 7) % len(cls.RESOLUTIONS)
                resolution = cls.RESOLUTIONS[res_idx if res_idx != 3 else (0 if idx % 10 != 0 else 3)]
                codec = cls.CODECS[0] if (idx % 5 != 0) else cls.CODECS[1]
                fps = cls.FRAME_RATES[(idx * 3) % len(cls.FRAME_RATES)]
                
                bitrate_kbps = 4096 if "1080" in resolution else (2048 if "720" in resolution else 8192)

                # Radial coordinate jitter around district centroid (~0.05 deg radius)
                angle = (idx * 0.61803398875) * 2 * math.pi
                radius = 0.01 + ((idx % 100) / 100.0) * 0.04
                lat = round(district_meta["lat"] + (radius * math.cos(angle)), 6)
                lng = round(district_meta["lng"] + (radius * math.sin(angle)), 6)

                cam = {
                    "camera_id": camera_id,
                    "name": f"{district_meta['district']} Surveillance Node {idx}",
                    "district": district_meta["district"],
                    "district_code": district_meta["code"],
                    "rto_code": district_meta["rto"],
                    "region": district_meta["region"],
                    "gateway_subnet": district_meta["gateway_subnet"],
                    "lat": lat,
                    "lng": lng,
                    "resolution": resolution,
                    "codec": codec,
                    "fps": fps,
                    "bitrate_kbps": bitrate_kbps,
                    "status": "ONLINE",
                    "protocol": "RTSP",
                    "rtsp_url": f"rtsp://{district_meta['gateway_subnet'].split('/')[0].rsplit('.', 1)[0]}.{idx % 254 + 1}:8554/stream/{camera_id.lower()}",
                    "vendor": "GIVIN-Heterogeneous-Edge"
                }
                yield cam
                produced += 1

        # Top-up any remainder due to integer rounding
        d_idx = 0
        while produced < limit:
            district_meta = GUJARAT_DISTRICTS_33[d_idx % len(GUJARAT_DISTRICTS_33)]
            idx = produced + 1
            cam_num = f"{idx:06d}"
            camera_id = f"GJ-{district_meta['code']}-{cam_num}"
            cam = {
                "camera_id": camera_id,
                "name": f"{district_meta['district']} Surveillance Node {idx}",
                "district": district_meta["district"],
                "district_code": district_meta["code"],
                "rto_code": district_meta["rto"],
                "region": district_meta["region"],
                "gateway_subnet": district_meta["gateway_subnet"],
                "lat": district_meta["lat"],
                "lng": district_meta["lng"],
                "resolution": "1920x1080",
                "codec": "H.264",
                "fps": 25,
                "bitrate_kbps": 4096,
                "status": "ONLINE",
                "protocol": "RTSP",
                "rtsp_url": f"rtsp://{district_meta['gateway_subnet'].split('/')[0].rsplit('.', 1)[0]}.{idx % 254 + 1}:8554/stream/{camera_id.lower()}",
                "vendor": "GIVIN-Heterogeneous-Edge"
            }
            yield cam
            produced += 1
            d_idx += 1

    @classmethod
    def generate_list(cls, limit: int = TOTAL_STATEWIDE_CAMERAS) -> List[Dict[str, Any]]:
        """Returns fleet as a list in memory."""
        return list(cls.iter_fleet(limit=limit))

    @classmethod
    def export_to_json(cls, filepath: str, limit: int = TOTAL_STATEWIDE_CAMERAS) -> int:
        """Streams fleet directly to JSON file without loading whole list into memory."""
        count = 0
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("[\n")
            for cam in cls.iter_fleet(limit=limit):
                if count > 0:
                    f.write(",\n")
                f.write(json.dumps(cam))
                count += 1
            f.write("\n]\n")
        return count

    @classmethod
    def export_to_csv(cls, filepath: str, limit: int = TOTAL_STATEWIDE_CAMERAS) -> int:
        """Exports fleet to CSV format."""
        count = 0
        fieldnames = [
            "camera_id", "name", "district", "district_code", "rto_code",
            "region", "gateway_subnet", "lat", "lng", "resolution",
            "codec", "fps", "bitrate_kbps", "status", "protocol", "rtsp_url", "vendor"
        ]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for cam in cls.iter_fleet(limit=limit):
                writer.writerow(cam)
                count += 1
        return count
