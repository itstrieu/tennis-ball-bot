from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import threading
import logging

from src.app.camera_manager import get_camera
from src.core.detection.vision_tracker import VisionTracker
from src.config.vision import MODEL_PATH, FRAME_WIDTH

app = FastAPI()

# Globals
latest_frame = None
lock = threading.Lock()

# Get the shared camera instance
camera = get_camera()

# Initialize Vision Tracker with camera access
vision = VisionTracker(model_path=MODEL_PATH, frame_width=FRAME_WIDTH, camera=camera)


def capture_frame():
    """
    Capture a single frame from the camera and process it.
    """
    try:
        frame = camera.capture_array()  # Capture frame
        bboxes = vision.detect_ball(frame)  # Detect balls in the frame
        for x, y, w, h in bboxes:
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w), int(y + h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return frame
    except Exception as e:
        logging.error(f"Error capturing frame: {e}")
        return None


# MJPEG stream generator
def gen():
    """
    Generate MJPEG frames for streaming.
    """
    while True:
        frame = capture_frame()  # Capture a new frame
        if frame is None:
            logging.warning("No frame captured, skipping...")
            continue

        ret, buffer = cv2.imencode(".jpg", frame)  # Encode frame as JPEG
        if not ret:
            logging.warning("Failed to encode frame.")
            continue

        frame_bytes = buffer.tobytes()  # Convert to bytes for streaming
        yield (
            b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


# HTML UI
html_page = """
<html>
<head><title>Live Stream</title></head>
<body>
    <h1>Robot Camera</h1>
    <img src="/stream" width="640" height="480" />
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """
    Simple route to serve HTML for the live stream.
    """
    return html_page


@app.get("/stream")
def stream():
    """
    MJPEG stream route for embedding in a browser or client.
    This route continuously serves the latest frames as a MJPEG stream.
    """
    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
