#!/bin/bash
cd "$(dirname "$0")"
source pi-yolo/bin/activate

# Trap Ctrl+C to ensure cleanup
cleanup() {
  echo "[INFO] Shutting down camera stream (PID $STREAM_PID)..."
  kill $STREAM_PID 2>/dev/null
  exit
}
trap cleanup SIGINT SIGTERM

# Start camera stream in background with logging
echo "[INFO] Starting camera stream at http://raspberrypi.local:8000"
PYTHONPATH=src uvicorn src.streaming.camera_stream:app --host 0.0.0.0 --port 8000 > stream.log 2>&1 &
STREAM_PID=$!

# Wait a few seconds to let the stream boot
sleep 2

# Check if stream server is running
if ps -p $STREAM_PID > /dev/null; then
  echo "[INFO] Stream running with PID $STREAM_PID"
else
  echo "[ERROR] Stream failed to start. See stream.log:"
  tail stream.log
  exit 1
fi

# Start main robot logic
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py

# Cleanup after demo_robot exits
cleanup
