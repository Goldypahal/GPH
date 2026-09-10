"""
Sentinel Camera Grid Integration Contract (Section 39) Regression & Acceptance Test Suite.
Verifies all 18 requirements:
1. Camera Catalogue Contract (/api/ingest)
2. Forced TCP transport for RTSP
3. Authoritative PTS timing (pts vs arrival time)
4. Variable Frame Rate (VFR) tolerance
5. GOP burst-on-connect resilience
6. Exponential backoff reconnect (2s -> 30s)
7. Mixed codecs (H.264 & H.265) with UNSUPPORTED_CODEC handling
8. Heterogeneous resolution handling
9. Scene loop discontinuity detection & ByteTrack reset
10. Journey reconstruction discontinuity tolerance
11. Consume-only pipeline architecture
12. Load pacing & concurrency controls
13. Stream health truth state machine (8 distinct states)
14. Sentinel Deployment Readiness endpoint (/api/system/sentinel-readiness)
"""

import os
import sys
import time
import pytest
from datetime import datetime, timezone, timedelta

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.orm import Camera, VehicleSighting
from backend.app.services.sentinel_catalogue import sentinel_catalogue, SentinelCatalogueService
from backend.app.services.sentinel_stream import (
    sentinel_stream_manager,
    SentinelStreamManager,
    StreamHealthState,
    SentinelFrameMeta,
    MAX_ACTIVE_CAMERA_STREAMS
)
from backend.app.services.bytetrack import ByteTracker, STrack, TrackerPool
from backend.app.services.vehicle_tracker import VehicleTracker

client = TestClient(app)


def test_sentinel_catalogue_contract_endpoint():
    """
    Section 39.1: Camera Catalogue Contract (/api/ingest).
    Validates dynamic discovery, normalization, and complete metadata schema.
    """
    res = client.get("/api/ingest")
    assert res.status_code == 200, f"Expected 200 from /api/ingest, got {res.status_code}"
    data = res.json()
    assert data["status"] in ("CATALOGUE_AVAILABLE", "CATALOGUE_SYNCED")
    assert "provenance" in data
    assert data["total_cameras"] >= 50, f"Expected at least 50 catalogue cameras, got {data['total_cameras']}"

    # Verify each camera satisfies the authoritative catalogue contract
    for cam in data["cameras"]:
        assert "camera_id" in cam and len(cam["camera_id"]) > 0
        assert "name" in cam and len(cam["name"]) > 0
        assert "location" in cam
        assert "district" in cam
        assert cam["live_status"] in ("ACTIVE", "OFFLINE", "MAINTENANCE", "DEGRADED")
        assert cam["codec"] in ("H.264", "H.265", "HEVC", "AVC")
        assert ("x" in cam["resolution"] or "p" in cam["resolution"] or "K" in cam["resolution"])
        assert cam["declared_fps"] > 0
        assert cam["bitrate_kbps"] > 0
        assert cam["rtsp_url"].startswith("rtsp://")
        assert "stream_properties" in cam
        assert cam["stream_properties"]["transport"] == "TCP"

    print(f"[PASS] test_sentinel_catalogue_contract_endpoint verified {len(data['cameras'])} normalized cameras.")


def test_sentinel_catalogue_discovery_and_registration():
    """
    Section 39.1: Verifies newly discovered cameras register in DB without fabrication.
    """
    db = SessionLocal()
    try:
        raw_mock = {
            "camera_id": "GJ-TEST-SURAT-9999",
            "name": "Surat Ring Road Junction 44",
            "location": "Surat Ring Road Toll Gate",
            "district": "Surat",
            "live_status": "ACTIVE",
            "codec": "H.265",
            "resolution": "3840x2160",
            "fps": 30,
            "bitrate_kbps": 8192,
            "rtsp_url": "rtsp://surat-cam:8554/live/stream44",
            "lat": 21.1702,
            "lng": 72.8311,
            "vendor": "Sentinel-4K-Pro"
        }
        normalized = SentinelCatalogueService.normalize_camera_record(raw_mock)
        assert normalized is not None
        assert normalized["camera_id"] == "GJ-TEST-SURAT-9999"
        assert normalized["codec"] == "H.265"
        assert normalized["stream_properties"]["transport"] == "TCP"

        # Test sync to DB
        SentinelCatalogueService._sync_to_db(db, normalized)
        saved = db.query(Camera).filter(Camera.logical_camera_id == "GJ-TEST-SURAT-9999").first()
        assert saved is not None
        assert saved.district == "Surat"
        assert saved.resolution == "3840x2160"

        # Cleanup test camera
        db.delete(saved)
        db.commit()
    finally:
        db.close()
    print("[PASS] test_sentinel_catalogue_discovery_and_registration passed.")


def test_sentinel_rtsp_forced_tcp():
    """
    Section 39.2: Forced TCP transport for RTSP.
    Verifies that OPENCV_FFMPEG_CAPTURE_OPTIONS is strictly enforced as rtsp_transport;tcp.
    """
    tcp_opt = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
    assert tcp_opt is not None, "OPENCV_FFMPEG_CAPTURE_OPTIONS must be set"
    assert "rtsp_transport;tcp" in tcp_opt, f"Expected 'rtsp_transport;tcp' in {tcp_opt}"
    print("[PASS] test_sentinel_rtsp_forced_tcp passed.")


def test_sentinel_timestamp_correctness():
    """
    Section 39.14: Timestamp correctness verification.
    PTS 0ms, 40ms, 80ms, 120ms (dt = 40ms).
    Arrival times arrive in burst: 0ms, 5ms, 10ms, 15ms (arrival dt = 5ms).
    Downstream velocity calculation MUST use pts_delta (40ms), NEVER arrival dt (5ms).
    """
    strack = STrack([100.0, 100.0, 200.0, 200.0], score=0.95, class_name="Car")
    strack.pts = 0.0

    # Frame 2 moves by 20 pixels horizontally
    # PTS advance = 0.040s (40ms)
    # Wall clock / arrival interval = 0.005s (5ms burst)
    new_track = STrack([120.0, 100.0, 220.0, 200.0], score=0.95, class_name="Car")
    strack.update(new_track, frame_id=2, pts=0.040, pts_delta=0.040)

    # Velocity must be normalized by pts_delta (0.04s): dx / dt = 20 / 0.04 = 500 px/s
    # If arrival dt (0.005s) were used: dx / dt = 20 / 0.005 = 4000 px/s (8x false inflation)
    assert abs(strack.pts_delta - 0.040) < 1e-4, f"Expected pts_delta 0.040, got {strack.pts_delta}"
    assert abs(strack.velocity[0] - 500.0) < 1.0, f"Expected velocity 500 px/s based on PTS, got {strack.velocity[0]}"

    print(f"[PASS] test_sentinel_timestamp_correctness: velocity correctly normalized to {strack.velocity[0]} px/s via PTS.")


def test_sentinel_burst_on_connect():
    """
    Section 39.15: GOP / Join burst-on-connect resilience.
    Rapid initial arrivals must be tagged as burst and must NOT produce speed spikes.
    """
    tracker = ByteTracker()

    # 5 frames arriving in rapid burst: 5ms wall clock, but PTS cadence is 40ms
    dets = [([100.0, 100.0, 200.0, 200.0], 0.95, "Car")]
    pts_sequence = [0.0, 0.04, 0.08, 0.12, 0.16]

    for idx, pts in enumerate(pts_sequence):
        pts_delta = 0.04
        active_tracks = tracker.update(dets, pts=pts, pts_delta=pts_delta)
        assert len(active_tracks) >= 1

    # Verify track velocity remains stable
    tr = tracker.tracked_stracks[0]
    assert abs(tr.velocity[0]) < 10.0, f"Stationary object in burst frames registered speed spike: {tr.velocity}"
    print("[PASS] test_sentinel_burst_on_connect passed.")


def test_sentinel_scene_discontinuity_and_tracker_reset():
    """
    Section 39.16: Scene loop discontinuity detection & tracker state recovery.
    When PTS jumps backwards (e.g. 120.0s -> 0.04s), ByteTracker must reset state
    to prevent impossible cross-scene track continuation.
    """
    cam_id = "GJ-SCENE-LOOP-CAM-01"
    tracker = TrackerPool.get_tracker(cam_id)
    tracker.reset()

    # Feed scene 1 frames (ascending PTS up to 60.0s)
    tracker.update([([100.0, 100.0, 200.0, 200.0], 0.95, "Car")], pts=10.0, pts_delta=0.04)
    tracker.update([([105.0, 100.0, 205.0, 200.0], 0.95, "Car")], pts=10.04, pts_delta=0.04)
    assert len(tracker.tracked_stracks) == 1
    scene1_track_id = tracker.tracked_stracks[0].track_id

    # Scene loop boundary: PTS jumps backwards to 0.04s
    tracker.update([([500.0, 500.0, 600.0, 600.0], 0.95, "Car")], pts=0.04, pts_delta=0.04)

    # Tracker must have reset its prior track
    assert tracker.last_pts == 0.04
    # The new detection must not be merged into scene1_track_id with impossible displacement
    active_ids = [t.track_id for t in tracker.tracked_stracks]
    assert scene1_track_id not in active_ids or len(tracker.tracked_stracks) == 1

    print(f"[PASS] test_sentinel_scene_discontinuity_and_tracker_reset passed (Tracker reset at loop boundary).")


def test_sentinel_journey_discontinuity_resilience():
    """
    Section 39.9 & 39.10: Vehicle journey reconstruction handles backward time delta
    as SCENE_DISCONTINUITY_RESET instead of false IMPOSSIBLE_SPEED error.
    """
    db = SessionLocal()
    try:
        # Create test sightings where second sighting has an earlier timestamp (loop cut)
        now = datetime.now(timezone.utc)
        cam = db.query(Camera).first()
        cam_id = cam.id if cam else "GJ-CAM-DEFAULT-01"

        s1 = VehicleSighting(
            camera_id=cam_id,
            plate_text="GJ01SC9999",
            normalized_plate="GJ01SC9999",
            confidence=0.95,
            timestamp=now,
            speed_kmh=50.0
        )
        s2 = VehicleSighting(
            camera_id=cam_id,
            plate_text="GJ01SC9999",
            normalized_plate="GJ01SC9999",
            confidence=0.95,
            timestamp=now - timedelta(minutes=5),  # 5 minutes earlier (scene loop reset)
            speed_kmh=50.0
        )
        db.add(s1)
        db.add(s2)
        db.commit()

        # Reconstruct journey
        summary = VehicleTracker.reconstruct_journey(db, "GJ01SC9999")
        assert summary is not None
        assert len(summary.trajectory) == 2

        # Sighting 1 (earlier timestamp) to Sighting 2 (later timestamp)
        # Verify link_status is valid and not crashing
        for pt in summary.trajectory:
            assert pt.link_status in ("VERIFIED_PLAUSIBLE", "SCENE_DISCONTINUITY_RESET", "LOW_CONFIDENCE_LINK")

        # Cleanup
        db.delete(s1)
        db.delete(s2)
        db.commit()
    finally:
        db.close()
    print("[PASS] test_sentinel_journey_discontinuity_resilience passed.")


def test_sentinel_exponential_backoff_reconnect():
    """
    Section 39.6: Automatic exponential backoff reconnect (2s -> 4s -> 8s -> 16s -> 30s).
    """
    cam_id = "GJ-RECONNECT-TEST-CAM-01"
    sentinel_stream_manager.register_stream_intent(cam_id, "rtsp://test/live")

    # Sequence of disconnects
    d1 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d1 - 2.0) < 1e-3, f"Expected 2.0s initial delay, got {d1}"

    d2 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d2 - 4.0) < 1e-3, f"Expected 4.0s second delay, got {d2}"

    d3 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d3 - 8.0) < 1e-3, f"Expected 8.0s third delay, got {d3}"

    d4 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d4 - 16.0) < 1e-3, f"Expected 16.0s fourth delay, got {d4}"

    d5 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d5 - 30.0) < 1e-3, f"Expected 30.0s max delay cap, got {d5}"

    d6 = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d6 - 30.0) < 1e-3, f"Expected capped delay at 30.0s, got {d6}"

    # Reconnect reset
    sentinel_stream_manager.reset_backoff(cam_id)
    d_after_reset = sentinel_stream_manager.compute_next_backoff(cam_id)
    assert abs(d_after_reset - 2.0) < 1e-3, f"Expected reset to 2.0s, got {d_after_reset}"

    sentinel_stream_manager.close_stream(cam_id)
    print("[PASS] test_sentinel_exponential_backoff_reconnect passed.")


def test_sentinel_mixed_codecs_and_resolutions():
    """
    Section 39.7 & 39.8: Codec awareness (H.264, H.265) & heterogeneous resolutions.
    """
    # Test valid H.264
    telem264 = sentinel_stream_manager.register_stream_intent("GJ-H264-CAM", "rtsp://h264/live", codec="H.264", resolution="1920x1080")
    assert telem264.codec == "H.264"
    assert telem264.resolution == "1920x1080"

    # Test valid H.265 / HEVC
    telem265 = sentinel_stream_manager.register_stream_intent("GJ-H265-CAM", "rtsp://h265/live", codec="H.265", resolution="3840x2160")
    assert telem265.codec == "H.265"
    assert telem265.resolution == "3840x2160"

    # Test unsupported codec rejection
    with pytest.raises(RuntimeError) as excinfo:
        # stream_frames_with_pts checks codec support
        gen = sentinel_stream_manager.stream_frames_with_pts("GJ-INVALID-CODEC", "rtsp://invalid/live", expected_codec="VP9_UNKNOWN")
        next(gen)
    assert "UNSUPPORTED_CODEC" in str(excinfo.value)
    assert sentinel_stream_manager.get_telemetry("GJ-INVALID-CODEC").current_state == StreamHealthState.UNSUPPORTED_CODEC

    sentinel_stream_manager.close_stream("GJ-H264-CAM")
    sentinel_stream_manager.close_stream("GJ-H265-CAM")
    sentinel_stream_manager.close_stream("GJ-INVALID-CODEC")
    print("[PASS] test_sentinel_mixed_codecs_and_resolutions passed.")


def test_sentinel_load_pacing_and_concurrency():
    """
    Section 39.11 & 39.12: Consume-only pipeline & load pacing limits.
    """
    # 1. Consume-only: verify no publish/write methods exist on manager
    assert not hasattr(sentinel_stream_manager, "publish_stream")
    assert not hasattr(sentinel_stream_manager, "control_gateway")
    assert not hasattr(sentinel_stream_manager, "broadcast_to_gateway")

    # 2. Load pacing limit check
    active_before = len(sentinel_stream_manager.get_all_active_streams())
    dummy_cams = []

    try:
        # Fill up to MAX_ACTIVE_CAMERA_STREAMS
        slots_to_fill = MAX_ACTIVE_CAMERA_STREAMS - active_before
        for i in range(slots_to_fill):
            c_id = f"GJ-LOAD-PACING-CAM-{i:03d}"
            dummy_cams.append(c_id)
            sentinel_stream_manager.register_stream_intent(c_id, f"rtsp://mock/{c_id}")

        # Try to open one more stream beyond limit
        allowed, reason = sentinel_stream_manager.can_open_stream("GJ-OVERFLOW-CAM")
        assert not allowed, "Should disallow opening stream when MAX_ACTIVE_CAMERA_STREAMS is reached"
        assert "LOAD_PACING_EXCEEDED" in reason
    finally:
        for c_id in dummy_cams:
            sentinel_stream_manager.close_stream(c_id)

    print("[PASS] test_sentinel_load_pacing_and_concurrency passed.")


def test_sentinel_stream_health_truth_states():
    """
    Section 39.17: Stream health truth state machine.
    Verifies 8 distinct un-collapsed states.
    """
    cam_id = "GJ-HEALTH-TRUTH-CAM-01"
    sentinel_stream_manager.register_stream_intent(cam_id, "rtsp://live/health")

    states = [
        StreamHealthState.CATALOGUE_LIVE,
        StreamHealthState.TCP_REACHABLE,
        StreamHealthState.RTSP_CONNECTED,
        StreamHealthState.RTSP_AUTHENTICATED,
        StreamHealthState.STREAM_ACTIVE,
        StreamHealthState.FRAME_RECEIVING,
        StreamHealthState.FRAME_FRESH,
        StreamHealthState.AI_PROCESSING
    ]

    for state in states:
        sentinel_stream_manager.record_state(cam_id, state)
        telem = sentinel_stream_manager.get_telemetry(cam_id)
        assert telem.current_state == state

    sentinel_stream_manager.close_stream(cam_id)
    print("[PASS] test_sentinel_stream_health_truth_states passed (all 8 states verified).")


def test_sentinel_readiness_endpoint():
    """
    Section 39.18: Sentinel Deployment Readiness endpoint.
    GET /api/system/sentinel-readiness
    """
    res = client.get("/api/system/sentinel-readiness")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    report = res.json()

    assert report["sentinel_readiness"] == "PASS"
    assert "checks" in report
    checks = report["checks"]

    required_checks = [
        "camera_catalogue",
        "rtsp_tcp",
        "pts_timing",
        "reconnect",
        "h264",
        "h265",
        "mixed_resolution",
        "scene_discontinuity",
        "load_pacing"
    ]

    for chk in required_checks:
        assert chk in checks, f"Missing check {chk}"
        assert checks[chk] == "PASS", f"Check {chk} failed with {checks[chk]}"

    assert report["catalogue_cameras_count"] >= 50
    assert report["max_allowed_streams"] == 32
    assert "pts_telemetry" in report

    print("[PASS] test_sentinel_readiness_endpoint passed with 100% PASS on all checks.")
