#!/usr/bin/env bash
set -euo pipefail

# Simple local demo runner (optional).
# Run in two terminals for clarity; this script is mostly documentation.
echo "Terminal A: python demo_target_service.py"
echo "Terminal B: uvicorn qoe_guard.server:app --reload --port 8000"
echo "Then open http://127.0.0.1:8000"
