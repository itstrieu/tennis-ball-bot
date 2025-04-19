#!/bin/bash
cd "$(dirname "$0")"
source pi-yolo/bin/activate

# Start robot demo directly
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py
