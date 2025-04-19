import os
import cv2


class Visualizer:
    WINDOW_NAME = "Live Detection"

    @staticmethod
    def show_frame(frame, bboxes):
        for x, y, w, h in bboxes:
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w), int(y + h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if not os.environ.get("DISPLAY") or (
            os.environ.get("DISPLAY") == ":0" and not os.path.exists("/dev/tty0")
        ):
            print("[Visualizer] Headless mode — skipping preview.")
            return True

        try:
            cv2.imshow(Visualizer.WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return False
        except cv2.error:
            print("[Visualizer] OpenCV error — skipping preview.")
            return True

        return True

    @staticmethod
    def cleanup():
        try:
            cv2.destroyWindow(Visualizer.WINDOW_NAME)
        except cv2.error:
            pass
