"""
Mode 1: Connection-Only Scalability Stress Test.
Evaluates:
- 80,000 virtual camera client sessions
- Paced heartbeat dispatch (0.1 - 1.0 Hz)
- Connection establishment rate and host memory footprint
- No video inference (pure connection & health management)
"""

import time
from typing import Dict, Any, Optional
from scale_testing.load_clients.connection_pool import VirtualCameraConnectionPool
from scale_testing.metrics.collector import ScaleMetricsCollector


def run_mode1_connection_stress(
    camera_count: int = 80000,
    rounds: int = 3,
    sample_per_round: int = 20000
) -> Dict[str, Any]:
    """
    Executes Mode 1 Connection Stress Test.
    """
    collector = ScaleMetricsCollector(name=f"mode1_connection_stress_{camera_count}")
    pool = VirtualCameraConnectionPool(target_capacity=camera_count)

    # 1. Fleet Initialization
    t0_init = time.perf_counter()
    mem_before = collector.get_resource_snapshot()["ram_used_mb"]
    fleet_size = pool.initialize_fleet(count=camera_count)
    init_duration_sec = time.perf_counter() - t0_init
    mem_after = collector.get_resource_snapshot()["ram_used_mb"]
    mem_delta_mb = max(0.1, mem_after - mem_before)

    # 2. Dispatch Heartbeat Rounds
    collector.start()
    round_results = []
    for r in range(rounds):
        res = pool.dispatch_heartbeats(sample_size=sample_per_round)
        collector.record_batch(
            count=res["dispatched"],
            duration_sec=res["duration_sec"]
        )
        round_results.append(res)

    summary = collector.compute_summary()
    fleet_health = pool.get_fleet_health_summary()

    return {
        "scenario": "MODE_1_CONNECTION_ONLY",
        "target_cameras": camera_count,
        "fleet_initialized": fleet_size,
        "init_duration_sec": round(init_duration_sec, 3),
        "memory_delta_mb": round(mem_delta_mb, 1),
        "bytes_per_session": round((mem_delta_mb * 1024 * 1024) / max(1, fleet_size), 1),
        "rounds_executed": rounds,
        "samples_per_round": sample_per_round,
        "total_heartbeats_dispatched": summary["total_processed"],
        "heartbeat_throughput_hps": summary["throughput_per_sec"],
        "latency_p50_ms": summary["latency_p50_ms"],
        "latency_p95_ms": summary["latency_p95_ms"],
        "latency_p99_ms": summary["latency_p99_ms"],
        "fleet_health": fleet_health,
        "system_resources": summary["resources"],
        "verdict": "PASSED" if summary["throughput_per_sec"] > 5000 else "DEGRADED"
    }
