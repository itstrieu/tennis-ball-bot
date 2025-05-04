# src/core/detection/vision_tracker.py
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
    
    Attributes:
        model: YOLOInference instance for object detection
        frame_width: Width of the camera frame
        camera_offset: Offset of the camera's center
        conf_threshold: Confidence threshold for detections
        camera: Shared camera instance
        logger: Logger instance
    """
    
    def __init__(self, config=None):
        """
        Initialize vision tracker with configuration.
        
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
        
        # Load YOLO model
        try:
            self.model = YOLOInference(self.config.vision_model_path, config=self.config)
            self.logger.info("YOLO model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {str(e)}")
            raise RobotError(f"YOLO model loading failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    def set_camera(self, camera):
        """Set the shared camera instance."""
        if self.model is None:
            raise RobotError("YOLO model not loaded", "vision_tracker")
            
        self.camera = camera
        try:
            # Test camera access
            frame = self.camera.get_frame()
            if frame is None:
                raise RobotError("Failed to capture frame", "vision_tracker")
            self._initialized = True
            self.logger.info("Vision tracker initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize vision tracker: {str(e)}")
            raise RobotError(f"Vision tracker initialization failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    def get_frame(self):
        """
        Capture a frame from the shared camera.
        
        Returns:
            np.ndarray: The captured frame
            
        Raises:
            RobotError: If camera access fails
        """
        if not self._initialized:
            raise RobotError("Vision tracker not initialized", "vision_tracker")
            
        try:
            frame = self.camera.get_frame()
            if frame is None:
                raise RobotError("Failed to capture frame", "vision_tracker")
            return frame
        except Exception as e:
            self.logger.error(f"Error capturing frame: {str(e)}")
            raise RobotError(f"Camera access failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    def detect_ball(self, frame):
        """
        Run YOLO model, filter for 'tennis_ball', return all detected tennis balls' bounding boxes.
        
        Args:
            frame: Input frame to process
            
        Returns:
            List of bounding boxes for detected tennis balls
            
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

            # If no tennis balls are detected, return an empty list
            if not tennis_balls:
                return []

            # Return the list of bounding boxes for tennis balls
            return [bbox for (bbox, conf, label) in tennis_balls]
        except Exception as e:
            self.logger.error(f"Error during ball detection: {str(e)}")
            raise RobotError(f"Ball detection failed: {str(e)}", "vision_tracker")

    @with_error_handling("vision_tracker")
    def calculate_area(self, bbox):
        """
        Calculates the area of the bounding box.
        
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
        """Clean up resources used by the vision tracker."""
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
