#!/bin/bash

# launch_demo.sh - start the demo_robot (with integrated camera stream)

# Change to the script's directory
cd "$(dirname "$0")" || exit 1

# Activate virtual environment
source pi-yolo/bin/activate

# Cleanup function to stop any lingering camera processes
cleanup() {
  echo "[INFO] Cleaning up camera processes..."
  # Terminate any picamera2 processes
  local pids
  if pids=$(pgrep -f picamera2); then
    echo "[INFO] Stopping camera processes: $pids"
    kill $pids 2>/dev/null
  fi
}

# Ensure cleanup runs on exit or interruption
trap cleanup SIGINT SIGTERM EXIT

# Launch demo_robot.py (which starts the camera stream internally)
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py