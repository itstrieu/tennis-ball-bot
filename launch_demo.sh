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

# Inject shared camera instance before launching stream
echo "[INFO] Injecting camera into stream_client..."
PYTHONPATH=src python3 -c "from src.app.camera_manager import get_camera; from src.streaming import stream_client; stream_client.set_camera(get_camera())"

# Launch stream server
echo "[INFO] Starting camera stream at http://raspberrypi.local:8000"
PYTHONPATH=src uvicorn src.streaming.stream_client:app --host 0.0.0.0 --port 8000 > stream.log 2>&1 &
STREAM_PID=$!

# Let stream warm up
sleep 2

# Launch main robot control loop
echo "[INFO] Launching demo_robot.py..."
PYTHONPATH=src python3 demo_robot.py

# Cleanup when robot script exits
cleanup
