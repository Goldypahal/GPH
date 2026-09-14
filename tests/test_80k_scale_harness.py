"""
Automated Test Suite for GIVIN 80,000 Virtual Camera Scale Validation Harness.
Verifies:
- 33-District Partitioning sums to exactly 80,000 cameras
- Camera & Sighting generators produce valid RTO schemas
- Connection pool session state machine and heartbeats
- Storage estimator exact mathematical compliance
- Scenarios (Mode 1, Mode 2, Mode 3, Mode 4, Mode 5) execute reliably
"""

import os
import pytest
from scale_testing.camera_profiles.district_fleet import GUJARAT_DISTRICTS_33, DISTRICT_CAMERA_DISTRIBUTION, TOTAL_STATEWIDE_CAMERAS
from scale_testing.generators.camera_generator import CameraGenerator
from scale_testing.generators.sighting_generator import SightingGenerator
from scale_testing.load_clients.connection_pool import VirtualCameraConnectionPool, CameraSessionState
from scale_testing.load_clients.stream_replayer import StreamReplayer
from scale_testing.metrics.storage_estimator import StorageEstimator
from scale_testing.scenarios.mode1_connection_stress import run_mode1_connection_stress
from scale_testing.scenarios.mode2_metadata_throughput import run_mode2_metadata_throughput
from scale_testing.scenarios.mode3_frame_replay import run_mode3_frame_replay
from scale_testing.scenarios.mode4_mixed_inference import run_mode4_mixed_inference
from scale_testing.scenarios.mode5_failure_recovery import run_mode5_failure_recovery


def test_district_distribution_sums_to_80k():
    """Verify that all 33 Gujarat districts sum to exactly 80,000 cameras."""
    assert len(GUJARAT_DISTRICTS_33) == 33
    total_cams = sum(d["cameras"] for d in GUJARAT_DISTRICTS_33)
    assert total_cams == 80000

    top4_sum = (
        DISTRICT_CAMERA_DISTRIBUTION["Ahmedabad"] +
        DISTRICT_CAMERA_DISTRIBUTION["Surat"] +
        DISTRICT_CAMERA_DISTRIBUTION["Vadodara"] +
        DISTRICT_CAMERA_DISTRIBUTION["Rajkot"]
    )
    assert top4_sum == 24000
    rem_sum = total_cams - top4_sum
    assert rem_sum == 56000


def test_camera_generator_lazy_stream():
    """Verify CameraGenerator yields valid schema without memory bloat."""
    cams = list(CameraGenerator.iter_fleet(limit=250))
    assert len(cams) == 250
    first = cams[0]
    assert "camera_id" in first
    assert first["camera_id"].startswith("GJ-")
    assert "district" in first
    assert "gateway_subnet" in first
    assert first["resolution"] in CameraGenerator.RESOLUTIONS
    assert first["codec"] in CameraGenerator.CODECS


def test_sighting_generator_hsrp_format():
    """Verify SightingGenerator produces compliant Gujarat vehicle sighting events."""
    batch = SightingGenerator.generate_batch(batch_size=100, hotlist_rate=0.05)
    assert len(batch) == 100
    evt = batch[0]
    assert "event_id" in evt
    assert "plate_text" in evt
    assert "pts_timestamp_ms" in evt
    assert "confidence" in evt
    assert evt["confidence"] >= 0.80
    assert evt["provenance"] == "SIMULATION_SCALE_TEST"


def test_virtual_camera_connection_pool():
    """Verify connection pool state machine, heartbeats, and chaos drops."""
    pool = VirtualCameraConnectionPool(target_capacity=500)
    count = pool.initialize_fleet(count=500)
    assert count == 500

    # Heartbeat
    hb_res = pool.dispatch_heartbeats(sample_size=200)
    assert hb_res["accepted"] == 200
    assert hb_res["throughput_hps"] > 0

    # Drop 10%
    dropped = pool.simulate_offline_drop(percentage_cameras=0.10)
    assert dropped == 50
    health = pool.get_fleet_health_summary()
    assert health["offline_count"] == 50

    # Reconnect
    recon = pool.simulate_reconnection_storm(percentage_cameras=0.10)
    assert recon["reconnect_successful"] == 50


def test_storage_estimator_exact_formulas():
    """Verify storage calculations match mathematical formula."""
    # 80,000 * 1,000,000 * 86400 / 8 = 864,000,000,000,000 bytes
    daily_1mbps = StorageEstimator.calculate_daily_bytes(80000, 1.0)
    assert daily_1mbps == 864_000_000_000_000.0

    central = StorageEstimator.get_central_storage_model(80000)
    assert central["1_mbps_profile"]["daily_tb"] == 864.0
    assert central["2_mbps_profile"]["daily_tb"] == 1728.0
    assert central["4_mbps_profile_1080p"]["daily_tb"] == 3456.0
    assert central["4_mbps_profile_1080p"]["wan_bandwidth_gbps"] == 320.0

    hybrid = StorageEstimator.get_givin_hybrid_edge_model(80000)
    assert hybrid["bandwidth_reduction_pct"] > 95.0
    assert hybrid["storage_reduction_pct"] > 95.0


def test_mode1_connection_stress_scenario():
    """Verify Mode 1 connection scenario runs cleanly."""
    res = run_mode1_connection_stress(camera_count=100, rounds=1, sample_per_round=50)
    assert res["scenario"] == "MODE_1_CONNECTION_ONLY"
    assert res["fleet_initialized"] == 100
    assert res["verdict"] in ("PASSED", "DEGRADED")


def test_mode2_metadata_throughput_scenario():
    """Verify Mode 2 metadata burst scenario runs cleanly."""
    res = run_mode2_metadata_throughput(tiers=["normal"])
    assert res["scenario"] == "MODE_2_METADATA_AND_BURST_THROUGHPUT"
    assert "normal" in res["tier_benchmarks"]
    assert res["overall_throughput_eps"] > 0


def test_mode3_frame_replay_scenario():
    """Verify Mode 3 frame reference replay scenario runs cleanly."""
    res = run_mode3_frame_replay(virtual_camera_count=50, batches=1)
    assert res["scenario"] == "MODE_3_FRAME_REFERENCE_REPLAY"
    assert res["total_frames_multiplexed"] == 50
    assert res["verdict"] in ("PASSED", "DEGRADED")


def test_mode4_mixed_inference_scenario():
    """Verify Mode 4 mixed inference scenario runs cleanly."""
    res = run_mode4_mixed_inference(real_stream_count=5, virtual_metadata_count=50, inference_frames=5)
    assert res["scenario"] == "MODE_4_MIXED_INFERENCE_AND_METADATA"
    assert res["ai_inference_pipeline"]["frames_processed"] == 5
    assert res["verdict"] in ("PASSED", "DEGRADED")


def test_mode5_failure_recovery_scenario():
    """Verify Mode 5 failure and recovery chaos scenario runs cleanly."""
    res = run_mode5_failure_recovery(camera_count=100, drop_pct=0.10, reconnect_pct=0.10)
    assert res["scenario"] == "MODE_5_FAILURE_CHAOS_AND_RECOVERY"
    assert res["verdict"] == "PASSED_RESILIENT_SELF_HEALING"
    assert res["recovered_online_pct"] >= res["trough_online_pct"]
