#!/bin/bash
cd "$(dirname "$0")"
source pi-yolo/bin/activate

# Start camera stream in background with logging
echo "[INFO] Starting camera stream at http://<your-pi-ip>:8000"
PYTHONPATH=src uvicorn src.streaming.camera_stream:app --host 0.0.0.0 --port 8000 > stream.log 2>&1 &

# Save PID to kill later
STREAM_PID=$!

# Start main robot logic
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py

# When demo_robot.py exits, kill the stream server
echo "[INFO] Shutting down camera stream (PID $STREAM_PID)..."
kill $STREAM_PID
