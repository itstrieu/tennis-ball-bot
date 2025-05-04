# src/app/camera_manager.py
"""
camera_manager.py

Manages the camera resource and provides access to camera functionality.
Handles initialization, frame capture, and cleanup of camera resources.
"""

import logging
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
        self.camera: Optional[Picamera2] = None
        self.logger = Logger(name="camera", log_level=logging.INFO).get_logger()

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
            self.logger.info("Camera initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise RobotError(f"Camera initialization failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    def get_frame(self):
        """Get a frame from the camera."""
        if self.camera is None:
            self.initialize()
            
        try:
            return self.camera.capture_array()
        except Exception as e:
            self.logger.error(f"Failed to capture frame: {str(e)}")
            raise RobotError(f"Frame capture failed: {str(e)}", "camera_manager")

    @with_error_handling("camera_manager")
    def cleanup(self) -> None:
        """Clean up camera resources."""
        if self.camera is not None:
            try:
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
