# src/app/robot_controller.py
from utils.logger import Logger
import time
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    SEARCH_ROTATE_DURATION,
    CENTER_ROTATE_SPEED,
    NO_BALL_PAUSE,
    SWITCH_DELAY,
)
from src.app.camera_manager import get_camera


class RobotController:
    """
    RobotController ties together motion, vision, and decision modules,
    looping on camera input and driving the robot accordingly.
    """

    def __init__(self, motion_controller, vision_tracker, movement_decider):
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider

        # Get the shared camera instance
        self.camera = get_camera()  # Get the shared camera instance
        self.vision.set_camera(self.camera)  # Pass the camera instance to VisionTracker

        # Set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

    def run(self):
        """
        Main control loop:
        - capture frame
        - detect tennis balls
        - decide movement
        - execute movement

        Press Ctrl+C to exit.
        """
        self.logger.info("RobotController started. Press Ctrl+C to stop.")
        try:
            self.motion.stop()

            while True:
                frame = self.vision.get_frame()  # Get the frame from the shared camera
                bboxes = self.vision.detect_ball(frame)

                if not bboxes:
                    self.logger.info("❌ No tennis balls detected.")
                    self.motion.stop()
                    time.sleep(NO_BALL_PAUSE)
                    self.logger.info(
                        f"Searching: rotate left @ {SEARCH_ROTATE_SPEED}% for {SEARCH_ROTATE_DURATION}s"
                    )
                    self.motion.rotate_left(
                        speed=SEARCH_ROTATE_SPEED, duration=SEARCH_ROTATE_DURATION
                    )
                    continue

                largest = max(bboxes, key=self.vision.calculate_area)
                offset = self.vision.get_center_offset(largest)
                area = self.vision.calculate_area(largest)
                direction = self.decider.decide(offset, area)

                self.logger.debug(
                    f"Offset: {offset:.2f}, Area: {area:.2f}, Direction: {direction}"
                )
                self._move(direction)

        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received: stopping robot...")
        finally:
            self.motion.stop()
            self.logger.info("RobotController shutdown complete.")

    def _move(self, direction):
        """
        Translate a direction string into a motion_controller call.
        """
        self.motion.stop()
        time.sleep(SWITCH_DELAY)

        if direction == "left":
            self.logger.info(f"Rotating left @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_left(speed=CENTER_ROTATE_SPEED)
        elif direction == "right":
            self.logger.info(f"Rotating right @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_right(speed=CENTER_ROTATE_SPEED)
        elif direction == "forward":
            self.logger.info("Moving forward @ default speed")
            self.motion.move_forward()
        else:
            self.logger.info("Stopping: unknown direction")
            self.motion.stop()
