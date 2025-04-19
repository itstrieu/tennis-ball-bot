import time
import os
import logging
from utils.logger import Logger
from picamera2 import Picamera2
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    SEARCH_ROTATE_DURATION,
    CENTER_ROTATE_SPEED,
    NO_BALL_PAUSE,
    SWITCH_DELAY,
)
from src.app.camera_manager import get_camera, stop_camera
import signal

signal.signal(signal.SIGINT, signal.default_int_handler)


class RobotController:
    ...

    def __init__(self, motion_controller, vision_tracker, movement_decider):
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider
        self.camera = get_camera()

        # set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

        # set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

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
                frame = self.vision.get_frame()
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
            stop_camera()
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
