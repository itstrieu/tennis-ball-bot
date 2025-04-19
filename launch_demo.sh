#!/bin/bash
cd "$(dirname "$0")"
source pi-yolo/bin/activate

# Cleanup on exit
cleanup() {
  echo "[INFO] Shutting down camera stream (PID $STREAM_PID)..."
  kill $STREAM_PID 2>/dev/null
  exit
}
trap cleanup SIGINT SIGTERM

echo "[INFO] Starting camera stream at http://raspberrypi.local:8000"
PYTHONPATH=src uvicorn src.streaming.stream_client:app --host 0.0.0.0 --port 8000 > stream.log 2>&1 &
STREAM_PID=$!

sleep 2
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py

cleanup
