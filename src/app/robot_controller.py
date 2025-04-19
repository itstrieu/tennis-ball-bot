import time
from picamera2 import Picamera2
from src.config import demo as demo_config  # Import the config


class RobotController:
    def __init__(self, motion_controller, vision_tracker, movement_decider):
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider
        self.camera = self._init_camera()

    def _init_camera(self):
        cam = Picamera2()
        cam.configure(
            cam.create_preview_configuration(
                main={"format": "BGR888", "size": (640, 480)}
            )
        )
        cam.start()
        return cam

    def run(self):
        speed = demo_config.SPEED
        print("RobotController started. Press Ctrl+C to stop.")
        try:
            last_direction = None  # Track the last movement direction
            self.motion.stop()  # Ensure motors are stopped initially

            while True:
                frame = self.camera.capture_array()

                # Get all detected tennis balls in the current frame
                bboxes = self.vision.detect_ball(frame)

                if not bboxes:
                    print("❌ No tennis balls detected.")
                    self.motion.stop()
                    time.sleep(0.5)
                    self.motion.rotate_left(speed=int(speed * 0.65))
                    time.sleep(1)
                    self.motion.stop()  # Stop the robot when no ball is detected
                    continue  # Skip the rest of the loop and wait for ball detection again

                # Sort the detected balls by area (largest area first)
                bboxes_sorted = sorted(
                    bboxes,
                    key=lambda bbox: self.vision.calculate_area(bbox),
                    reverse=True,
                )

                # Pick the largest tennis ball (closest)
                largest_bbox = bboxes_sorted[0]
                offset = self.vision.get_center_offset(largest_bbox)
                area = self.vision.calculate_area(largest_bbox)

                # Decide on the movement based on the largest ball
                direction = self.decider.decide(offset, area)
                print(
                    f"[DEBUG] Offset: {offset:.2f}, Area: {area:.2f}, Direction: {direction}"
                )
                self._move(direction)

        except KeyboardInterrupt:
            print("Stopping robot...")

        finally:
            self.motion.stop()
            self.camera.stop()

    def _move(self, direction):
        """
        Converts direction decisions into motor actions.
        """
        speed = demo_config.SPEED  # Get speed from the config file

        # Stop briefly before switching directions
        self.motion.stop()
        time.sleep(0.05)  # try increasing this if needed

        if direction == "left":
            self.motion.rotate_left(speed=int(speed * 0.7))
        elif direction == "right":
            self.motion.rotate_right(speed=int(speed * 0.7))
        elif direction == "forward":
            self.motion.move_forward(speed=speed)
        else:
            self.motion.stop()
