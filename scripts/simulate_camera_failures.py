#!/usr/bin/env python3
"""
CLI Tool: Simulate Camera Failures, Network Delays, and Reconnection Storms.
Injects chaos conditions into the 80,000 virtual camera fleet and measures self-healing.
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scale_testing.scenarios.mode5_failure_recovery import run_mode5_failure_recovery


def main():
    parser = argparse.ArgumentParser(description="Simulate camera drop, packet loss, and reconnection storms.")
    parser.add_argument("--count", type=int, default=80000, help="Total virtual fleet size (default: 80000)")
    parser.add_argument("--drop-pct", type=float, default=0.05, help="Percentage of cameras to drop offline (default: 0.05 = 5%)")
    parser.add_argument("--reconnect-pct", type=float, default=0.10, help="Percentage of cameras to reconnect concurrently (default: 0.10 = 10%)")
    args = parser.parse_args()

    print("=" * 75)
    print("  GIVIN CAMERA FLEET CHAOS & FAILURE RECOVERY SIMULATOR")
    print(f"  Fleet Size: {args.count} | Drop Rate: {args.drop_pct*100:.1f}% | Reconnection Storm: {args.reconnect_pct*100:.1f}%")
    print("=" * 75)

    res = run_mode5_failure_recovery(
        camera_count=args.count,
        drop_pct=args.drop_pct,
        reconnect_pct=args.reconnect_pct
    )

    print(f"\n[BASELINE] Initial Online Fleet   : {res['baseline_online_pct']}%")
    print(f"[CHAOS]    Trough Online Fleet    : {res['trough_online_pct']}%")
    print(f"[RECOVERY] Final Recovered Fleet  : {res['recovered_online_pct']}%")
    print(f"[STORM]    Reconnected Cameras    : {res['total_cameras_recovered']} at {res['reconnect_throughput_per_sec']} cams/sec")
    print(f"[DLQ]      Dead-Letter Quarantine : {'CONTAINED (ZERO LOSS)' if res['dead_letter_queue_contained'] else 'UNCONTAINED'}")
    print(f"[VERDICT]  Resilience Status      : {res['verdict']}\n")

    print("Chaos Timeline Events:")
    for step in res["chaos_timeline"]:
        print(f"  * {step['phase']}")
        for k, v in step.items():
            if k != "phase":
                print(f"      - {k}: {v}")
    print("=" * 75)


if __name__ == "__main__":
    main()
