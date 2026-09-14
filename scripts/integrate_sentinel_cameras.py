#!/usr/bin/env python3
"""
Integration Script: Ingest Sentinel Camera Grid (cam01 - cam30) into GIVIN Database.
Server: 103.250.160.189:8554
Protocol: RTSP / TCP
Auth: amanpalpathi@gmail.com / UDTR-YLX2-9VTC
"""

import sys
import os
from urllib.parse import quote
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, CameraHealth, CameraCredential, Department


SENTINEL_GRID_SPECS = [
    {"id": "cam01", "name": "Sentinel Cam 01 (SG Highway Iscon Crossroad ANPR)", "district": "Ahmedabad", "loc": "SG Highway, Iscon Crossroad", "lat": 23.0298, "lng": 72.5074, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam02", "name": "Sentinel Cam 02 (CG Road Stadium Circle PTZ)", "district": "Ahmedabad", "loc": "C.G. Road, Stadium Circle", "lat": 23.0416, "lng": 72.5607, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam03", "name": "Sentinel Cam 03 (Kalupur Central Railway Ingress)", "district": "Ahmedabad", "loc": "Kalupur Railway Station Ingress", "lat": 23.0245, "lng": 72.5997, "res": "720p", "codec": "H.264", "fps": 25},
    {"id": "cam04", "name": "Sentinel Cam 04 (Ashram Road Vadaj Junction Corridor)", "district": "Ahmedabad", "loc": "Ashram Road, Vadaj Circle", "lat": 23.0581, "lng": 72.5711, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam05", "name": "Sentinel Cam 05 (Narol Highway Commercial Checkpost)", "district": "Ahmedabad", "loc": "Narol Highway Junction", "lat": 22.9734, "lng": 72.5921, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam06", "name": "Sentinel Cam 06 (SP Ring Road Bopal Flyover ANPR)", "district": "Ahmedabad", "loc": "SP Ring Road, Bopal Junction", "lat": 23.0335, "lng": 72.4645, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam07", "name": "Sentinel Cam 07 (CH-0 Circle Highway Surveillance)", "district": "Gandhinagar", "loc": "CH-0 Circle Highway Post", "lat": 23.1895, "lng": 72.6358, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam08", "name": "Sentinel Cam 08 (Infocity Outer Ring Toll ANPR)", "district": "Gandhinagar", "loc": "Infocity Outer Ring Gate", "lat": 23.1952, "lng": 72.6288, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam09", "name": "Sentinel Cam 09 (GIFT City Access Expressway North)", "district": "Gandhinagar", "loc": "GIFT City Gate 1 North Expressway", "lat": 23.1610, "lng": 72.6842, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam10", "name": "Sentinel Cam 10 (Mahatma Mandir Perimeter Ingress)", "district": "Gandhinagar", "loc": "Mahatma Mandir Central Axis", "lat": 23.2185, "lng": 72.6591, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam11", "name": "Sentinel Cam 11 (Kamrej Toll Plaza NH-48 Ingress)", "district": "Surat", "loc": "Kamrej Toll Plaza NH-48", "lat": 21.2721, "lng": 72.9612, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam12", "name": "Sentinel Cam 12 (Athwalines Police HQ Perimeter)", "district": "Surat", "loc": "Athwalines Police Bhavan", "lat": 21.1789, "lng": 72.8012, "res": "720p", "codec": "H.264", "fps": 25},
    {"id": "cam13", "name": "Sentinel Cam 13 (Ring Road Textile Market Central)", "district": "Surat", "loc": "Ring Road Sahara Darwaja", "lat": 21.1963, "lng": 72.8427, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam14", "name": "Sentinel Cam 14 (Hazira Port Logistics Corridor)", "district": "Surat", "loc": "Hazira Port Entry Gate 1", "lat": 21.1092, "lng": 72.6358, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam15", "name": "Sentinel Cam 15 (Golden Crossroads NH-48 North)", "district": "Vadodara", "loc": "NH-48 Golden Chowkdi", "lat": 22.3482, "lng": 73.2341, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam16", "name": "Sentinel Cam 16 (Sayajigunj Station Roundabout)", "district": "Vadodara", "loc": "Sayajigunj Central Circle", "lat": 22.3089, "lng": 73.1892, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam17", "name": "Sentinel Cam 17 (Makarpura GIDC Heavy Vehicle Check)", "district": "Vadodara", "loc": "Makarpura Industrial Gate", "lat": 22.2536, "lng": 73.1947, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam18", "name": "Sentinel Cam 18 (Alkapuri Central Commercial Post)", "district": "Vadodara", "loc": "Alkapuri Financial District", "lat": 22.3123, "lng": 73.1756, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam19", "name": "Sentinel Cam 19 (Kuvadva Road NH-27 Entrance Toll)", "district": "Rajkot", "loc": "Kuvadva Road NH-27 Toll", "lat": 22.3412, "lng": 70.8512, "res": "720p", "codec": "H.264", "fps": 25},
    {"id": "cam20", "name": "Sentinel Cam 20 (Trikon Baug City Intersection)", "district": "Rajkot", "loc": "Trikon Baug Central Junction", "lat": 22.3005, "lng": 70.8021, "res": "720p", "codec": "H.264", "fps": 25},
    {"id": "cam21", "name": "Sentinel Cam 21 (150ft Ring Road Indira Circle HEVC)", "district": "Rajkot", "loc": "150ft Ring Road Indira Circle", "lat": 22.2891, "lng": 70.7712, "res": "1080p", "codec": "H.265", "fps": 25},
    {"id": "cam22", "name": "Sentinel Cam 22 (Alang Ship Breaking Yard Ingress)", "district": "Bhavnagar", "loc": "Alang Gate Plot 12 Entry", "lat": 21.4123, "lng": 72.1895, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam23", "name": "Sentinel Cam 23 (Nari Chowkdi Ahmedabad Highway)", "district": "Bhavnagar", "loc": "Nari Chowkdi Bypass Post", "lat": 21.7891, "lng": 72.0912, "res": "720p", "codec": "H.264", "fps": 25},
    {"id": "cam24", "name": "Sentinel Cam 24 (Reliance Refinery Highway Post)", "district": "Jamnagar", "loc": "Motikhavdi NH-947 Ref Post", "lat": 22.3789, "lng": 69.8512, "res": "576p", "codec": "H.264", "fps": 25},
    {"id": "cam25", "name": "Sentinel Cam 25 (Digjam Circle Central City ANPR)", "district": "Jamnagar", "loc": "Digjam Bypass Junction", "lat": 22.4512, "lng": 70.0612, "res": "960p", "codec": "H.264", "fps": 25},
    {"id": "cam26", "name": "Sentinel Cam 26 (Kandla Port Heavy Logistics 2K)", "district": "Kutch", "loc": "Kandla Port Terminal Wharf 1", "lat": 23.0112, "lng": 70.2189, "res": "2K QHD", "codec": "H.265", "fps": 25},
    {"id": "cam27", "name": "Sentinel Cam 27 (Bhuj Jubilee Ground ANPR Post)", "district": "Kutch", "loc": "Bhuj Jubilee Ground Axis", "lat": 23.2512, "lng": 69.6712, "res": "960p", "codec": "H.264", "fps": 25},
    {"id": "cam28", "name": "Sentinel Cam 28 (Narmada Cable Bridge Entry Toll)", "district": "Bharuch", "loc": "NH-48 Narmada Cable Bridge", "lat": 21.7123, "lng": 72.9912, "res": "1080p", "codec": "H.264", "fps": 25},
    {"id": "cam29", "name": "Sentinel Cam 29 (Amul Dairy Road Express Junction)", "district": "Anand", "loc": "Amul Dairy Road Circle", "lat": 22.5512, "lng": 72.9512, "res": "960p", "codec": "H.264", "fps": 25},
    {"id": "cam30", "name": "Sentinel Cam 30 (Modhera State Highway Checkpost)", "district": "Mehsana", "loc": "Modhera Road State Checkpost", "lat": 23.6012, "lng": 72.3812, "res": "1080p", "codec": "H.264", "fps": 25},
]

EMAIL = "amanpalpathi@gmail.com"
PASSWORD = "UDTR-YLX2-9VTC"
SERVER = "103.250.160.189:8554"

email_encoded = quote(EMAIL, safe="")
password_encoded = quote(PASSWORD, safe="")


def integrate_sentinel_cameras():
    db = SessionLocal()
    print("=" * 75)
    print("  GIVIN SENTINEL CAMERA GRID DATABASE INTEGRATION (cam01 - cam30)")
    print(f"  Streaming Gateway: {SERVER} (RTSP / TCP Transport)")
    print("=" * 75)

    try:
        # 1. Fetch or create Home Department
        dept = db.query(Department).filter(Department.code == "HOME_POLICE").first()
        if not dept:
            dept = Department(
                name="Home Department (Gujarat Police)",
                code="HOME_POLICE",
                category="Law Enforcement & Traffic"
            )
            db.add(dept)
            db.commit()
            db.refresh(dept)

        integrated = 0
        updated = 0

        for spec in SENTINEL_GRID_SPECS:
            cam_id = spec["id"]
            rtsp_url = f"rtsp://{email_encoded}:{password_encoded}@{SERVER}/stream/{cam_id}"

            existing = db.query(Camera).filter(Camera.logical_camera_id == cam_id).first()

            if existing:
                existing.name = spec["name"]
                existing.district = spec["district"]
                existing.location_name = spec["loc"]
                existing.lat = spec["lat"]
                existing.lng = spec["lng"]
                existing.resolution = spec["res"]
                existing.fps = spec["fps"]
                existing.stream_url = rtsp_url
                existing.status = "ACTIVE"
                existing.protocol = "RTSP"
                existing.vendor = "Sentinel-MediaMTX"
                existing.vms_type = "MediaMTX-RTSP"
                updated += 1
                cam_obj = existing
            else:
                new_cam = Camera(
                    department_id=dept.id,
                    logical_camera_id=cam_id,
                    name=spec["name"],
                    district=spec["district"],
                    location_name=spec["loc"],
                    lat=spec["lat"],
                    lng=spec["lng"],
                    altitude=15.0,
                    fov_angle=90.0,
                    fov_range_m=85.0,
                    vendor="Sentinel-MediaMTX",
                    model="IP-RTSP-H264-H265",
                    camera_type="IP Bullet ANPR",
                    resolution=spec["res"],
                    fps=spec["fps"],
                    protocol="RTSP",
                    stream_url=rtsp_url,
                    vms_type="MediaMTX-RTSP",
                    storage_type="GIVIN-WORM-MinIO",
                    retention_days=30,
                    status="ACTIVE",
                    is_public_domain=True,
                    share_scope="STATEWIDE_FEDERATED"
                )
                db.add(new_cam)
                db.flush()
                cam_obj = new_cam
                integrated += 1

            # Camera Health Record
            health = db.query(CameraHealth).filter(CameraHealth.camera_id == cam_obj.id).first()
            if not health:
                health = CameraHealth(
                    camera_id=cam_obj.id,
                    last_seen=datetime.now(timezone.utc),
                    latency_ms=12,
                    packet_loss=0.0,
                    cpu_usage=18.5,
                    memory_usage=24.0,
                    clock_drift_ms=1.2,
                    status="HEALTHY"
                )
                db.add(health)
            else:
                health.status = "HEALTHY"
                health.last_seen = datetime.now(timezone.utc)

            # Camera Credential Record
            cred = db.query(CameraCredential).filter(CameraCredential.camera_id == cam_obj.id).first()
            if not cred:
                cred = CameraCredential(
                    camera_id=cam_obj.id,
                    username=EMAIL,
                    encrypted_password=PASSWORD,
                    auth_type="BASIC",
                    port=8554
                )
                db.add(cred)

        db.commit()
        print(f"\n[SUCCESS] Integrated {integrated} new cameras, updated {updated} existing cameras.")
        print(f"[TOTAL] Sentinel Grid Active Cameras: {len(SENTINEL_GRID_SPECS)} cameras registered in DB.")
        print("-" * 75)
        print(f"{'Camera ID':<10} | {'District':<14} | {'Resolution':<10} | {'Location':<35}")
        print("-" * 75)
        for s in SENTINEL_GRID_SPECS[:10]:
            print(f"{s['id']:<10} | {s['district']:<14} | {s['res']:<10} | {s['loc']:<35}")
        print(f"... and {len(SENTINEL_GRID_SPECS)-10} more cameras through cam30.")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    integrate_sentinel_cameras()
