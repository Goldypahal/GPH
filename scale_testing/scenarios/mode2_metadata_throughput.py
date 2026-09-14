"""
Mode 2: Metadata & Alert Ingestion Throughput Stress Test.
Evaluates:
- 80,000 virtual camera metadata streams (1 sighting per camera every 5s = 16,000 eps)
- Multi-tier burst condition evaluations:
  1. Normal Load:       1,000 events/sec
  2. Busy Period:      10,000 events/sec
  3. Major Incident:   50,000 events/sec
  4. Worst-Case Burst: 100,000 events/sec
- Watchlist matching, alert creation, and event bus latency percentiles
"""

import time
from typing import Dict, Any, List, Optional
from scale_testing.generators.sighting_generator import SightingGenerator
from scale_testing.metrics.collector import ScaleMetricsCollector
from backend.app.services.event_bus import event_bus


BURST_TIERS = {
    "normal": {"target_eps": 1000, "sample_events": 5000, "description": "Routine Statewide Traffic Flow"},
    "busy": {"target_eps": 10000, "sample_events": 20000, "description": "Peak Commute / Rush Hour"},
    "major_event": {"target_eps": 50000, "sample_events": 50000, "description": "Statewide VIP Movement / Festival Congestion"},
    "worst_burst": {"target_eps": 100000, "sample_events": 100000, "description": "Statewide Threat Vector Evacuation / Siren Burst"}
}


def run_mode2_metadata_throughput(
    tiers: Optional[List[str]] = None,
    hotlist_rate: float = 0.02
) -> Dict[str, Any]:
    """
    Executes Mode 2 Metadata & Alert Ingestion Throughput Test across burst tiers.
    """
    selected_tiers = tiers or ["normal", "busy", "major_event", "worst_burst"]
    tier_results = {}
    overall_collector = ScaleMetricsCollector(name="mode2_metadata_overall")
    overall_collector.start()

    hotlist_hits_total = 0

    for tier_key in selected_tiers:
        cfg = BURST_TIERS[tier_key]
        sample_size = cfg["sample_events"]
        tier_collector = ScaleMetricsCollector(name=f"mode2_{tier_key}")
        tier_collector.start()

        # Batch generation
        t0_gen = time.perf_counter()
        batch = SightingGenerator.generate_batch(batch_size=sample_size, hotlist_rate=hotlist_rate)
        gen_duration = time.perf_counter() - t0_gen

        # Processing loop (Event bus dispatch + watchlist evaluation)
        t0_proc = time.perf_counter()
        hot_count = 0
        chunk_size = 2000

        for idx in range(0, len(batch), chunk_size):
            chunk = batch[idx:idx + chunk_size]
            t_chunk_start = time.perf_counter()
            for evt in chunk:
                if evt.get("is_hotlist_target", False):
                    hot_count += 1
                # Publish event to decoupled memory bus
                event_bus.publish(event_bus.TOPIC_SIGHTINGS_RAW, evt)
            chunk_duration = time.perf_counter() - t_chunk_start
            tier_collector.record_batch(count=len(chunk), duration_sec=chunk_duration)
            overall_collector.record_batch(count=len(chunk), duration_sec=chunk_duration)

        tier_duration = time.perf_counter() - t0_proc
        tier_summary = tier_collector.compute_summary()
        hotlist_hits_total += hot_count

        tier_results[tier_key] = {
            "tier": tier_key,
            "description": cfg["description"],
            "target_eps": cfg["target_eps"],
            "events_processed": sample_size,
            "duration_sec": round(tier_duration, 4),
            "measured_throughput_eps": tier_summary["throughput_per_sec"],
            "target_achieved": tier_summary["throughput_per_sec"] >= (cfg["target_eps"] * 0.75),
            "latency_p50_ms": tier_summary["latency_p50_ms"],
            "latency_p95_ms": tier_summary["latency_p95_ms"],
            "latency_p99_ms": tier_summary["latency_p99_ms"],
            "hotlist_alerts_matched": hot_count,
            "packet_loss_pct": tier_summary["packet_loss_pct"]
        }

    overall_summary = overall_collector.compute_summary()

    return {
        "scenario": "MODE_2_METADATA_AND_BURST_THROUGHPUT",
        "total_events_processed": overall_summary["total_processed"],
        "overall_throughput_eps": overall_summary["throughput_per_sec"],
        "hotlist_alerts_triggered": hotlist_hits_total,
        "latency_p50_ms": overall_summary["latency_p50_ms"],
        "latency_p95_ms": overall_summary["latency_p95_ms"],
        "latency_p99_ms": overall_summary["latency_p99_ms"],
        "tier_benchmarks": tier_results,
        "system_resources": overall_summary["resources"],
        "verdict": "PASSED" if overall_summary["throughput_per_sec"] > 20000 else "DEGRADED"
    }
