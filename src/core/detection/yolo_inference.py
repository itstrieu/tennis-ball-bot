from ultralytics import YOLO
import numpy as np


class YOLOInference:
    def __init__(self, model_path):
        """
        Loads YOLOv8 model from .pt file.
        """
        self.model_path = model_path
        self.model = self._load_model(model_path)

    def _load_model(self, model_path):
        """
        Load YOLOv8 model using Ultralytics.
        """
        return YOLO(model_path)

    def predict(self, frame):
        """
        Run inference on a frame using YOLOv8.

        Args:
            frame (np.ndarray): Input image in BGR format

        Returns:
            List of (bbox, confidence, label)
                where bbox = (x, y, w, h)
        """
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
