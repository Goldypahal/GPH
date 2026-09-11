#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  Launching GIVIN Zero-to-Demo Environment"
echo "========================================================"

python3 scripts/bootstrap_demo.py

echo "[SUCCESS] Zero-to-Demo completed with exit code 0."

