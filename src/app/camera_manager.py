# src/app/camera_manager.py
"""
camera_manager.py

Manages the camera and frame capture operations.
Handles frame updates and provides access to the latest frame.
"""

import asyncio
import logging
import time
from typing import Optional, Set

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput
import numpy as np

from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class CameraManager:
    """
    Manages the camera and frame capture operations.
    Handles frame updates and provides access to the latest frame.
    
    Attributes:
        config: RobotConfig instance for configuration values
        logger: Logger instance
        camera: Picamera2 instance
        _frame_queue: asyncio.Queue for frame updates
        _frame_available: asyncio.Event for frame availability
        _streaming: bool indicating if camera is streaming
        _stream_consumers: set of stream consumers
        _frame_update_task: asyncio.Task for frame updates
        _stream_loop: asyncio event loop for streaming
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger.get_logger(name="camera", log_level=logging.INFO)
        self.camera = None
        self._frame_queue = None
        self._frame_available = None
        self._streaming = False
        self._stream_consumers = set()
        self._frame_update_task = None
        self._stream_loop = None

    async def initialize(self):
        """Initialize the camera and its components."""
        if self.camera is not None:
            return
            
        try:
            # Create new event loop for camera operations
            self._stream_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._stream_loop)
            
            # Initialize camera
            self.camera = Picamera2()
            self.camera.configure(self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                raw={"size": (1536, 864), "format": "SBGGR8"}
            ))
            
            # Create frame queue and event in the correct event loop context
            self._frame_queue = asyncio.Queue(maxsize=1)
            self._frame_available = asyncio.Event()
            
            # Start camera
            self.camera.start()
            self.logger.info("Camera initialized successfully")
            
            # Start frame update task
            self._frame_update_task = asyncio.create_task(self._update_frame())
            self.logger.info("Camera frame update task started")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise RobotError(f"Camera initialization failed: {str(e)}", "camera_manager")

    async def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame from the camera."""
        if not self._frame_queue:
            raise RobotError("Camera not initialized", "camera_manager")
            
        try:
            # Ensure we're in the correct event loop context
            if asyncio.get_event_loop() != self._stream_loop:
                asyncio.set_event_loop(self._stream_loop)
                
            frame = await self._frame_queue.get()
            self._frame_queue.task_done()
            return frame
        except Exception as e:
            raise RobotError(f"Frame capture failed: {str(e)}", "camera_manager")

    async def _update_frame(self):
        """Update the frame queue with the latest frame."""
        try:
            while True:
                if not self._streaming:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Ensure we're in the correct event loop context
                if asyncio.get_event_loop() != self._stream_loop:
                    asyncio.set_event_loop(self._stream_loop)
                    
                # Get frame from camera
                frame = self.camera.capture_array()
                if frame is not None:
                    # Put frame in queue
                    if self._frame_queue.full():
                        await self._frame_queue.get()
                        self._frame_queue.task_done()
                    await self._frame_queue.put(frame)
                    self._frame_available.set()
                    
                await asyncio.sleep(0.001)  # Small sleep to prevent CPU hogging
                
        except Exception as e:
            self.logger.error(f"Frame update task failed: {str(e)}")
            raise RobotError(f"Frame update failed: {str(e)}", "camera_manager")

    async def start_streaming(self):
        """Start camera streaming."""
        if not self._streaming:
            self._streaming = True
            self.logger.info("Camera streaming started")

    async def stop_streaming(self):
        """Stop camera streaming."""
        if self._streaming:
            self._streaming = False
            self.logger.info("Camera streaming stopped")

    async def register_stream_consumer(self):
        """Register a stream consumer."""
        self._stream_consumers.add(asyncio.current_task())
        self.logger.info(f"Stream consumer registered: {len(self._stream_consumers)} active")

    async def unregister_stream_consumer(self):
        """Unregister a stream consumer."""
        self._stream_consumers.discard(asyncio.current_task())
        self.logger.info(f"Stream consumer unregistered: {len(self._stream_consumers)} active")

    async def cleanup(self):
        """Clean up camera resources."""
        try:
            if self._frame_update_task:
                self._frame_update_task.cancel()
                try:
                    await self._frame_update_task
                except asyncio.CancelledError:
                    pass
                    
            if self.camera:
                self.camera.stop()
                self.camera.close()
                
            self._streaming = False
            self._stream_consumers.clear()
            
            if self._stream_loop:
                self._stream_loop.close()
                
            self.logger.info("Camera resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error cleaning up camera: {str(e)}")
            raise RobotError(f"Camera cleanup failed: {str(e)}", "camera_manager")
