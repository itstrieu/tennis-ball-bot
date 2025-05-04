"""
stream_server.py

FastAPI server for streaming camera feed and providing debug information.
Handles WebSocket connections for real-time video streaming.

This module provides a web interface for:
- Live video streaming from the robot's camera
- Debug information about the robot's state
- Control over the streaming process
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
    
    This class provides:
    - WebSocket-based video streaming
    - Debug information endpoints
    - Stream control endpoints
    - HTML interface for monitoring
    
    Attributes:
        config: RobotConfig instance for configuration values
        camera: CameraManager instance for frame capture
        vision: VisionTracker instance for debug information
        logger: Logger instance for logging operations
        app: FastAPI application instance
        _stream_lock: asyncio.Lock for thread-safe streaming
        _stream_consumers: set of active WebSocket connections
        _server_thread: Thread running the FastAPI server
        _should_stop: Flag for graceful shutdown
    """
    
    def __init__(self, config=None):
        """
        Initialize the StreamServer with optional configuration.
        
        Args:
            config: Optional RobotConfig instance. If None, uses default_config.
        """
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
        """
        Set the required components for streaming.
        
        Args:
            camera: CameraManager instance for frame capture
            vision: Optional VisionTracker instance for debug info
        """
        self.camera = camera
        self.vision = vision

    async def _get_frame(self):
        """
        Get the latest frame from the camera.
        
        Returns:
            Optional[np.ndarray]: The latest camera frame or None if capture fails
            
        Raises:
            RobotError: If camera is not available or frame capture fails
        """
        if not self.camera:
            raise RobotError("Camera not available", "stream_server")
            
        try:
            # Capture frame directly from camera
            frame = self.camera.camera.capture_array()
            if frame is not None:
                return frame
            return None
        except Exception as e:
            self.logger.error(f"Error getting frame: {str(e)}")
            raise RobotError(f"Frame capture failed: {str(e)}", "stream_server")

    def _setup_routes(self):
        """
        Set up FastAPI routes and endpoints.
        
        This method configures:
        - HTML interface for streaming
        - WebSocket endpoint for video frames
        - Debug information endpoint
        - Stream control endpoints
        """
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            """
            Serve the HTML interface for streaming.
            
            Returns:
                HTMLResponse: The streaming interface HTML page
            """
            return """
            <!DOCTYPE html>
            <html>
            <head>
              <title>Tennis Ball Bot • Live Stream</title>
              <style>
                /* Modern, responsive styling for the streaming interface */
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
                // WebSocket connection management
                let ws = null;
                const img = document.getElementById('stream');
                const status = document.getElementById('status');
                
                function connectWebSocket() {
                  // Establish WebSocket connection
                  ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws');
                  ws.binaryType = 'blob';
                  
                  // Handle incoming frames
                  ws.onmessage = e => {
                    const url = URL.createObjectURL(e.data);
                    img.src = url;
                    setTimeout(()=>URL.revokeObjectURL(url),100);
                  };
                  
                  // Connection status handling
                  ws.onopen = () => {
                    status.textContent = 'WebSocket connected';
                    status.style.background = '#e8f5e9';
                    status.style.color = '#2e7d32';
                  };
                  
                  ws.onclose = () => {
                    status.textContent = 'WebSocket disconnected - reconnecting...';
                    status.style.background = '#fff3e0';
                    status.style.color = '#e65100';
                    setTimeout(connectWebSocket, 1000);  // Auto-reconnect
                  };
                  
                  ws.onerror = () => {
                    status.textContent = 'WebSocket error - reconnecting...';
                    status.style.background = '#ffebee';
                    status.style.color = '#c62828';
                    ws.close();  // Force reconnection
                  };
                }
                
                // Initial connection
                connectWebSocket();
                
                // Stream control functions
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
            """
            Return debug information about the robot's state.
            
            Returns:
                dict: Debug information including detections, frame count, and FPS
            """
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
            """
            Start the video stream.
            
            Returns:
                dict: Status of the streaming operation
                
            Raises:
                RobotError: If camera is not available or stream start fails
            """
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
            """
            Stop the video stream.
            
            Returns:
                dict: Status of the streaming operation
                
            Raises:
                RobotError: If stream stop fails
            """
            try:
                await self.camera.stop_streaming()
                return {"status": "stopped"}
            except Exception as e:
                self.logger.error(f"Failed to stop stream: {str(e)}")
                raise RobotError(f"Stream stop failed: {str(e)}", "stream_server")

        @self.app.websocket("/ws")
        @with_error_handling("stream_server")
        async def websocket_endpoint(websocket: WebSocket):
            """
            Handle WebSocket connections for video streaming.
            
            This endpoint:
            1. Accepts WebSocket connections
            2. Sends video frames to connected clients
            3. Handles client disconnection
            4. Manages stream consumer registration
            
            Args:
                websocket: WebSocket connection instance
            """
            await websocket.accept()
            self._stream_consumers.add(websocket)
            
            try:
                while True:
                    # Get latest frame
                    frame = await self._get_frame()
                    if frame is None:
                        continue
                        
                    # Convert frame to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, 
                        [cv2.IMWRITE_JPEG_QUALITY, self.config.streaming_quality])
                    
                    # Send frame to client
                    await websocket.send_bytes(buffer.tobytes())
                    
            except WebSocketDisconnect:
                self._stream_consumers.remove(websocket)
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
                self._stream_consumers.remove(websocket)
                await websocket.close()

    async def start(self):
        """
        Start the streaming server.
        
        This method:
        1. Creates a new thread for the FastAPI server
        2. Configures the server with appropriate settings
        3. Starts the server in the background
        
        Raises:
            RobotError: If server start fails
        """
        if self._server_thread and self._server_thread.is_alive():
            return
            
        try:
            # Configure server settings
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
            
            # Create and start server in new thread
            server = uvicorn.Server(config)
            self._server_thread = threading.Thread(
                target=server.run,
                daemon=True
            )
            self._server_thread.start()
            
            self.logger.info("Streaming server started")
        except Exception as e:
            self.logger.error(f"Failed to start server: {str(e)}")
            raise RobotError(f"Server start failed: {str(e)}", "stream_server")

    def _run_server(self):
        """
        Run the FastAPI server.
        
        This method is called in a separate thread and:
        1. Runs the uvicorn server
        2. Handles server lifecycle
        3. Manages graceful shutdown
        """
        try:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
        except Exception as e:
            self.logger.error(f"Server error: {str(e)}")

    async def stop(self):
        """
        Stop the streaming server.
        
        This method:
        1. Signals the server to stop
        2. Waits for the server thread to finish
        3. Cleans up resources
        
        Raises:
            RobotError: If server stop fails
        """
        try:
            self._should_stop = True
            if self._server_thread:
                self._server_thread.join(timeout=5)
            self.logger.info("Streaming server stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop server: {str(e)}")
            raise RobotError(f"Server stop failed: {str(e)}", "stream_server")
