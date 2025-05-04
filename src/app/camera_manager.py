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
    Implements a frame streaming architecture with proper synchronization.
    
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
        self._streaming = False
        self._stream_consumers = set()
        # Create a new event loop for this instance
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # Create the event in the correct loop
        self._frame_available = asyncio.Event(loop=self._loop)

    @with_error_handling("camera_manager")
    def start(self) -> None:
        """Start the camera manager synchronously."""
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
            self.logger.info("Camera initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise RobotError(f"Camera initialization failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    async def initialize(self) -> None:
        """Initialize the camera with configuration asynchronously."""
        if not self._initialized:
            self.start()
            
        try:
            self._update_task = asyncio.get_event_loop().create_task(self._update_frame())
            self.logger.info("Camera frame update task started")
        except Exception as e:
            self.logger.error(f"Failed to start frame update task: {str(e)}")
            raise RobotError(f"Frame update task failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    async def get_frame(self):
        """Get a frame from the camera with proper synchronization."""
        if not self._initialized:
            self.start()
            
        try:
            # Ensure we're using the correct event loop
            if asyncio.get_event_loop() != self._loop:
                asyncio.set_event_loop(self._loop)
            
            await self._frame_available.wait()
            async with self._frame_lock:
                frame = self._frame_buffer
                self._frame_available.clear()
                return frame
        except Exception as e:
            self.logger.error(f"Failed to capture frame: {str(e)}")
            raise RobotError(f"Frame capture failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    async def _update_frame(self):
        """Update the frame buffer in a separate task with proper synchronization."""
        while self._initialized:
            try:
                # Ensure we're using the correct event loop
                if asyncio.get_event_loop() != self._loop:
                    asyncio.set_event_loop(self._loop)
                
                current_time = time.time()
                if current_time - self._last_frame_time < self._frame_interval:
                    await asyncio.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue

                # Capture new frame
                frame = self.camera.capture_array()
                
                # Update frame buffer with proper synchronization
                async with self._frame_lock:
                    self._frame_buffer = frame
                    self._frame_available.set()
                
                self._last_frame_time = current_time
                await asyncio.sleep(self._frame_interval)
            except Exception as e:
                self.logger.error(f"Error updating frame: {str(e)}")
                await asyncio.sleep(0.1)

    @with_error_handling("camera_manager")
    async def start_streaming(self):
        """Start the streaming mode."""
        self._streaming = True
        self.logger.info("Camera streaming started")

    @with_error_handling("camera_manager")
    async def stop_streaming(self):
        """Stop the streaming mode."""
        self._streaming = False
        self.logger.info("Camera streaming stopped")

    @with_error_handling("camera_manager")
    async def register_stream_consumer(self):
        """Register a new stream consumer."""
        consumer_id = id(asyncio.current_task())
        self._stream_consumers.add(consumer_id)
        return self._stream_consumers

    @with_error_handling("camera_manager")
    async def unregister_stream_consumer(self):
        """Unregister a stream consumer."""
        consumer_id = id(asyncio.current_task())
        self._stream_consumers.discard(consumer_id)

    @with_error_handling("camera_manager")
    def cleanup(self) -> None:
        """Clean up camera resources."""
        if self.camera is not None:
            try:
                self._initialized = False
                self._streaming = False
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
