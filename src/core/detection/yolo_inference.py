"""
yolo_inference.py

Provides YOLO model inference for object detection.
Handles model loading, prediction, and resource management.

This module provides:
- YOLOv8 model integration
- Object detection inference
- Resource management
- Error handling and logging
"""

from ultralytics import YOLO
import numpy as np
import logging
import time
from typing import Optional, List
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from contextlib import contextmanager
from config.robot_config import default_config
import cv2


class YOLOInference:
    """
    YOLO model inference for object detection.
    
    This class provides:
    - YOLOv8 model loading and management
    - Object detection inference
    - Resource cleanup
    - Context management
    
    The inference process:
    1. Loads YOLOv8 model from file
    2. Processes input frames
    3. Returns detections with bounding boxes
    4. Manages model resources
    
    Attributes:
        model_path: Path to the YOLO model file
        model: Loaded YOLO model
        logger: Logger instance
        _initialized: Whether the model is initialized
    """
    
    def __init__(self, model_path: str, config=None):
        """
        Loads YOLOv8 model from .pt file.
        
        This method:
        1. Sets up configuration
        2. Initializes logging
        3. Loads YOLO model
        4. Handles errors
        
        Args:
            model_path: Path to the YOLO model file
            config: Optional RobotConfig instance
            
        Raises:
            RobotError: If model loading fails
        """
        self.config = config or default_config
        self.logger = Logger.get_logger(name="yolo", log_level=logging.INFO)
        self.model_path = model_path
        self.model = None
        self._initialized = False
        
        try:
            self.model = self._load_model(model_path)
            self._initialized = True
            self.logger.info("YOLO model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {str(e)}")
            raise RobotError(f"Model loading failed: {str(e)}", "yolo_inference")

    @with_error_handling("yolo_inference")
    def _load_model(self, model_path):
        """
        Load YOLOv8 model using Ultralytics.
        
        This method:
        1. Attempts to load model
        2. Handles loading errors
        3. Returns loaded model
        
        Args:
            model_path: Path to the YOLO model file
            
        Returns:
            YOLO: Loaded YOLO model
            
        Raises:
            RobotError: If model loading fails
        """
        try:
            return YOLO(model_path)
        except Exception as e:
            self.logger.error(f"Error loading YOLO model: {str(e)}")
            raise RobotError(f"Model loading failed: {str(e)}", "yolo_inference")

    @with_error_handling("yolo_inference")
    def predict(self, frame):
        """
        Run inference on a frame using YOLOv8.

        This method:
        1. Validates initialization
        2. Runs model prediction
        3. Processes detection results
        4. Returns formatted detections
        
        Args:
            frame (np.ndarray): Input image in BGR format

        Returns:
            List of (bbox, confidence, label)
                where bbox = (x, y, w, h)
                
        Raises:
            RobotError: If inference fails
        """
        if not self._initialized:
            raise RobotError("YOLO model not initialized", "yolo_inference")
            
        try:
            # Run YOLO prediction
            results = self.model.predict(frame, verbose=False)[0]
            detections = []

            # Process each detection
            for box in results.boxes:
                # Extract confidence and class
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = self.model.names[cls_id]

                # Convert bounding box format
                x1, y1, x2, y2 = box.xyxy[0]
                x, y = float(x1), float(y1)
                w, h = float(x2 - x1), float(y2 - y1)

                bbox = (x, y, w, h)
                detections.append((bbox, conf, label))

            return detections
        except Exception as e:
            self.logger.error(f"Error during YOLO inference: {str(e)}")
            raise RobotError(f"Inference failed: {str(e)}", "yolo_inference")
            
    @with_error_handling("yolo_inference")
    def cleanup(self):
        """
        Clean up resources used by the YOLO model.
        
        This method:
        1. Checks if the model is initialized
        2. Clears the model from memory
        3. Resets the initialization state
        4. Logs the cleanup status
        
        Raises:
            RobotError: If cleanup fails
        """
        if not self._initialized:
            self.logger.debug("YOLO model already cleaned up")
            return
            
        try:
            # Clear model from memory
            if hasattr(self, 'model'):
                del self.model
            self._initialized = False
            self.logger.info("YOLO model cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during YOLO cleanup: {str(e)}")
            raise RobotError(f"Cleanup failed: {str(e)}", "yolo_inference")
            
    def __enter__(self):
        """
        Context manager entry.
        
        Returns:
            YOLOInference: This instance
        """
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - ensures cleanup.
        
        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self.cleanup()
        
    @contextmanager
    def inference_context(self):
        """
        Context manager for inference operations.
        
        This method:
        1. Yields the YOLO instance
        2. Ensures cleanup on exit
        
        Usage:
            with yolo.inference_context():
                detections = yolo.predict(frame)
        """
        try:
            yield self
        finally:
            self.cleanup()
