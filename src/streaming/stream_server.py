# src/streaming/stream_server.py

import io
import asyncio
import logging
from threading import Condition, Thread
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

# --- import your robot modules ---
from src.app.camera_manager import get_camera
from src.app.robot_controller import RobotController
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.config import vision as vision_config, motion as motion_config

# ------------------------------------

# --- streaming classes (unchanged) ---
from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput

camera = None
vision = None


def set_shared_components(cam, vision_tracker):
    global camera, vision
    camera = cam
    vision = vision_tracker


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

    async def read(self):
        with self.condition:
            self.condition.wait()
            return self.frame


class JpegStream:
    def __init__(self):
        self.active = False
        self.connections = set()
        self.task = None
        self.output = StreamingOutput()

    async def stream_jpeg(self):
        if not camera:
            logging.error("Camera not initialized")
            return
        try:
            camera.start_recording(
                MJPEGEncoder(), FileOutput(self.output), Quality.MEDIUM
            )
            frame_count = 0
            while self.active:
                jpeg_data = await self.output.read()
                await asyncio.gather(
                    *(ws.send_bytes(jpeg_data) for ws in list(self.connections)),
                    return_exceptions=True,
                )
                frame_count += 1
                if frame_count % 60 == 0:
                    print(f"[+] Streaming to {len(self.connections)} clients")
        except Exception as e:
            logging.error(f"Streaming error: {e}")
        finally:
            camera.stop_recording()

    async def start(self):
        if not self.active:
            self.active = True
            self.task = asyncio.create_task(self.stream_jpeg())

    async def stop(self):
        if self.active:
            self.active = False
            if self.task:
                await self.task
                self.task = None


jpeg_stream = JpegStream()
# ------------------------------------

app = FastAPI()


# 1) On startup, initialize camera + robot and launch robot.run()
@app.on_event("startup")
def startup_event():
    cam = get_camera()
    motion = MotionController()
    motion.fin_on(speed=motion_config.FIN_SPEED)
    vis = VisionTracker(
        model_path=vision_config.MODEL_PATH,
        frame_width=vision_config.FRAME_WIDTH,
        camera=cam,
        camera_offset=vision_config.CAMERA_OFFSET,
    )
    strategy = MovementDecider(
        target_area=motion_config.TARGET_AREA,
        center_threshold=motion_config.CENTER_THRESHOLD,
    )
    robot = RobotController(motion, vis, strategy)

    set_shared_components(cam, vis)

    def run_robot():
        try:
            robot.run()
        finally:
            motion.fin_off()
            cam.stop()

    Thread(target=run_robot, daemon=True).start()
    print(
        "[INFO] Robot thread started. All routes registered:",
        [r.path for r in app.routes],
    )


# 2) Serve the HTML + JS UI
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html><head><title>Live Stream</title></head><body>
      <h1>Tennis Ball Bot Live</h1>
      <div id="status">Connecting...</div>
      <img id="stream"/>
      <script>
        const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')
                                  +location.host+'/ws');
        const status = document.getElementById('status');
        const img = document.getElementById('stream');
        ws.binaryType='blob';
        ws.onopen   = ()=>status.textContent='🟢 Connected';
        ws.onclose  = ()=>status.textContent='🔴 Disconnected';
        ws.onerror  = ()=>status.textContent='⚠️ Error';
        ws.onmessage= e=>{
          const url=URL.createObjectURL(e.data);
          img.src=url;
          setTimeout(()=>URL.revokeObjectURL(url),100);
        };
      </script>
    </body></html>
    """


# 3) WebSocket endpoint for MJPEG frames
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    jpeg_stream.connections.add(ws)
    if not jpeg_stream.active:
        await jpeg_stream.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        jpeg_stream.connections.discard(ws)
        if not jpeg_stream.connections:
            await jpeg_stream.stop()


# 4) (Optional) Debug route
@app.get("/debug")
def debug():
    return {"camera": camera is not None, "vision": vision is not None}


# 5) Run with: python src/streaming/stream_server.py
if __name__ == "__main__":
    uvicorn.run(
        "src.streaming.stream_server:app", host="0.0.0.0", port=8000, log_level="info"
    )
