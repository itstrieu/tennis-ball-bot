# src/core/detection/vision_tracker.py
from .yolo_inference import YOLOInference
from src.config import vision as vision_config
from utils.logger import Logger
import logging


class VisionTracker:
    def __init__(self, model_path, frame_width, camera, camera_offset=0):
        """
        Initialize vision tracker with model, camera, and parameters.

        Arguments:
        - model_path: path to the YOLO model
        - frame_width: width of the frame for the camera
        - camera: the shared camera instance
        - camera_offset: offset of the camera's center, default 0
        """
        self.model = YOLOInference(model_path)
        self.frame_width = frame_width
        self.camera_offset = camera_offset
        self.conf_threshold = vision_config.CONFIDENCE_THRESHOLD

        self.camera = camera  # Use the shared camera instance

        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def get_frame(self):
        """
        Capture a frame from the shared camera.
        """
        return self.camera.capture_array()

    def detect_ball(self, frame):
        """
        Run YOLO model, filter for 'tennis_ball', return all detected tennis balls' bounding boxes.
        """
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

    def calculate_area(self, bbox):
        """
        Calculates the area of the bounding box.
        """
        x, y, w, h = bbox
        return w * h

    def get_center_offset(self, bbox):
        """
        Returns how far the object is from the robot's centerline (in pixels).
        Positive → object is to the right of center, negative → left.
        """
        x, _, w, _ = bbox
        bbox_center_x = x + (w / 2)
        adjusted_center = bbox_center_x - self.camera_offset
        return adjusted_center - (self.frame_width / 2)
