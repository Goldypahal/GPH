#!/usr/bin/env python3
"""
CLI Tool: Generate 80,000 Virtual Camera Fleet Definitions.
Exports heterogeneous camera profiles across all 33 Gujarat administrative districts.
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scale_testing.generators.camera_generator import CameraGenerator
from scale_testing.camera_profiles.district_fleet import GUJARAT_DISTRICTS_33, TOTAL_STATEWIDE_CAMERAS


def main():
    parser = argparse.ArgumentParser(description="Generate 80,000 camera fleet definition across 33 Gujarat districts.")
    parser.add_argument("--count", type=int, default=TOTAL_STATEWIDE_CAMERAS, help="Total cameras to generate (default: 80000)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format (json or csv)")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: artifacts/scale-80k/camera_fleet.<fmt>)")
    args = parser.parse_args()

    out_dir = os.path.join("artifacts", "scale-80k")
    os.makedirs(out_dir, exist_ok=True)
    out_file = args.output or os.path.join(out_dir, f"camera_fleet_{args.count}.{args.format}")

    print("=" * 75)
    print("  GIVIN 80,000 VIRTUAL CAMERA FLEET GENERATOR")
    print(f"  Target Fleet Size: {args.count} cameras across 33 Gujarat districts")
    print("=" * 75)

    t0 = time.perf_counter()
    if args.format == "json":
        count = CameraGenerator.export_to_json(out_file, limit=args.count)
    else:
        count = CameraGenerator.export_to_csv(out_file, limit=args.count)
    elapsed = time.perf_counter() - t0

    file_size_mb = os.path.getsize(out_file) / (1024 * 1024)

    print(f"[SUCCESS] Exported {count} camera profiles in {elapsed:.3f}s")
    print(f"[FILE] Saved to: {out_file} ({file_size_mb:.2f} MB)")
    print("\nDistrict Distribution Highlights:")
    for dist in GUJARAT_DISTRICTS_33[:6]:
        print(f"  - {dist['district']:<16} ({dist['code']}): {dist['cameras']:>5} cameras | Subnet: {dist['gateway_subnet']}")
    print(f"  ... and {len(GUJARAT_DISTRICTS_33) - 6} other districts.")
    print("=" * 75)


if __name__ == "__main__":
    main()
