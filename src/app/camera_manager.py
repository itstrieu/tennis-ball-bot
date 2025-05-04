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
import threading
import queue

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
    
    This class provides a high-level interface for camera operations, including:
    - Camera initialization and configuration
    - Frame capture and management
    - Streaming control
    - Resource cleanup
    
    Attributes:
        config: RobotConfig instance for configuration values
        logger: Logger instance for logging operations
        camera: Picamera2 instance for camera control
        _frame_queue: asyncio.Queue for storing the latest frame
        _frame_available: asyncio.Event to signal frame availability
        _streaming: bool indicating if camera is streaming
        _stream_consumers: set of active stream consumers
        _frame_update_task: asyncio.Task for continuous frame updates
        _stream_loop: asyncio event loop for streaming operations
    """
    
    def __init__(self, config=None):
        """
        Initialize the CameraManager with optional configuration.
        
        Args:
            config: Optional RobotConfig instance. If None, uses default_config.
        """
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
        """
        Initialize the camera and its components.
        
        This method:
        1. Creates and configures the Picamera2 instance
        2. Sets up the frame queue and availability event
        3. Starts the camera
        4. Launches the frame update task
        
        Raises:
            RobotError: If camera initialization fails
        """
        if self.camera is not None:
            return
            
        try:
            # Initialize camera with preview configuration
            self.camera = Picamera2()
            self.camera.configure(self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"},  # Main stream resolution
                raw={"size": (1536, 864), "format": "SBGGR8"}   # Raw stream for higher quality
            ))
            
            # Create frame queue and event for frame management
            self._frame_queue = asyncio.Queue(maxsize=1)  # Store only latest frame
            self._frame_available = asyncio.Event()
            
            # Start camera capture
            self.camera.start()
            self.logger.info("Camera initialized successfully")
            
            # Start continuous frame update task
            self._frame_update_task = asyncio.create_task(self._update_frame())
            self.logger.info("Camera frame update task started")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise RobotError(f"Camera initialization failed: {str(e)}", "camera_manager")

    async def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest frame from the camera.
        
        Returns:
            Optional[np.ndarray]: The latest camera frame or None if capture fails
            
        Raises:
            RobotError: If camera is not initialized or frame capture fails
        """
        if not self._frame_queue:
            raise RobotError("Camera not initialized", "camera_manager")
            
        try:
            # Capture frame directly from camera
            frame = self.camera.capture_array()
            if frame is not None:
                return frame
            return None
        except Exception as e:
            raise RobotError(f"Frame capture failed: {str(e)}", "camera_manager")

    async def _update_frame(self):
        """
        Continuously update the frame queue with the latest frame.
        
        This method runs in a separate task and:
        1. Captures frames from the camera
        2. Updates the frame queue
        3. Signals frame availability
        4. Handles queue overflow
        
        Raises:
            RobotError: If frame update task fails
        """
        try:
            while True:
                if not self._streaming:
                    await asyncio.sleep(0.1)  # Reduce CPU usage when not streaming
                    continue
                    
                # Capture new frame
                frame = self.camera.capture_array()
                if frame is not None:
                    # Update frame queue
                    try:
                        if self._frame_queue.full():
                            await self._frame_queue.get()  # Remove old frame
                            self._frame_queue.task_done()
                        await self._frame_queue.put(frame)  # Add new frame
                        self._frame_available.set()  # Signal frame availability
                    except Exception as e:
                        self.logger.error(f"Error updating frame queue: {str(e)}")
                    
                await asyncio.sleep(0.001)  # Prevent CPU hogging
                
        except Exception as e:
            self.logger.error(f"Frame update task failed: {str(e)}")
            raise RobotError(f"Frame update failed: {str(e)}", "camera_manager")

    async def start_streaming(self):
        """
        Start camera streaming.
        
        This method enables the frame update task to begin capturing
        and updating frames in the queue.
        """
        if not self._streaming:
            self._streaming = True
            self.logger.info("Camera streaming started")

    async def stop_streaming(self):
        """
        Stop camera streaming.
        
        This method disables the frame update task from capturing
        new frames, but maintains the existing frame in the queue.
        """
        if self._streaming:
            self._streaming = False
            self.logger.info("Camera streaming stopped")

    async def register_stream_consumer(self):
        """
        Register a new stream consumer.
        
        This method tracks active stream consumers to manage
        streaming resources efficiently.
        """
        self._stream_consumers.add(asyncio.current_task())
        self.logger.info(f"Stream consumer registered: {len(self._stream_consumers)} active")

    async def unregister_stream_consumer(self):
        """
        Unregister a stream consumer.
        
        This method removes a consumer from the tracking set
        when it no longer needs streaming access.
        """
        self._stream_consumers.discard(asyncio.current_task())
        self.logger.info(f"Stream consumer unregistered: {len(self._stream_consumers)} active")

    async def cleanup(self):
        """
        Clean up camera resources.
        
        This method:
        1. Cancels the frame update task
        2. Stops and closes the camera
        3. Clears all internal state
        
        Raises:
            RobotError: If cleanup fails
        """
        try:
            # Cancel frame update task
            if self._frame_update_task:
                self._frame_update_task.cancel()
                try:
                    await self._frame_update_task
                except asyncio.CancelledError:
                    pass
                
            # Stop and close camera
            if self.camera:
                self.camera.stop()
                self.camera.close()
                
            # Clear all state
            self._frame_queue = None
            self._frame_available = None
            self._streaming = False
            self._stream_consumers.clear()
            self._frame_update_task = None
            self._stream_loop = None
            
            self.logger.info("Camera cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during camera cleanup: {str(e)}")
            raise RobotError(f"Camera cleanup failed: {str(e)}", "camera_manager")
