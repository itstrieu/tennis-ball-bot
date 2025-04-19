import cv2
import threading
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from picamera2 import Picamera2
from src.core.detection.vision_tracker import VisionTracker
from src.config.vision import MODEL_PATH, FRAME_WIDTH
from src.app.camera_manager import get_camera

app = FastAPI()

# Globals
latest_frame = None
lock = threading.Lock()
vision = VisionTracker(model_path=MODEL_PATH, frame_width=FRAME_WIDTH)

# Get camera
camera = get_camera()


# Background capture + detection


def capture_loop():
    global latest_frame
    while True:
        frame = camera.capture_array()
        bboxes = vision.detect_ball(frame)
        for x, y, w, h in bboxes:
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w), int(y + h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        with lock:
            latest_frame = frame


# Start in background
threading.Thread(target=capture_loop, daemon=True).start()


# MJPEG stream generator
def gen():
    while True:
        with lock:
            if latest_frame is None:
                continue
            ret, buffer = cv2.imencode(".jpg", latest_frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
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
    return html_page


@app.get("/stream")
def stream():
    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
