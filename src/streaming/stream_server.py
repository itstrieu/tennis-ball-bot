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
import time

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
        self.jpeg_stream = JpegStream(self.config)
        self._stream_lock = asyncio.Lock()
        self._setup_routes()

    def set_components(self, camera, vision=None):
        """Set the camera and vision components."""
        self.camera = camera
        self.vision = vision
        self.jpeg_stream.set_camera(camera)

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
                let ws = null;
                const img = document.getElementById('stream');
                const status = document.getElementById('status');
                
                function connectWebSocket() {
                  ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws');
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
                    status.textContent = 'WebSocket disconnected - reconnecting...';
                    status.style.background = '#fff3e0';
                    status.style.color = '#e65100';
                    setTimeout(connectWebSocket, 1000);  // Reconnect after 1 second
                  };
                  
                  ws.onerror = () => {
                    status.textContent = 'WebSocket error - reconnecting...';
                    status.style.background = '#ffebee';
                    status.style.color = '#c62828';
                    ws.close();  // Force close to trigger reconnection
                  };
                }
                
                // Initial connection
                connectWebSocket();
                
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
                # Verify camera is ready
                test_frame = self.camera.get_frame()
                if test_frame is None:
                    raise RobotError("Camera not capturing frames", "stream_server")
                    
                # Start the stream
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
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time video streaming."""
            try:
                await websocket.accept()
                self.jpeg_stream.connections.add(websocket)
                self.logger.info("New WebSocket connection established")
                
                # Send initial frame from buffer if available
                async with self.jpeg_stream._frame_buffer_lock:
                    if self.jpeg_stream._frame_buffer:
                        try:
                            await websocket.send_bytes(self.jpeg_stream._frame_buffer[-1])
                        except Exception as e:
                            self.logger.error(f"Error sending initial frame: {str(e)}")
                
                # Keep connection alive with pings
                while True:
                    try:
                        await asyncio.sleep(5)  # Send ping every 5 seconds
                        await websocket.send_text("ping")
                    except Exception as e:
                        self.logger.error(f"Error sending ping: {str(e)}")
                        break
                    
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
            finally:
                self.jpeg_stream.connections.discard(websocket)
                if not self.jpeg_stream.connections:
                    await self.jpeg_stream.stop()
                self.logger.info("WebSocket connection closed")

    @with_error_handling("stream_server")
    async def start(self, host="0.0.0.0", port=8000):
        """Start the streaming server."""
        async with self._stream_lock:
            try:
                if not self.camera:
                    raise RobotError("Camera not available", "stream_server")
                    
                # Verify camera is ready
                try:
                    test_frame = await self.camera.get_frame()
                    if test_frame is None:
                        raise RobotError("Camera not capturing frames", "stream_server")
                except Exception as e:
                    raise RobotError(f"Camera verification failed: {str(e)}", "stream_server")
                    
                # Start the stream
                await self.jpeg_stream.start()
                
                # Start the server
                config = uvicorn.Config(
                    self.app,
                    host=host,
                    port=port,
                    log_level="info",
                    timeout_keep_alive=30
                )
                server = uvicorn.Server(config)
                self.logger.info(f"Starting streaming server on {host}:{port}")
                await server.serve()
            except Exception as e:
                self.logger.error(f"Failed to start server: {str(e)}")
                await self.stop()  # Ensure cleanup on failure
                raise RobotError(f"Server start failed: {str(e)}", "stream_server")

    @with_error_handling("stream_server")
    async def stop(self):
        """Stop the streaming server."""
        async with self._stream_lock:
            try:
                # Stop the JPEG stream
                if self.jpeg_stream.active:
                    await self.jpeg_stream.stop()
                    
                # Close all WebSocket connections
                for ws in list(self.jpeg_stream.connections):
                    try:
                        await ws.close()
                    except Exception as e:
                        self.logger.error(f"Error closing WebSocket connection: {str(e)}")
                        
                self.jpeg_stream.connections.clear()
                self.logger.info("Streaming server stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop server: {str(e)}")
                raise RobotError(f"Server stop failed: {str(e)}", "stream_server")


class StreamingOutput(io.BufferedIOBase):
    """Handles frame buffering and synchronization for streaming."""
    
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self._closed = False

    def write(self, buf):
        """Write frame to stream."""
        if self._closed:
            return
            
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

    async def read(self):
        """Read next frame from stream."""
        if self._closed:
            raise IOError("Stream is closed")
            
        with self.condition:
            if self.frame is None:
                self.condition.wait()
            frame = self.frame
            self.frame = None  # Clear frame after reading
            return frame

    def close(self):
        """Close the stream."""
        with self.condition:
            self._closed = True
            self.condition.notify_all()


class JpegStream:
    """Handles JPEG streaming of frames."""
    
    def __init__(self, config):
        self.config = config
        self.logger = Logger.get_logger(name="jpeg_stream", log_level=logging.INFO)
        self.camera = None
        self.active = False
        self.connections = set()
        self._frame_buffer = []
        self._frame_buffer_lock = asyncio.Lock()
        self._frame_buffer_size = self.config.frame_buffer_size
        self._frame_interval = 1.0 / self.config.streaming_fps
        self._last_frame_time = 0

    def set_camera(self, camera):
        """Set the camera reference."""
        self.camera = camera

    async def _stream_frames(self):
        """Stream frames to connected clients."""
        while self.active:
            try:
                # Get frame from camera
                frame = await self.camera.get_frame()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue

                # Encode frame to JPEG
                ret, jpeg = cv2.imencode('.jpg', frame, 
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.streaming_quality])
                if not ret:
                    self.logger.error("Failed to encode frame to JPEG")
                    continue

                # Add frame to buffer
                async with self._frame_buffer_lock:
                    if len(self._frame_buffer) >= self._frame_buffer_size:
                        self._frame_buffer.pop(0)
                    self._frame_buffer.append(jpeg.tobytes())

                # Send frame to all connected clients
                for ws in list(self.connections):
                    try:
                        await ws.send_bytes(jpeg.tobytes())
                    except Exception as e:
                        self.logger.error(f"Error sending frame to client: {str(e)}")
                        self.connections.discard(ws)

                # Control frame rate
                current_time = time.time()
                elapsed = current_time - self._last_frame_time
                if elapsed < self._frame_interval:
                    await asyncio.sleep(self._frame_interval - elapsed)
                self._last_frame_time = time.time()

            except Exception as e:
                self.logger.error(f"Error in frame streaming: {str(e)}")
                await asyncio.sleep(0.1)

    async def start(self):
        """Start the stream."""
        if not self.camera:
            raise RobotError("Camera not set", "jpeg_stream")
        self.active = True
        self._last_frame_time = time.time()
        asyncio.create_task(self._stream_frames())
        self.logger.info("JPEG stream started")

    async def stop(self):
        """Stop the stream."""
        self.active = False
        async with self._frame_buffer_lock:
            self._frame_buffer.clear()
        self.logger.info("JPEG stream stopped")
