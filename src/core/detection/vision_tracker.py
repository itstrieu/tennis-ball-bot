from .yolo_inference import YOLOInference
from src.config import vision as vision_config


class VisionTracker:
    """
    Handles object detection using a YOLO model and calculates position and size of the target object.
    """

    def __init__(self, model_path, frame_width, camera_offset=0):
        """
        Initialize the YOLO model and tracking parameters.

        Args:
            model_path (str): Path to the trained YOLO model (.pt file).
            frame_width (int): Width of the camera frame (used to calculate offset from center).
            camera_offset (int, optional): Pixel offset for the physical placement of the camera on the robot. Defaults to 0.
        """
        self.model = YOLOInference(model_path)
        self.frame_width = frame_width
        self.camera_offset = camera_offset
        self.conf_threshold = vision_config.CONFIDENCE_THRESHOLD

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
