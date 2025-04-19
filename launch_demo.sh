#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Activate virtual environment
source pi-yolo/bin/activate

# Cleanup on exit
cleanup() {
  # Check if the camera stream is running and kill it
  if [ ! -z "$STREAM_PID" ]; then
    echo "[INFO] Shutting down camera stream (PID $STREAM_PID)..."
    kill $STREAM_PID 2>/dev/null
  fi

  # If any camera process is running, try killing it
  echo "[INFO] Checking for any camera processes..."
  camera_pid=$(ps aux | grep -i 'picamera2' | grep -v 'grep' | awk '{print $2}')
  if [ ! -z "$camera_pid" ]; then
    echo "[INFO] Found camera process (PID $camera_pid), terminating..."
    kill $camera_pid
  fi

  exit
}

# Trap SIGINT and SIGTERM signals to ensure cleanup
trap cleanup SIGINT SIGTERM

# Start camera stream in the background with logging
echo "[INFO] Starting camera stream at http://raspberrypi.local:8000"
PYTHONPATH=src uvicorn src.streaming.stream_client:app --host 0.0.0.0 --port 8000 > stream.log 2>&1 &
STREAM_PID=$!

# Wait a few seconds to let the stream boot
sleep 2
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py

# Cleanup after demo_robot.py exits
cleanup
