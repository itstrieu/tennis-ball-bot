from .yolo_inference import YOLOInference
from src.config import vision as vision_config


class VisionTracker:
    def __init__(self, model_path, frame_width, camera=None, camera_offset=0):
        self.model = YOLOInference(model_path)
        self.frame_width = frame_width
        self.camera_offset = camera_offset
        self.conf_threshold = vision_config.CONFIDENCE_THRESHOLD

        # Use the camera passed into the constructor (default is None)
        self.camera = camera

    def set_camera(self, camera):
        self.camera = camera  # Set the camera if it is passed after initialization

    def get_frame(self):
        """
        Capture a frame from the camera.
        """
        return self.camera.capture_array()

    def detect_ball(self, frame):
        """
        Run YOLO model, filter for 'tennis ball', return all detected tennis balls' bounding boxes.
        """
        predictions = self.model.predict(frame)

        # Extract only tennis balls and filter based on confidence threshold
        tennis_balls = [
            (bbox, conf, label)
            for (bbox, conf, label) in predictions
            if label.lower() == "tennis_ball" and conf >= self.conf_threshold
        ]

        print(f"[DEBUG] Raw predictions: {len(predictions)}")
        print(f"[DEBUG] Tennis balls found: {len(tennis_balls)}")

        # If no tennis balls are detected, return an empty list
        if not tennis_balls:
            return []

        # Return the list of bounding boxes for tennis balls
        return [bbox for (bbox, conf, label) in tennis_balls]
