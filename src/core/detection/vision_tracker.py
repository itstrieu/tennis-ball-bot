from .yolo_inference import YOLOInference
from src.config import vision as vision_config
from picamera2 import Picamera2


class VisionTracker:
    def __init__(self, model_path, frame_width, camera_offset=0):
        self.model = YOLOInference(model_path)
        self.frame_width = frame_width
        self.camera_offset = camera_offset
        self.conf_threshold = vision_config.CONFIDENCE_THRESHOLD

        # Re-add this if removed
        self.camera = Picamera2()
        self.camera.configure(
            self.camera.create_preview_configuration(
                main={"format": "BGR888", "size": (640, 480)}
            )
        )
        self.camera.start()

    def get_frame(self):
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
