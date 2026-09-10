import io
import os
import time
import math
from typing import Generator
from PIL import Image, ImageDraw

class FeedConnector:
    """Vendor-neutral stream gateway.

    RTSP/HTTP ingestion is used for real cameras. Synthetic frames are only
    available when GIVIN_STREAM_MODE=simulation, keeping demo mode explicit.
    """

    @staticmethod
    def generate_live_frame(camera_id: str, camera_name: str, district: str, frame_idx: int = 0) -> bytes:
        width, height = 640, 360
        img = Image.new("RGB", (width, height), color=(18, 24, 38))
        draw = ImageDraw.Draw(img)
        draw.polygon([(0, 360), (width, 360), (400, 180), (240, 180)], fill=(35, 42, 58))
        for y in range(190, 360, 30):
            draw.line([(width // 2, y), (width // 2, y + 15)], fill=(220, 220, 100), width=3)
        cycle = (frame_idx * 6) % (width + 200) - 100
        veh_x = cycle
        veh_y = 200 + int(30 * math.sin(frame_idx * 0.1))
        if -100 <= veh_x <= width + 50:
            draw.rectangle([veh_x, veh_y, veh_x+160, veh_y+90], fill=(180,30,40), outline=(240,50,60), width=2)
            draw.rectangle([veh_x-8, veh_y-8, veh_x+168, veh_y+98], outline=(0,255,128), width=2)
            draw.text((veh_x, veh_y-24), "Car: SUV [ID #4821] 94.2%", fill=(0,255,128))
            plate_x, plate_y = veh_x+35, veh_y+68
            draw.rectangle([plate_x, plate_y, plate_x+90, plate_y+20], fill=(255,255,255), outline=(0,0,0))
            draw.text((plate_x+5, plate_y+3), "GJ 01 AB 1234", fill=(0,0,0))
        draw.rectangle([0,0,width,28], fill=(10,14,23))
        draw.text((10,7), f"GIVIN C4I // CAM: {camera_name[:25]} [{district}]", fill=(14,165,233))
        draw.text((width-190,7), time.strftime("%Y-%m-%d %H:%M:%S UTC"), fill=(245,158,11))
        draw.rectangle([10,height-30,180,height-10], fill=(0,0,0))
        draw.text((15,height-26), "SIMULATION // 12 FPS", fill=(239,68,68))
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=80); return buf.getvalue()

    @classmethod
    def _rtsp_generator(cls, camera_id: str, url: str) -> Generator[bytes, None, None]:
        from backend.app.services.sentinel_stream import sentinel_stream_manager
        for frame_meta in sentinel_stream_manager.stream_frames_with_pts(camera_id, url):
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_meta.frame_bytes + b"\r\n"

    @classmethod
    def get_stream_generator(cls, camera_id: str, camera_name: str, district: str, stream_url: str | None = None) -> Generator[bytes, None, None]:
        mode = os.getenv("GIVIN_STREAM_MODE", "real").lower()
        if mode != "simulation" and stream_url and stream_url.startswith(("rtsp://", "rtsps://", "http://", "https://")):
            yield from cls._rtsp_generator(camera_id, stream_url)
            return
        if mode != "simulation":
            raise RuntimeError("No supported camera stream URL configured; use GIVIN_STREAM_MODE=simulation only for demo feeds")
        frame_idx = 0
        while True:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + cls.generate_live_frame(camera_id, camera_name, district, frame_idx) + b"\r\n"
            frame_idx += 1
            time.sleep(0.08)
