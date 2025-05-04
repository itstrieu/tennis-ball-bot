from ultralytics import YOLO
import numpy as np
import logging
import time
from typing import Optional, List
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from contextlib import contextmanager
from config.robot_config import default_config


class YOLOInference:
    """
    YOLO model inference for object detection.
    
    Attributes:
        model_path: Path to the YOLO model file
        model: Loaded YOLO model
        logger: Logger instance
    """
    
    def __init__(self, model_path: str, config=None):
        """
        Loads YOLOv8 model from .pt file.
        
        Args:
            model_path: Path to the YOLO model file
            
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
            results = self.model.predict(frame, verbose=False)[0]
            detections = []

            for box in results.boxes:
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = self.model.names[cls_id]

                # Convert to (x, y, w, h)
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
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        
    @contextmanager
    def inference_context(self):
        """
        Context manager for inference operations.
        
        Usage:
            with yolo.inference_context():
                detections = yolo.predict(frame)
        """
        try:
            yield self
        finally:
            self.cleanup()
