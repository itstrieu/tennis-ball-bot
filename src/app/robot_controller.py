"""
robot_controller.py

Main control logic for the robot. Coordinates vision, motion, and decision-making
to perform search-and-retrieve behaviors for tennis balls using a camera feed.
"""

import logging
import time
from utils.logger import Logger
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    CENTER_ROTATE_SPEED,
    SPEED,
)
from src.app.camera_manager import get_camera
from src.config.motion import MOVEMENT_STEPS, DEV_SLOWDOWN


class RobotController:
    """
    Coordinates motion, vision tracking, and decision logic to control the robot's behavior.

    Executes a cyclic process:
    - Rotates to scan surroundings.
    - Waits for ball detection.
    - Approaches and retrieves ball when found.
    - Resumes scanning after completing the retrieval cycle.

    Attributes:
        motion: Motion controller module for moving/rotating the robot.
        vision: Vision module for detecting balls via camera input.
        decider: MovementDecider instance for deciding how to respond to detections.
        dev_mode (bool): Whether development slowdown is active.
    """

    def __init__(self, motion, vision, decider, dev_mode=True):
        self.motion = motion
        self.vision = vision
        self.decider = decider
        self.dev_slowdown = DEV_SLOWDOWN if dev_mode else 1.0

        self.logger = Logger(name="robot", log_level=logging.INFO).get_logger()

    def run(self):
        self.logger.info("Starting control loop (dev_mode=%s)", self.dev_mode)
        last_area = 0

        try:
            while True:
                frame = self.vision.get_frame()
                bboxes = self.vision.detect_ball(frame)

                if bboxes:
                    largest = max(bboxes, key=self.vision.calculate_area)
                    offset = self.vision.get_center_offset(largest)
                    area = self.vision.calculate_area(largest)
                else:
                    offset = None
                    area = last_area

                # Decide & execute
                action = self.decider.decide(offset, area)
                params = MOVEMENT_STEPS[action]

                self.logger.debug(f"[EXECUTE] {action} → {params}")
                getattr(self.motion, params["method"])(speed=params["speed"])
                time.sleep(params["time"] * self.dev_slowdown)
                self.motion.stop()

                last_area = area

        except KeyboardInterrupt:
            self.logger.info("Stopping robot (KeyboardInterrupt).")
        finally:
            self.motion.stop()
            self.logger.info("Control loop ended.")
