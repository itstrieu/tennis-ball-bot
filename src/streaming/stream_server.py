# stream_server.py

import io
import asyncio
import logging
from threading import Condition
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput

camera = None
vision = None


def set_shared_components(cam, vision_tracker=None):
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
                try:
                    jpeg_data = await self.output.read()
                except asyncio.CancelledError:
                    break
                await asyncio.gather(
                    *(ws.send_bytes(jpeg_data) for ws in list(self.connections)),
                    return_exceptions=True,
                )
                frame_count += 1
                if frame_count % 60 == 0:
                    print(f"[+] Streaming to {len(self.connections)} clients")
        finally:
            camera.stop_recording()

    async def start(self):
        if not self.active:
            self.active = True
            self.task = asyncio.create_task(self.stream_jpeg())

    async def stop(self):
        if self.active:
            self.active = False
            # Wake any blocked read()
            with self.output.condition:
                self.output.condition.notify_all()
            if self.task:
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                finally:
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
        body { font-family: Arial, sans-serif; text-align: center; padding: 2em; }
        #stream { border: 3px solid #444; border-radius: 6px; width: 640px; }
      </style>
    </head>
    <body>
      <h1>Tennis Ball Bot • Live Stream</h1>
      <img id="stream" src="" alt="Live camera feed"/>
      <script>
        const ws = new WebSocket(
          (location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws'
        );
        const img = document.getElementById('stream');
        ws.binaryType = 'blob';
        ws.onmessage = e => {
          const url = URL.createObjectURL(e.data);
          img.src = url;
          setTimeout(()=>URL.revokeObjectURL(url),100);
        };
      </script>
    </body>
    </html>
    """


@app.get("/debug")
def debug():
    return {"camera": camera is not None, "vision": vision is not None}


@app.post("/start")
async def start_stream():
    await jpeg_stream.start()
    return {"status": "stream started"}


@app.post("/stop")
async def stop_stream():
    await jpeg_stream.stop()
    return {"status": "stream stopped"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    jpeg_stream.connections.add(ws)
    if not jpeg_stream.active:
        await jpeg_stream.start()
    try:
        while True:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
    finally:
        jpeg_stream.connections.discard(ws)
        if not jpeg_stream.connections:
            await jpeg_stream.stop()


if __name__ == "__main__":
    import sys

    try:
        uvicorn.run("stream_server:app", host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server interrupted by user, shutting down.")
        sys.exit(0)
