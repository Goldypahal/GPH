#!/usr/bin/env python3
"""
Sentinel Camera Grid - RTSP Live Stream Viewer
Connects to physical/virtual operational camera endpoints at 103.250.160.189:8554
over TCP transport with authorized credentials.

Usage:
  python scripts/sentinel_live_viewer.py
  python scripts/sentinel_live_viewer.py --camera cam02
  python scripts/sentinel_live_viewer.py --camera cam15 --width 1920 --height 1080
"""

import os
import sys
import time
import argparse
from urllib.parse import quote
import cv2

# Force RTSP over TCP transport for firewall/NAT traversal & reliability
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

DEFAULT_EMAIL = "goldypahal06@gmail.com"
DEFAULT_PASSWORD = "PBL8-NRGG-BN8J"
DEFAULT_SERVER = "103.250.160.189:8554"
DEFAULT_CAMERA = "cam01"


def parse_args():
    parser = argparse.ArgumentParser(description="Sentinel Camera Grid - RTSP Live Viewer")
    parser.add_argument(
        "--camera", "-c",
        default=DEFAULT_CAMERA,
        help="Camera ID to stream (e.g. cam01 through cam30). Default: cam01"
    )
    parser.add_argument(
        "--email", "-e",
        default=DEFAULT_EMAIL,
        help=f"Registered access email. Default: {DEFAULT_EMAIL}"
    )
    parser.add_argument(
        "--password", "-p",
        default=DEFAULT_PASSWORD,
        help="Access password / passkey. Default: PBL8-NRGG-BN8J"
    )
    parser.add_argument(
        "--server", "-s",
        default=DEFAULT_SERVER,
        help=f"Gateway host:port. Default: {DEFAULT_SERVER}"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Viewer window display width in pixels. Default: 1280"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Viewer window display height in pixels. Default: 720"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    email_encoded = quote(args.email, safe="")
    password_encoded = quote(args.password, safe="")
    rtsp_url = f"rtsp://{email_encoded}:{password_encoded}@{args.server}/stream/{args.camera}"

    # Sanitized URL for console output (hide password)
    safe_url = f"rtsp://{email_encoded}:***@{args.server}/stream/{args.camera}"

    print("=" * 65)
    print("  SENTINEL CAMERA GRID — RTSP LIVE VIEWER")
    print("=" * 65)
    print(f"  Target Camera   : {args.camera}")
    print(f"  Gateway Host    : {args.server}")
    print(f"  Authorized User : {args.email}")
    print(f"  RTSP URL        : {safe_url}")
    print(f"  Transport       : TCP (Forced)")
    print("=" * 65)
    print("Connecting to live camera stream...")

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("\n[ERROR] Could not open RTSP camera stream.")
        print("  - Check whether port 8554/TCP outbound is allowed on your network.")
        print("  - Verify that the camera ID is active on the gateway (cam01 - cam30).")
        print("  - Confirm access credentials.")
        sys.exit(1)

    print("[SUCCESS] Stream connected!")
    print("Waiting for initial video frames...")

    window_name = f"Sentinel Camera Grid — {args.camera} ({args.server})"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, args.width, args.height)

    frame_count = 0
    start_time = time.time()
    last_stat_time = time.time()
    frames_since_stat = 0

    try:
        while True:
            ok, frame = cap.read()

            if not ok or frame is None:
                print("\n[WARNING] Frame could not be read. Stream interrupted or buffering...")
                # Allow a brief pause for reconnect buffer
                time.sleep(0.05)
                continue

            frame_count += 1
            frames_since_stat += 1

            # Telemetry readout every 30 frames
            if frame_count % 30 == 0:
                now = time.time()
                elapsed = now - last_stat_time
                fps = frames_since_stat / max(0.001, elapsed)
                last_stat_time = now
                frames_since_stat = 0
                h, w = frame.shape[:2]
                print(f"  [STREAMING] Native: {w}x{h} | Rate: {fps:.1f} FPS | Total Frames: {frame_count}")

            # Display live frame
            cv2.imshow(window_name, frame)

            # Check for quit key ('q' or ESC)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                print("\nUser requested shutdown. Stopping stream...")
                break

            # Check if user closed the window directly
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("\nWindow closed. Stopping stream...")
                break

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        total_time = time.time() - start_time
        print("=" * 65)
        print(f"Session ended. Displayed {frame_count} frames in {total_time:.1f} seconds.")
        print("Camera disconnected successfully.")
        print("=" * 65)


if __name__ == "__main__":
    main()
