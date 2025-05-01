import io
import asyncio
import logging
from threading import Condition
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse
from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput

# Shared components from robot main()
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
            while self.active:
                jpeg_data = await self.output.read()
                tasks = [ws.send_bytes(jpeg_data) for ws in self.connections.copy()]
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logging.error(f"Streaming error: {e}")
        finally:
            try:
                camera.stop_recording()
            except Exception:
                pass

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await jpeg_stream.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tennis Ball Bot • Live Stream</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #f7f7f7;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px;
            }
            h1 {
                margin-bottom: 10px;
            }
            #stream {
                width: 640px;
                height: auto;
                border: 3px solid #444;
                border-radius: 6px;
                margin-top: 20px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            }
            .controls {
                margin-top: 20px;
                display: flex;
                gap: 10px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            #status {
                margin-top: 10px;
                font-size: 14px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <h1>Tennis Ball Bot • Live Stream</h1>
        <div class="controls">
            <button onclick="fetch('/start', {method: 'POST'})">Start Stream</button>
            <button onclick="fetch('/stop', {method: 'POST'})">Stop Stream</button>
        </div>
        <div id="status">Connecting...</div>
        <img id="stream" src="" alt="Live camera feed"/>
        <script>
            const ws = new WebSocket("ws://" + location.host + "/ws");
            const img = document.getElementById("stream");
            const status = document.getElementById("status");

            ws.binaryType = "blob";

            ws.onopen = () => {
                status.textContent = "🟢 Connected";
            };
            ws.onclose = () => {
                status.textContent = "🔴 Disconnected";
            };
            ws.onerror = () => {
                status.textContent = "⚠️ Error with WebSocket.";
            };

            ws.onmessage = (event) => {
                const url = URL.createObjectURL(event.data);
                img.src = url;
            };
        </script>
    </body>
    </html>
    """


@app.get("/debug")
def debug():
    return {"camera_exists": camera is not None, "vision_exists": vision is not None}


@app.post("/start")
async def start_stream():
    await jpeg_stream.start()
    return {"message": "Stream started"}


@app.post("/stop")
async def stop_stream():
    await jpeg_stream.stop()
    return {"message": "Stream stopped"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    jpeg_stream.connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        jpeg_stream.connections.remove(websocket)
        if not jpeg_stream.connections:
            await jpeg_stream.stop()
