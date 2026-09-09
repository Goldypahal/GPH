import io
import time
import math
from typing import Generator
from PIL import Image, ImageDraw, ImageFont

class FeedConnector:
    """
    Heterogeneous Feed Ingestion and Stream Normalization Gateway (Model 3).
    Supports RTSP, ONVIF, HTTP-FLV, MP4 files, and Synthetic Live Inference Streams.
    """

    @staticmethod
    def generate_live_frame(
        camera_id: str,
        camera_name: str,
        district: str,
        frame_idx: int = 0
    ) -> bytes:
        """
        Generates a synthetic high-definition video frame with real-time AI computer vision overlays:
        - Highway / Urban road background
        - Moving vehicle bounding boxes
        - Tracking IDs & Vehicle classification
        - ANPR License Plate banners with confidence scores
        - Camera telemetry HUD (Timestamp, Lat/Long, Vendor/Protocol)
        """
        width = 640
        height = 360
        img = Image.new("RGB", (width, height), color=(18, 24, 38))
        draw = ImageDraw.Draw(img)

        # Draw road perspective
        draw.polygon([(0, 360), (width, 360), (400, 180), (240, 180)], fill=(35, 42, 58))
        # Draw road dashed center line
        for y in range(190, 360, 30):
            draw.line([(width // 2, y), (width // 2, y + 15)], fill=(220, 220, 100), width=3)

        # Animated vehicle position
        cycle = (frame_idx * 6) % (width + 200) - 100
        veh_x = cycle
        veh_y = 200 + int(30 * math.sin(frame_idx * 0.1))
        veh_w = 160
        veh_h = 90

        if -100 <= veh_x <= width + 50:
            # Draw vehicle body (Sedan/SUV)
            draw.rectangle([veh_x, veh_y, veh_x + veh_w, veh_y + veh_h], fill=(180, 30, 40), outline=(240, 50, 60), width=2)
            # Windshield
            draw.polygon([(veh_x + 30, veh_y + 15), (veh_x + 130, veh_y + 15), (veh_x + 110, veh_y + 40), (veh_x + 40, veh_y + 40)], fill=(80, 120, 160))

            # AI Bounding Box (Neon Cyber Green)
            bbox_pad = 8
            bx1, by1 = veh_x - bbox_pad, veh_y - bbox_pad
            bx2, by2 = veh_x + veh_w + bbox_pad, veh_y + veh_h + bbox_pad
            draw.rectangle([bx1, by1, bx2, by2], outline=(0, 255, 128), width=2)

            # AI Classification Tag
            tag_text = f"Car: SUV [ID #4821] 94.2%"
            draw.rectangle([bx1, by1 - 18, bx1 + 175, by1], fill=(0, 200, 100))
            draw.text((bx1 + 4, by1 - 16), tag_text, fill=(0, 0, 0))

            # ANPR Plate Detection Box & Label
            plate_x = veh_x + (veh_w // 2) - 45
            plate_y = veh_y + veh_h - 22
            draw.rectangle([plate_x, plate_y, plate_x + 90, plate_y + 20], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
            draw.text((plate_x + 5, plate_y + 3), "GJ 01 AB 1234", fill=(0, 0, 0))

            # ANPR High-Confidence Badge
            draw.rectangle([plate_x - 5, plate_y - 14, plate_x + 95, plate_y], fill=(14, 165, 233))
            draw.text((plate_x, plate_y - 13), "ANPR: 96.8% MATCH", fill=(255, 255, 255))

        # Command Center Telemetry HUD Overlays
        # Top HUD bar
        draw.rectangle([0, 0, width, 28], fill=(10, 14, 23))
        hud_left = f"GIVIN C4I // CAM: {camera_name[:25]} [{district}]"
        draw.text((10, 7), hud_left, fill=(14, 165, 233))

        curr_time = time.strftime("%Y-%m-%d %H:%M:%S UTC")
        draw.text((width - 190, 7), curr_time, fill=(245, 158, 11))

        # Live Watermark & FPS
        draw.rectangle([10, height - 30, 180, height - 10], fill=(0, 0, 0))
        draw.text((15, height - 26), f"REC ● 25.0 FPS | 1080p RTSP", fill=(239, 68, 68))

        # Output to JPEG buffer
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()

    @classmethod
    def get_stream_generator(
        cls,
        camera_id: str,
        camera_name: str,
        district: str
    ) -> Generator[bytes, None, None]:
        """Streams MJPEG frames for real-time video wall monitoring."""
        frame_idx = 0
        while True:
            frame_bytes = cls.generate_live_frame(camera_id, camera_name, district, frame_idx)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            frame_idx += 1
            time.sleep(0.08)  # ~12 FPS simulated live stream
