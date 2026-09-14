#!/usr/bin/env python3
"""
CLI Tool: Generate and Inject Synthetic Sighting Bursts.
Simulates high-throughput ANPR event bursts (1,000 to 100,000 events/sec) into the event bus.
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scale_testing.scenarios.mode2_metadata_throughput import run_mode2_metadata_throughput, BURST_TIERS


def main():
    parser = argparse.ArgumentParser(description="Inject synthetic sighting load bursts into GIVIN event bus.")
    parser.add_argument("--tier", choices=["normal", "busy", "major_event", "worst_burst", "all"], default="all", help="Burst load tier to execute")
    parser.add_argument("--hotlist-rate", type=float, default=0.02, help="Watchlist hit probability (default: 0.02 = 2%)")
    args = parser.parse_args()

    tiers = None if args.tier == "all" else [args.tier]

    print("=" * 75)
    print("  GIVIN SIGHTING EVENT BURST INJECTOR")
    print(f"  Execution Tier(s): {args.tier} | Hotlist Ratio: {args.hotlist_rate * 100:.1f}%")
    print("=" * 75)

    res = run_mode2_metadata_throughput(tiers=tiers, hotlist_rate=args.hotlist_rate)

    print(f"\n[RESULT] Total Events Processed : {res['total_events_processed']}")
    print(f"[RESULT] Overall Throughput     : {res['overall_throughput_eps']} events/sec")
    print(f"[RESULT] Hotlist Alerts Matched : {res['hotlist_alerts_triggered']}")
    print(f"[RESULT] Latency (p50 / p95)    : {res['latency_p50_ms']} ms / {res['latency_p95_ms']} ms")
    print(f"[VERDICT] Status                : {res['verdict']}\n")

    print("Tier-by-Tier Performance:")
    for k, v in res["tier_benchmarks"].items():
        print(f"  - {k.upper():<12} | Target: {v['target_eps']:>6} eps | Measured: {v['measured_throughput_eps']:>8} eps | p95: {v['latency_p95_ms']:>5} ms | Alerts: {v['hotlist_alerts_matched']}")
    print("=" * 75)


if __name__ == "__main__":
    main()
