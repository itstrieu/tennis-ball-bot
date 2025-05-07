"""
stream_server.py

FastAPI server for streaming camera feed and providing debug information.
Handles WebSocket connections for real-time video streaming.

This module provides a web interface for:
- Live video streaming from the robot's camera
- Debug information about the robot's state
- Control over the streaming process
"""

import asyncio
import logging
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import cv2
import numpy as np

from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config
from src.app.robot_controller import RobotController
from src.core.strategy.robot_state import RobotStateMachine
from src.core.detection.vision_tracker import VisionTracker

logger_global = logging.getLogger(__name__)


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
        _server_stopped_event: asyncio.Event for server stop completion
        _executor: ThreadPoolExecutor for thread join
        controller: Optional[RobotController] = None
        state_machine: Optional[RobotStateMachine] = None
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
        self.vision: Optional[VisionTracker] = None
        self.controller: Optional[RobotController] = None
        self.state_machine: Optional[RobotStateMachine] = None
        self.app = FastAPI()
        self._stream_lock = asyncio.Lock()
        self._stream_consumers = set()
        self._server_thread = None
        self._should_stop = False
        self._server_stopped_event = asyncio.Event()
        self._executor = ThreadPoolExecutor(max_workers=1)  # Executor for join
        self._setup_routes()

    def set_components(
        self,
        camera,
        vision: Optional[VisionTracker] = None,
        controller: Optional[RobotController] = None,
    ):
        """
        Set the required components for streaming and status.

        Args:
            camera: CameraManager instance for frame capture
            vision: Optional VisionTracker instance for debug info
            controller: Optional RobotController instance for status info
        """
        self.camera = camera
        self.vision = vision
        self.controller = controller
        if self.controller:
            self.state_machine = getattr(self.controller, "state_machine", None)
            if self.state_machine and not isinstance(
                self.state_machine, RobotStateMachine
            ):
                self.logger.warning(
                    f"Controller provided a state_machine of unexpected type: {type(self.state_machine)}"
                )
                self.state_machine = None

        self.logger.info(
            f"StreamServer components set. Camera: {'Yes' if self.camera else 'No'}, Vision: {'Yes' if self.vision else 'No'}, Controller: {'Yes' if self.controller else 'No'}, StateMachine: {'Yes' if self.state_machine else 'No'}"
        )

    async def _get_frame(self):
        """
        Get the latest frame from the camera.

        Returns:
            Optional[np.ndarray]: The latest camera frame or None if capture fails

        Raises:
            RobotError: If camera is not available or frame capture fails
        """
        if not self.camera:
            raise RobotError(
                "Camera component not set in StreamServer", "stream_server"
            )

        if not hasattr(self.camera, "get_frame"):
            raise RobotError(
                "Camera object does not have get_frame method", "stream_server"
            )

        try:
            frame = await self.camera.get_frame()
            if frame is not None and isinstance(frame, np.ndarray):
                return frame
            elif frame is not None:
                self.logger.warning(
                    f"_get_frame received non-numpy array: {type(frame)}"
                )
                return None
            else:
                return None
        except Exception as e:
            self.logger.error(
                f"Error getting frame via camera.get_frame(): {str(e)}", exc_info=True
            )
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
              <title>Tennis Ball Bot - Live Feed</title>
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <style>
                body {
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  padding: 1em;
                  background-color: #f0f2f5;
                  color: #1c1e21;
                  margin: 0;
                  min-height: 100vh;
                }
                h1 {
                  color: #0b3d91;
                  margin-bottom: 0.5em;
                }
                .container {
                  background-color: #ffffff;
                  padding: 2em;
                  border-radius: 8px;
                  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1), 0 8px 16px rgba(0, 0, 0, 0.1);
                  text-align: center;
                  width: 90%;
                  max-width: 700px;
                }
                #stream {
                  border: 1px solid #ccd0d5;
                  border-radius: 6px;
                  width: 100%;
                  max-width: 640px;
                  height: auto;
                  margin-bottom: 1em;
                  background-color: #000;
                }
                .status-container {
                  margin-top: 1.5em;
                  padding: 1em;
                  background: #e7f3ff;
                  border: 1px solid #b8d6fb;
                  border-radius: 6px;
                  text-align: left;
                }
                .status-container h2 {
                  margin-top: 0;
                  color: #0b3d91;
                  font-size: 1.1em;
                  margin-bottom: 0.5em;
                }
                #decision-log {
                  font-family: monospace;
                  font-size: 1em;
                  color: #333;
                  white-space: pre-wrap;
                  min-height: 4em;
                  background-color: #f0f2f5;
                  padding: 0.5em;
                  border-radius: 4px;
                  border: 1px solid #dddfe2;
                }
                #ws-status {
                    font-size: 0.8em;
                    color: #606770;
                    margin-top: 1em;
                    text-align: center;
                }
              </style>
            </head>
            <body>
              <h1>Tennis Ball Bot - Live Feed</h1>
              <div class="container">
                  <img id="stream" src="" alt="Loading live camera feed..."/>
                  <div id="ws-status">Connecting to stream...</div>
                  
                  <div class="status-container">
                      <h2>Robot Status</h2>
                      <div id="decision-log">Waiting for status...</div>
                  </div>
              </div>
              
              <script>
                const img = document.getElementById('stream');
                const wsStatus = document.getElementById('ws-status');
                const decisionLog = document.getElementById('decision-log');
                let ws = null;

                function connectWebSocket() {
                  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
                  ws.binaryType = 'blob';
                  img.alt = 'Loading live camera feed...';

                  ws.onopen = () => {
                    wsStatus.textContent = 'Stream Connected';
                    wsStatus.style.color = '#31a24c';
                  };

                  ws.onmessage = event => {
                    const url = URL.createObjectURL(event.data);
                    img.src = url;
                    img.alt = 'Live camera feed';
                    img.onload = () => { URL.revokeObjectURL(url); }
                    setTimeout(() => URL.revokeObjectURL(url), 200);
                  };

                  ws.onclose = () => {
                    wsStatus.textContent = 'Stream Disconnected. Retrying...';
                    wsStatus.style.color = '#f02849';
                    img.src = '';
                    img.alt = 'Stream disconnected';
                    setTimeout(connectWebSocket, 2000);
                  };

                  ws.onerror = (error) => {
                    console.error('WebSocket Error:', error);
                    wsStatus.textContent = 'Stream Error. Check console.';
                    wsStatus.style.color = '#f02849';
                    img.src = '';
                    img.alt = 'Stream error';
                    ws.close();
                  };
                }

                async function fetchStatus() {
                    try {
                        const response = await fetch('/status');
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        const data = await response.json();
                        decisionLog.textContent = data.status || 'Status unavailable';
                    } catch (error) {
                        console.error('Error fetching status:', error);
                        decisionLog.textContent = 'Error fetching status...';
                    }
                }

                connectWebSocket();
                
                setInterval(fetchStatus, 1000);
                fetchStatus();
                
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
                    "fps": self.vision.get_fps(),
                }
            except Exception as e:
                self.logger.error(f"Error getting debug info: {str(e)}")
                return {"error": str(e)}

        @self.app.get("/status")
        async def get_status():
            """Return the current status/action of the robot."""
            status_text = "Unknown (Controller / StateMachine unavailable)"
            current_state_name = "N/A"
            last_action_str = "N/A"

            if self.state_machine and isinstance(self.state_machine, RobotStateMachine):
                try:
                    current_state_name = self.state_machine.current_state.name
                    # Safely get last_executed_action from controller
                    if self.controller:
                        last_action_str = getattr(
                            self.controller, "last_executed_action", "N/A"
                        )
                        if (
                            last_action_str is None
                        ):  # Ensure it's not None if attribute exists but is None
                            last_action_str = "N/A"

                    status_text = (
                        f"State: {current_state_name}\nLast Action: {last_action_str}"
                    )
                except AttributeError as e:
                    self.logger.warning(f"Attribute error getting state/action: {e}")
                    status_text = (
                        f"State: {current_state_name}\nLast Action: Error ({e})"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error retrieving status from state machine: {e}"
                    )
                    status_text = "Error retrieving status from state machine"
            elif self.controller and isinstance(self.controller, RobotController):
                # Fallback if only controller is available
                controller_is_running = getattr(self.controller, "is_running", False)
                status_text = f"Controller Status: {'Running' if controller_is_running else 'Stopped'}"

            return {"status": status_text}

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
            self.logger.info(
                f"WebSocket client connected. Total consumers: {len(self._stream_consumers)}"
            )

            try:
                while True:
                    frame = None
                    detections = None

                    # 1. Get latest frame
                    try:
                        frame = await self._get_frame()
                        if frame is None:
                            await asyncio.sleep(0.05)
                            continue
                    except RobotError as e:
                        self.logger.error(f"Stream Error: Failed to get frame: {e}")
                        await asyncio.sleep(0.5)
                        continue
                    except Exception as e:
                        self.logger.exception(
                            "Stream Error: Unexpected error getting frame"
                        )
                        await asyncio.sleep(0.5)
                        continue

                    # 2. Get latest detections (if vision component exists)
                    if self.vision and isinstance(self.vision, VisionTracker):
                        try:
                            detections = await self.vision.detect_ball(frame)
                        except Exception as e:
                            self.logger.warning(
                                f"Could not get detections for current frame: {e}"
                            )
                            detections = None

                    # 3. Annotate frame
                    annotated_frame = frame.copy()
                    if detections:
                        try:
                            for bbox, conf, label in detections:
                                x, y, w, h = map(int, bbox)
                                color = (255, 100, 0)
                                text_color = (255, 255, 255)
                                text = f"{label}: {conf:.2f}"
                                font_scale = 0.5
                                thickness = 1
                                font = cv2.FONT_HERSHEY_SIMPLEX

                                (text_width, text_height), baseline = cv2.getTextSize(
                                    text, font, font_scale, thickness
                                )

                                cv2.rectangle(
                                    annotated_frame,
                                    (x, y - text_height - baseline - 2),
                                    (x + text_width, y),
                                    color,
                                    -1,
                                )

                                cv2.rectangle(
                                    annotated_frame,
                                    (x, y),
                                    (x + w, y + h),
                                    color,
                                    thickness + 1,
                                )

                                cv2.putText(
                                    annotated_frame,
                                    text,
                                    (x, y - baseline),
                                    font,
                                    font_scale,
                                    text_color,
                                    thickness,
                                    cv2.LINE_AA,
                                )
                        except Exception as e:
                            self.logger.error(f"Error drawing detections: {e}")

                    # 4. Encode frame
                    try:
                        is_success, buffer = cv2.imencode(
                            ".jpg",
                            annotated_frame,
                            [
                                cv2.IMWRITE_JPEG_QUALITY,
                                int(self.config.streaming_quality),
                            ],
                        )
                        if not is_success:
                            self.logger.warning("Failed to encode frame to JPEG.")
                            await asyncio.sleep(0.05)
                            continue
                    except Exception as e:
                        self.logger.error(f"Error encoding frame: {e}")
                        await asyncio.sleep(0.05)
                        continue

                    # 5. Send frame
                    try:
                        await websocket.send_bytes(buffer.tobytes())
                    except WebSocketDisconnect:
                        self.logger.info("WebSocket client disconnected during send.")
                        break
                    except Exception as e:
                        self.logger.error(f"Error sending frame over WebSocket: {e}")
                        break

                    # 6. Regulate frame rate
                    await asyncio.sleep(1 / self.config.streaming_fps)

            except WebSocketDisconnect:
                self.logger.info("WebSocket client disconnected (detected by FastAPI).")
            except asyncio.CancelledError:
                self.logger.info("WebSocket handler task cancelled.")
                raise
            except Exception as e:
                self.logger.exception(f"Unhandled WebSocket error: {str(e)}")
            finally:
                if websocket in self._stream_consumers:
                    self._stream_consumers.remove(websocket)
                try:
                    await websocket.close()
                    self.logger.info(
                        f"WebSocket connection explicitly closed. Total consumers: {len(self._stream_consumers)}"
                    )
                except Exception as close_e:
                    self.logger.warning(
                        f"Error closing WebSocket after loop exit: {close_e}"
                    )

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
                self.app, host="127.0.0.1", port=8000, log_level="info"
            )

            # Create and start server in new thread
            server = uvicorn.Server(config)
            self.server = server  # Store the server instance
            self._server_thread = threading.Thread(target=server.run, daemon=True)
            self._server_thread.start()

            # Wait briefly for the server to start up
            await asyncio.sleep(1.0)

            self.logger.info("Streaming server started on 127.0.0.1:8000")
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
            uvicorn.run(self.app, host="127.0.0.1", port=8000, log_level="info")
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
        if not self._server_thread or not self._server_thread.is_alive():
            self.logger.info("Server thread not running or already stopped.")
            self._server_stopped_event.set()  # Ensure event is set if already stopped
            return

        self.logger.info("Attempting to stop streaming server gracefully...")

        # Signal uvicorn to exit (it handles signals internally)
        if hasattr(self, "server") and hasattr(self.server, "handle_exit"):
            self.server.handle_exit(sig=None, frame=None)
        else:
            self.logger.warning("Could not access uvicorn server handle_exit.")
            # As a fallback, setting _should_stop might be checked by ws loop if implemented
            self._should_stop = True

        # Wait for the thread to join without blocking the event loop
        loop = asyncio.get_running_loop()
        join_task = loop.run_in_executor(self._executor, self._server_thread.join, 5.0)

        try:
            await asyncio.wait_for(
                join_task, timeout=6.0
            )  # Wait slightly longer than join timeout
            if self._server_thread.is_alive():
                self.logger.warning("Server thread did not stop within timeout.")
            else:
                self.logger.info("Server thread stopped successfully.")
        except asyncio.TimeoutError:
            self.logger.warning("Timeout waiting for server thread to join.")
        except Exception as e:
            self.logger.error(f"Error waiting for server thread: {e}")
            # Don't raise here, allow cleanup to continue
        finally:
            self._server_thread = None
            self._executor.shutdown(wait=False)  # Shutdown executor used for join
            self._server_stopped_event.set()  # Signal completion
            self.logger.info("Streaming server stop sequence complete.")

    async def wait_for_stop(self, timeout: Optional[float] = None):
        """Wait until the server stop process is complete."""
        await self._server_stopped_event.wait()
