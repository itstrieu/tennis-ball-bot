from .yolo_inference import YOLOInference
from src.config import vision as vision_config


class VisionTracker:
    def __init__(self, model_path, frame_width, camera, camera_offset=0):
        """
        Initializes the object detector and stores reference to the shared camera.

        Args:
            model_path (str): Path to YOLO model
            frame_width (int): Width of camera frame for calculating center offset
            camera (Picamera2): Shared camera instance (from camera_manager)
            camera_offset (int): Horizontal offset of camera relative to robot center
        """
        self.model = YOLOInference(model_path)
        self.frame_width = frame_width
        self.camera_offset = camera_offset
        self.conf_threshold = vision_config.CONFIDENCE_THRESHOLD
        self.camera = camera

    def get_frame(self):
        """Capture a frame from the shared Picamera2 instance."""
        return self.camera.capture_array()

    def detect_ball(self, frame):
        """
        Run YOLO object detection and filter predictions to return only tennis balls.

        Args:
            frame (ndarray): BGR image captured from the camera.

        Returns:
            list: Bounding boxes of detected tennis balls in (x, y, w, h) format.
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

        return [bbox for (bbox, conf, label) in tennis_balls]

    def calculate_area(self, bbox):
        """
        Calculate the area of a bounding box.

        Args:
            bbox (tuple): Bounding box in (x, y, w, h) format.

        Returns:
            float: Area of the bounding box.
        """
        x, y, w, h = bbox
        return w * h

    def get_center_offset(self, bbox):
        """
        Calculate horizontal offset of the object from the frame's center.

        Args:
            bbox (tuple): Bounding box in (x, y, w, h) format.

        Returns:
            float: Horizontal offset in pixels. Positive = right of center, Negative = left.
        """
        x, _, w, _ = bbox
        bbox_center_x = x + (w / 2)
        adjusted_center = bbox_center_x - self.camera_offset
        return adjusted_center - (self.frame_width / 2)
