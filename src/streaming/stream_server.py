"""
stream_server.py

FastAPI server for streaming camera feed and providing debug information.
Handles WebSocket connections for real-time video streaming.
"""

import io
import asyncio
import logging
from threading import Condition
from contextlib import asynccontextmanager
from typing import Optional, Set

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput

from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class StreamServer:
    """
    Manages the streaming server and its components.
    
    Attributes:
        config: RobotConfig instance for configuration values
        camera: CameraManager instance
        vision: VisionTracker instance
        logger: Logger instance
        app: FastAPI application
        jpeg_stream: JpegStream instance
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger.get_logger(name="stream", log_level=logging.INFO)
        self.camera = None
        self.vision = None
        self.app = FastAPI()
        self.jpeg_stream = JpegStream()
        self._setup_routes()

    def set_components(self, camera, vision=None):
        """Set the camera and vision components."""
        self.camera = camera
        self.vision = vision

    def _setup_routes(self):
        """Set up FastAPI routes."""
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            return """
            <!DOCTYPE html>
            <html>
            <head>
              <title>Tennis Ball Bot • Live Stream</title>
              <style>
                body { 
                  font-family: Arial, sans-serif; 
                  text-align: center; 
                  padding: 2em;
                  background: #f5f5f5;
                }
                #stream { 
                  border: 3px solid #444; 
                  border-radius: 6px; 
                  width: 640px;
                  max-width: 100%;
                  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
                .controls { 
                  margin: 1em; 
                  padding: 1em;
                  background: white;
                  border-radius: 6px;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                button { 
                  padding: 0.5em 1em; 
                  margin: 0 0.5em;
                  border: none;
                  border-radius: 4px;
                  background: #4CAF50;
                  color: white;
                  cursor: pointer;
                  transition: background 0.3s;
                }
                button:hover {
                  background: #45a049;
                }
                button:active {
                  background: #3d8b40;
                }
                .status {
                  margin: 1em;
                  padding: 0.5em;
                  border-radius: 4px;
                  background: #e8f5e9;
                  color: #2e7d32;
                }
              </style>
            </head>
            <body>
              <h1>Tennis Ball Bot • Live Stream</h1>
              <div class="controls">
                <button onclick="startStream()">Start Stream</button>
                <button onclick="stopStream()">Stop Stream</button>
                <div class="status" id="status">Stream not started</div>
              </div>
              <img id="stream" src="" alt="Live camera feed"/>
              <script>
                const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws');
                const img = document.getElementById('stream');
                const status = document.getElementById('status');
                
                ws.binaryType = 'blob';
                ws.onmessage = e => {
                  const url = URL.createObjectURL(e.data);
                  img.src = url;
                  setTimeout(()=>URL.revokeObjectURL(url),100);
                };
                
                ws.onopen = () => {
                  status.textContent = 'WebSocket connected';
                  status.style.background = '#e8f5e9';
                  status.style.color = '#2e7d32';
                };
                
                ws.onclose = () => {
                  status.textContent = 'WebSocket disconnected';
                  status.style.background = '#ffebee';
                  status.style.color = '#c62828';
                };
                
                ws.onerror = () => {
                  status.textContent = 'WebSocket error';
                  status.style.background = '#ffebee';
                  status.style.color = '#c62828';
                };
                
                async function startStream() {
                  try {
                    const response = await fetch('/start', {method: 'POST'});
                    const data = await response.json();
                    status.textContent = 'Stream started';
                    status.style.background = '#e8f5e9';
                    status.style.color = '#2e7d32';
                  } catch (error) {
                    status.textContent = 'Failed to start stream';
                    status.style.background = '#ffebee';
                    status.style.color = '#c62828';
                  }
                }
                
                async function stopStream() {
                  try {
                    const response = await fetch('/stop', {method: 'POST'});
                    const data = await response.json();
                    status.textContent = 'Stream stopped';
                    status.style.background = '#fff3e0';
                    status.style.color = '#e65100';
                  } catch (error) {
                    status.textContent = 'Failed to stop stream';
                    status.style.background = '#ffebee';
                    status.style.color = '#c62828';
                  }
                }
              </script>
            </body>
            </html>
            """

        @self.app.get("/debug")
        @with_error_handling("stream_server")
        def debug():
            """Return debug information about the robot's state."""
            if not self.vision:
                return {"error": "Vision tracker not available"}
                
            try:
                return {
                    "detections": self.vision.get_detections(),
                    "frame_count": self.vision.frame_count,
                    "fps": self.vision.get_fps()
                }
            except Exception as e:
                self.logger.error(f"Error getting debug info: {str(e)}")
                return {"error": str(e)}

        @self.app.post("/start")
        @with_error_handling("stream_server")
        async def start_stream():
            """Start the video stream."""
            if not self.camera:
                raise RobotError("Camera not available", "stream_server")
                
            try:
                await self.jpeg_stream.start()
                return {"status": "streaming"}
            except Exception as e:
                self.logger.error(f"Failed to start stream: {str(e)}")
                raise RobotError(f"Stream start failed: {str(e)}", "stream_server")

        @self.app.post("/stop")
        @with_error_handling("stream_server")
        async def stop_stream():
            """Stop the video stream."""
            try:
                await self.jpeg_stream.stop()
                return {"status": "stopped"}
            except Exception as e:
                self.logger.error(f"Failed to stop stream: {str(e)}")
                raise RobotError(f"Stream stop failed: {str(e)}", "stream_server")

        @self.app.websocket("/ws")
        @with_error_handling("stream_server")
        async def websocket_endpoint(ws: WebSocket):
            """Handle WebSocket connections for video streaming."""
            await ws.accept()
            self.jpeg_stream.connections.add(ws)
            
            try:
                while True:
                    frame = await self.jpeg_stream.output.read()
                    await ws.send_bytes(frame)
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
            finally:
                self.jpeg_stream.connections.remove(ws)

    @with_error_handling("stream_server")
    async def start(self, host="0.0.0.0", port=8000):
        """Start the streaming server."""
        try:
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            self.logger.error(f"Failed to start server: {str(e)}")
            raise RobotError(f"Server start failed: {str(e)}", "stream_server")

    @with_error_handling("stream_server")
    async def stop(self):
        """Stop the streaming server."""
        try:
            await self.jpeg_stream.stop()
            self.logger.info("Streaming server stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop server: {str(e)}")
            raise RobotError(f"Server stop failed: {str(e)}", "stream_server")


class StreamingOutput(io.BufferedIOBase):
    """Handles frame buffering and synchronization for streaming."""
    
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        """Write frame to stream."""
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

    async def read(self):
        """Read next frame from stream."""
        with self.condition:
            self.condition.wait()
            return self.frame


class JpegStream:
    """Manages JPEG encoding and streaming of video frames."""
    
    def __init__(self):
        self.active = False
        self.connections = set()
        self.task = None
        self.output = StreamingOutput()
        self.encoder = MJPEGEncoder()

    async def start(self):
        """Start the JPEG stream."""
        if self.active:
            return
            
        self.active = True
        self.task = asyncio.create_task(self._stream_frames())

    async def stop(self):
        """Stop the JPEG stream."""
        self.active = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None

    async def _stream_frames(self):
        """Stream frames to connected clients."""
        while self.active:
            try:
                frame = await self.output.read()
                for ws in self.connections:
                    try:
                        await ws.send_bytes(frame)
                    except Exception:
                        self.connections.remove(ws)
            except Exception as e:
                self.logger.error(f"Error streaming frame: {str(e)}")
                await asyncio.sleep(0.1)
