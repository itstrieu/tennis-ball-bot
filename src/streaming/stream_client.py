# stream_client.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import threading
import logging

# Globals (no get_camera() here!)
camera = None
vision = None


def set_shared_components(cam, vision_tracker):
    global camera, vision
    camera = cam
    vision = vision_tracker


app = FastAPI()


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


def gen():
    while True:
        frame = capture_frame()
        if frame is None:
            logging.warning("No frame captured, skipping...")
            continue
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            logging.warning("Failed to encode frame.")
            continue
        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


html_page = """..."""  # keep this part unchanged


@app.get("/", response_class=HTMLResponse)
def index():
    return html_page


@app.get("/stream")
def stream():
    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
