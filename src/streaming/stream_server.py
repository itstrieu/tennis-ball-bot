"""
stream_server.py

FastAPI server for streaming camera feed and providing debug information.
Handles WebSocket connections for real-time video streaming.
"""

import io
import asyncio
import logging
import threading
from threading import Condition
from contextlib import asynccontextmanager
from typing import Optional, Set
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import cv2

from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class StreamServer:
    """
    Manages the streaming server and its components.
    Uses the camera's streaming architecture for efficient frame delivery.
    
    Attributes:
        config: RobotConfig instance for configuration values
        camera: CameraManager instance
        vision: VisionTracker instance
        logger: Logger instance
        app: FastAPI application
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger.get_logger(name="stream", log_level=logging.INFO)
        self.camera = None
        self.vision = None
        self.app = FastAPI()
        self._stream_lock = asyncio.Lock()
        self._stream_consumers = set()
        self._server_thread = None
        self._should_stop = False
        self._setup_routes()

    def set_components(self, camera, vision=None):
        """Set the camera and vision components."""
        self.camera = camera
        self.vision = vision

    async def _get_frame(self):
        """Get frame from camera."""
        if not self.camera:
            raise RobotError("Camera not available", "stream_server")
            
        try:
            # Get frame directly from camera
            frame = self.camera.camera.capture_array()
            if frame is not None:
                return frame
            return None
        except Exception as e:
            self.logger.error(f"Error getting frame: {str(e)}")
            raise RobotError(f"Frame capture failed: {str(e)}", "stream_server")

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
                await self.camera.start_streaming()
                return {"status": "streaming"}
            except Exception as e:
                self.logger.error(f"Failed to start stream: {str(e)}")
                raise RobotError(f"Stream start failed: {str(e)}", "stream_server")

        @self.app.post("/stop")
        @with_error_handling("stream_server")
        async def stop_stream():
            """Stop the video stream."""
            try:
                await self.camera.stop_streaming()
                return {"status": "stopped"}
            except Exception as e:
                self.logger.error(f"Failed to stop stream: {str(e)}")
                raise RobotError(f"Stream stop failed: {str(e)}", "stream_server")

        @self.app.websocket("/ws")
        @with_error_handling("stream_server")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for streaming camera feed."""
            try:
                await websocket.accept()
                self.logger.info("WebSocket connection accepted")
                
                # Register as a stream consumer
                await self.camera.register_stream_consumer()
                
                # Start camera streaming if not already started
                if not self.camera._streaming:
                    await self.camera.start_streaming()
                
                try:
                    while True:
                        # Get frame from camera in the correct event loop context
                        frame = await self._get_frame()
                        if frame is None:
                            continue
                        
                        # Encode frame as JPEG for streaming
                        ret, jpeg = cv2.imencode('.jpg', frame)
                        if not ret:
                            continue
                        try:
                            await websocket.send_bytes(jpeg.tobytes())
                        except WebSocketDisconnect:
                            break
                        
                        # Small sleep to prevent CPU hogging
                        await asyncio.sleep(0.001)
                        
                except WebSocketDisconnect:
                    self.logger.info("WebSocket disconnected")
                except Exception as e:
                    self.logger.error(f"Error in WebSocket stream: {str(e)}")
                    raise
                finally:
                    # Cleanup
                    await self.camera.unregister_stream_consumer()
                    if not self.camera._stream_consumers:
                        await self.camera.stop_streaming()
                    try:
                        await websocket.close()
                    except:
                        pass
                    
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
                try:
                    await websocket.close()
                except:
                    pass
                raise

    async def start(self):
        """Start the streaming server."""
        if self._server_thread is not None:
            self.logger.warning("Stream server already running")
            return
            
        if not self.camera:
            self.logger.warning("Camera not available - streaming disabled")
            return
            
        try:
            # Start camera streaming
            await self.camera.start_streaming()
            
            # Create server thread
            self._server_thread = threading.Thread(target=self._run_server)
            self._server_thread.daemon = True
            self._server_thread.start()
            
            self.logger.info("Stream server started")
        except Exception as e:
            self.logger.error(f"Failed to start stream server: {str(e)}")
            raise RobotError(f"Stream server start failed: {str(e)}", "stream_server")

    def _run_server(self):
        """Run the server in a separate thread."""
        try:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
        except Exception as e:
            self.logger.error(f"Server thread error: {str(e)}")

    async def stop(self):
        """Stop the streaming server."""
        if self._server_thread is None:
            return
            
        try:
            # Stop camera streaming
            await self.camera.stop_streaming()
            
            # Signal server to stop
            self._should_stop = True
            
            # Wait for server thread to finish
            if self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)
                if self._server_thread.is_alive():
                    self.logger.warning("Server thread did not stop gracefully")
            
            self._server_thread = None
            self._should_stop = False
            self.logger.info("Stream server stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop stream server: {str(e)}")
            raise RobotError(f"Stream server stop failed: {str(e)}", "stream_server")
