# vision.py

# YOLO model path (for local testing)
MODEL_PATH = "models/current_best.pt"

# Confidence threshold for filtering weak detections
CONFIDENCE_THRESHOLD = 0.4

# Expected camera frame width (used for center offset logic)
FRAME_WIDTH = 640

# Offset if the camera is not perfectly centered
CAMERA_OFFSET = 0

# When to stop approaching the ball (in bbox area)
TARGET_AREA = 17000
