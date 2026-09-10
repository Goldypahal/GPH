#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  Launching GIVIN Demonstration Environment"
echo "========================================================"

python3 scripts/demo_seed.py
python3 scripts/run_demo.py

echo "[SUCCESS] Demonstration completed successfully."
