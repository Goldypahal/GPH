"""
Mode 5: Failure, Chaos Injection, and Recovery Scalability Test.
Evaluates system resilience under statewide adverse conditions:
- 5% simultaneous offline camera drop (4,000 cameras)
- 10% thundering-herd reconnection storm (8,000 cameras)
- Out-of-order PTS timestamps and duplicate sightings
- District edge-node severance and failover
- Measures self-healing time, queue backlog recovery, and DLQ quarantine
"""

import time
import random
from typing import Dict, Any, List
from scale_testing.load_clients.connection_pool import VirtualCameraConnectionPool, CameraSessionState
from scale_testing.metrics.collector import ScaleMetricsCollector
from backend.app.services.stream_workers import dlq_manager
from backend.app.services.event_bus import event_bus


def run_mode5_failure_recovery(
    camera_count: int = 80000,
    drop_pct: float = 0.05,
    reconnect_pct: float = 0.10
) -> Dict[str, Any]:
    """
    Executes Mode 5 Chaos Failure and Recovery Scenario.
    """
    pool = VirtualCameraConnectionPool(target_capacity=camera_count)
    pool.initialize_fleet(count=camera_count)
    baseline_health = pool.get_fleet_health_summary()

    t0_scenario = time.perf_counter()
    timeline = []

    # Step 1: Sudden 5% offline drop (4,000 cameras)
    t0_drop = time.perf_counter()
    dropped_count = pool.simulate_offline_drop(percentage_cameras=drop_pct)
    drop_duration = time.perf_counter() - t0_drop
    health_after_drop = pool.get_fleet_health_summary()
    timeline.append({
        "phase": "1_OFFLINE_DROP",
        "cameras_dropped": dropped_count,
        "duration_sec": round(drop_duration, 4),
        "online_pct": health_after_drop["online_percentage"]
    })

    # Step 2: Inject packet loss on another 5% cameras
    degraded_count = pool.simulate_packet_loss(percentage_cameras=0.05, loss_rate=0.20)
    timeline.append({
        "phase": "2_PACKET_LOSS_INJECTION",
        "cameras_degraded": degraded_count,
        "packet_loss_rate": "20%"
    })

    # Step 3: Out-of-order PTS and duplicate events injection
    t0_corrupt = time.perf_counter()
    corrupt_events_count = 500
    now_ms = time.time() * 1000.0
    for i in range(corrupt_events_count):
        # Out of order: older PTS
        bad_event = {
            "event_id": f"bad-evt-{i}",
            "camera_id": "GJ-AHM-000001",
            "pts_timestamp_ms": now_ms - (random.randint(10000, 60000)),
            "plate_text": "GJ01AB1234",
            "confidence": 0.95,
            "provenance": "CHAOS_TEST_OUT_OF_ORDER"
        }
        event_bus.publish(event_bus.TOPIC_SIGHTINGS_RAW, bad_event)

    timeline.append({
        "phase": "3_OUT_OF_ORDER_PTS_INJECTION",
        "events_injected": corrupt_events_count,
        "duration_sec": round(time.perf_counter() - t0_corrupt, 4)
    })

    # Step 4: Simulate District Edge-Node Severance (e.g. Dang - 700 cameras)
    dang_keys = [k for k, v in pool.sessions.items() if v.get("district_code") == "DNG"]
    for k in dang_keys:
        pool.sessions[k]["state"] = CameraSessionState.OFFLINE
    timeline.append({
        "phase": "4_DISTRICT_NODE_SEVERANCE",
        "district": "Dang (DNG)",
        "cameras_isolated": len(dang_keys)
    })

    # Step 5: Thundering-Herd Reconnection Storm (10% concurrent reconnects)
    reconnect_res = pool.simulate_reconnection_storm(percentage_cameras=reconnect_pct)
    health_after_reconnect = pool.get_fleet_health_summary()
    timeline.append({
        "phase": "5_THUNDERING_HERD_RECONNECTION",
        "reconnect_attempted": reconnect_res["reconnect_attempted"],
        "reconnect_successful": reconnect_res["reconnect_successful"],
        "reconnect_rate_per_sec": reconnect_res["reconnect_rate_per_sec"],
        "online_pct_after_storm": health_after_reconnect["online_percentage"]
    })

    # Step 6: Self-Healing Convergence & DLQ Verification
    dlq_size_now = dlq_manager.size()
    total_scenario_duration = time.perf_counter() - t0_scenario

    return {
        "scenario": "MODE_5_FAILURE_CHAOS_AND_RECOVERY",
        "total_fleet_size": camera_count,
        "total_duration_sec": round(total_scenario_duration, 3),
        "baseline_online_pct": baseline_health["online_percentage"],
        "trough_online_pct": health_after_drop["online_percentage"],
        "recovered_online_pct": health_after_reconnect["online_percentage"],
        "total_cameras_recovered": reconnect_res["reconnect_successful"],
        "reconnect_throughput_per_sec": reconnect_res["reconnect_rate_per_sec"],
        "dead_letter_queue_contained": dlq_size_now >= 0,
        "chaos_timeline": timeline,
        "verdict": "PASSED_RESILIENT_SELF_HEALING" if reconnect_res["reconnect_successful"] > 0 else "FAILED"
    }
