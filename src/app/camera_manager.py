# src/app/camera_manager.py
"""
camera_manager.py

Manages the camera resource and provides access to camera functionality.
Handles initialization, frame capture, and cleanup of camera resources.
"""

import logging
import asyncio
import time
from typing import Optional
from picamera2 import Picamera2
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class CameraManager:
    """
    Manages the camera resource and provides access to camera functionality.
    
    Attributes:
        config: RobotConfig instance for configuration values
        camera: Picamera2 instance
        logger: Logger instance for logging
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger.get_logger(name="camera", log_level=logging.INFO)
        self.camera = None
        self._initialized = False
        self._frame_lock = asyncio.Lock()
        self._frame_buffer = None
        self._frame_available = asyncio.Event()
        self._update_task = None
        self._last_frame_time = 0
        self._frame_interval = 1.0 / self.config.target_fps

    @with_error_handling("camera_manager")
    def initialize(self) -> None:
        """Initialize the camera with configuration."""
        if self.camera is not None:
            self.logger.warning("Camera already initialized")
            return
            
        try:
            self.camera = Picamera2()
            self.camera.configure(
                self.camera.create_video_configuration(
                    main={"format": "BGR888", "size": (self.config.frame_width, 480)}
                )
            )
            self.camera.start()
            self._initialized = True
            self._update_task = asyncio.create_task(self._update_frame())
            self.logger.info("Camera initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise RobotError(f"Camera initialization failed: {str(e)}", "camera_manager")

    async def _update_frame(self):
        """Update the frame buffer in a separate task."""
        while self._initialized:
            try:
                current_time = time.time()
                if current_time - self._last_frame_time < self._frame_interval:
                    await asyncio.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue

                async with self._frame_lock:
                    self._frame_buffer = self.camera.capture_array()
                    self._frame_available.set()
                self._last_frame_time = current_time
                await asyncio.sleep(self._frame_interval)
            except Exception as e:
                self.logger.error(f"Error updating frame: {str(e)}")
                await asyncio.sleep(0.1)

    @with_error_handling("camera_manager")
    async def get_frame(self):
        """Get a frame from the camera with proper synchronization."""
        if not self._initialized:
            self.initialize()
            
        try:
            await self._frame_available.wait()
            async with self._frame_lock:
                frame = self._frame_buffer
                self._frame_available.clear()
                return frame
        except Exception as e:
            self.logger.error(f"Failed to capture frame: {str(e)}")
            raise RobotError(f"Frame capture failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    def cleanup(self) -> None:
        """Clean up camera resources."""
        if self.camera is not None:
            try:
                self._initialized = False
                if self._update_task:
                    self._update_task.cancel()
                self.camera.stop()
                self.camera.close()
                self.camera = None
                self.logger.info("Camera resources cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error during camera cleanup: {str(e)}")
                raise RobotError(f"Camera cleanup failed: {str(e)}", "camera_manager")

    def __del__(self):
        """Ensure camera is cleaned up when object is destroyed."""
        self.cleanup()
