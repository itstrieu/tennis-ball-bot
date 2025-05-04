# src/core/detection/vision_tracker.py
"""
vision_tracker.py

Handles tennis ball detection and tracking using YOLO model and camera input.
Provides real-time ball detection and position analysis.

This module provides:
- YOLO model integration for object detection
- Camera frame capture and processing
- Ball position and size analysis
- Error handling and logging
"""

from .yolo_inference import YOLOInference
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config
import logging
import time
from typing import Optional, Tuple
from src.app.camera_manager import CameraManager


class VisionTracker:
    """
    Tracks tennis balls using YOLO model and camera input.
    
    This class provides:
    - Real-time ball detection using YOLO
    - Frame capture and processing
    - Ball position and size analysis
    - Error handling and logging
    
    The tracker implements the following workflow:
    1. Initializes YOLO model and camera
    2. Captures frames from camera
    3. Processes frames through YOLO model
    4. Filters detections for tennis balls
    5. Analyzes ball position and size
    
    Attributes:
        model: YOLOInference instance for object detection
        frame_width: Width of the camera frame
        camera_offset: Offset of the camera's center
        conf_threshold: Confidence threshold for detections
        camera: Shared camera instance
        logger: Logger instance
        _initialized: Whether the tracker is initialized
    """
    
    def __init__(self, config=None):
        """
        Initialize vision tracker with configuration.
        
        This method:
        1. Sets up configuration
        2. Initializes logging
        3. Sets default values
        
        Args:
            config: Optional RobotConfig instance
        """
        self.config = config or default_config
        self.logger = Logger.get_logger(name="vision", log_level=logging.INFO)
        self.camera = None
        self.model = None
        self._initialized = False
        self.frame_width = self.config.frame_width
        self.camera_offset = self.config.camera_offset
        self.conf_threshold = self.config.confidence_threshold

    async def initialize(self):
        """
        Initialize the vision tracker components.
        
        This method:
        1. Loads YOLO model
        2. Sets initialization flag
        3. Handles errors
        
        Raises:
            RobotError: If initialization fails
        """
        try:
            # Load YOLO model
            self.model = YOLOInference(self.config.vision_model_path, config=self.config)
            self.logger.info("YOLO model loaded successfully")
            self._initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize vision tracker: {str(e)}")
            raise RobotError(f"Vision tracker initialization failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    async def set_camera(self, camera):
        """
        Set the shared camera instance.
        
        This method:
        1. Validates YOLO model
        2. Tests camera access
        3. Sets initialization flag
        
        Args:
            camera: CameraManager instance
            
        Raises:
            RobotError: If camera setup fails
        """
        if self.model is None:
            raise RobotError("YOLO model not loaded", "vision_tracker")
            
        self.camera = camera
        try:
            # Test camera access
            frame = await self.camera.get_frame()
            if frame is None:
                raise RobotError("Failed to capture frame", "vision_tracker")
            self._initialized = True
            self.logger.info("Vision tracker initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize vision tracker: {str(e)}")
            raise RobotError(f"Vision tracker initialization failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    async def get_frame(self):
        """
        Capture a frame from the shared camera.
        
        This method:
        1. Validates initialization
        2. Captures frame
        3. Handles errors
        
        Returns:
            np.ndarray: The captured frame
            
        Raises:
            RobotError: If camera access fails
        """
        if not self._initialized:
            raise RobotError("Vision tracker not initialized", "vision_tracker")
            
        try:
            frame = await self.camera.get_frame()
            if frame is None:
                raise RobotError("Failed to capture frame", "vision_tracker")
            return frame
        except Exception as e:
            self.logger.error(f"Error capturing frame: {str(e)}")
            raise RobotError(f"Camera access failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    async def detect_ball(self, frame):
        """
        Run YOLO model, filter for 'tennis_ball', return all detected tennis balls' bounding boxes.
        
        This method:
        1. Validates initialization
        2. Runs YOLO prediction
        3. Filters tennis ball detections
        4. Applies confidence threshold
        5. Returns bounding boxes
        
        Args:
            frame: Input frame to process
            
        Returns:
            List[Tuple[float, float, float, float]]: List of bounding boxes (x, y, w, h) for detected tennis balls,
                                                    or None if no balls detected
            
        Raises:
            RobotError: If detection fails
        """
        if not self._initialized:
            raise RobotError("Vision tracker not initialized", "vision_tracker")
            
        try:
            predictions = self.model.predict(frame)

            # Extract only tennis balls and filter based on confidence threshold
            tennis_balls = [
                (bbox, conf, label)
                for (bbox, conf, label) in predictions
                if label.lower() == "tennis_ball" and conf >= self.conf_threshold
            ]

            self.logger.debug(f"[DEBUG] Raw predictions: {len(predictions)}")
            self.logger.debug(f"[DEBUG] Tennis balls found: {len(tennis_balls)}")

            # If no tennis balls are detected, return None
            if not tennis_balls:
                return None

            # Return the list of bounding boxes for tennis balls
            return [bbox for (bbox, conf, label) in tennis_balls]
        except Exception as e:
            self.logger.error(f"Error during ball detection: {str(e)}")
            raise RobotError(f"Ball detection failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    def calculate_area(self, bbox):
        """
        Calculates the area of the bounding box.
        
        This method:
        1. Extracts width and height
        2. Calculates area
        
        Args:
            bbox: Bounding box tuple (x, y, w, h)
            
        Returns:
            float: Area of the bounding box
        """
        x, y, w, h = bbox
        return w * h

    @with_error_handling("vision_tracker")
    def get_center_offset(self, bbox):
        """
        Returns how far the object is from the robot's centerline (in pixels).
        Positive → object is to the right of center, negative → left.
        
        This method:
        1. Calculates bounding box center
        2. Adjusts for camera offset
        3. Computes offset from frame center
        
        Args:
            bbox: Bounding box tuple (x, y, w, h)
            
        Returns:
            float: Offset from center in pixels
        """
        x, _, w, _ = bbox
        bbox_center_x = x + (w / 2)
        adjusted_center = bbox_center_x - self.camera_offset
        return adjusted_center - (self.frame_width / 2)
        
    @with_error_handling("vision_tracker")
    def cleanup(self):
        """
        Clean up resources used by the vision tracker.
        
        This method:
        1. Validates initialization
        2. Cleans up model resources
        3. Resets initialization flag
        
        Raises:
            RobotError: If cleanup fails
        """
        if not self._initialized:
            return
            
        try:
            if hasattr(self.model, 'cleanup'):
                self.model.cleanup()
            self._initialized = False
            self.logger.info("Vision tracker cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during vision tracker cleanup: {str(e)}")
            raise RobotError(f"Vision tracker cleanup failed: {str(e)}", "vision_tracker")
