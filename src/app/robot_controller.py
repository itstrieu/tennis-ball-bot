import time
import os
import logging
from utils.logger import Logger
from picamera2 import Picamera2
from src.streaming.visualizer import Visualizer
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    SEARCH_ROTATE_DURATION,
    CENTER_ROTATE_SPEED,
    NO_BALL_PAUSE,
    SWITCH_DELAY,
)


class RobotController:
    """
    RobotController ties together motion, vision, and decision modules,
    looping on camera input and driving the robot accordingly.
    """

    def __init__(self, motion_controller, vision_tracker, movement_decider):
        """
        Initialize controllers, decider, camera, and logger.

        Arguments:
        - motion_controller: instance of MotionController
        - vision_tracker: object with detect_ball(frame) and calculate_area(bbox)
        - movement_decider: object with decide(offset, area)
        """
        # dependencies
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider

        # set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

        # initialize camera
        self.camera = self._init_camera()

    def _init_camera(self):
        """
        Configure and start the Picamera2 preview camera.

        Returns:
            cam (Picamera2): started camera instance
        """
        cam = Picamera2()
        cam.configure(
            cam.create_preview_configuration(
                main={"format": "BGR888", "size": (640, 480)}
            )
        )
        cam.start()
        self.logger.info("Camera initialized (640x480, BGR888)")
        return cam

    def run(self):
        """
        Main control loop:
        - capture frame
        - detect tennis balls
        - overlay & display live inference
        - decide movement
        - execute movement

        Press 'q' in window or Ctrl+C to exit.
        """
        self.logger.info(
            "RobotController started. Press 'q' in window or Ctrl+C to stop."
        )
        try:
            self.motion.stop()

            while True:
                frame = self.camera.capture_array()
                bboxes = self.vision.detect_ball(frame)

                # show live feed with bounding boxes; exit loop if user presses 'q'
                if os.environ.get("DISPLAY"):
                    if not Visualizer.show_frame(frame, bboxes):
                        break

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

                # choose the largest (closest) ball
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
            self.camera.stop()
            Visualizer.cleanup()
            self.logger.info("RobotController shutdown complete.")

    def _move(self, direction):
        """
        Translate a direction string into a motion_controller call.

        Arguments:
        - direction (str): one of 'left', 'right', 'forward', or others to stop
        """
        # brief pause to avoid mixing commands
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
