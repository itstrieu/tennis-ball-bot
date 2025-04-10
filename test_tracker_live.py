from picamera2 import Picamera2
from src.core.detection.vision_tracker import VisionTracker
import time

tracker = VisionTracker(
    model_path="models/current_best.pt",
    frame_width=640,
    camera_offset=81
)

cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "BGR888", "size": (640, 480)}))
cam.start()
time.sleep(1)

print("📷 Starting live detection... (Ctrl+C to stop)")

try:
    while True:
        frame = cam.capture_array()
        predictions = tracker.model.predict(frame)

        if not predictions:
            print("❌ No detections at all")
        else:
            for bbox, conf, label in predictions:
                print(f"🧠 Detected: {label} | conf={conf:.2f} | bbox={bbox}")

        time.sleep(0.2)


except KeyboardInterrupt:
    print("\n🛑 Stopped by user")

finally:
    cam.close()
