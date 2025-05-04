#!/bin/bash

# launch_demo.sh - start the demo_robot (with integrated camera stream)

# Change to the script's directory
cd "$(dirname "$0")" || exit 1

# Check if virtual environment exists
if [ ! -d "pi-yolo" ]; then
    echo "[ERROR] Virtual environment 'pi-yolo' not found"
    exit 1
fi

# Activate virtual environment
source pi-yolo/bin/activate

# Cleanup function to stop any lingering camera processes
cleanup() {
  echo "[INFO] Cleaning up camera processes..."
  # Terminate any picamera2 processes
  local pids
  if pids=$(pgrep -f "python.*demo_robot.py"); then
    echo "[INFO] Stopping demo processes: $pids"
    kill $pids 2>/dev/null
  fi
  # Give processes time to clean up
  sleep 1
}

# Ensure cleanup runs on exit or interruption
trap cleanup SIGINT SIGTERM EXIT

# Launch demo_robot.py (which starts the camera stream internally)
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py