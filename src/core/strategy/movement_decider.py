"""
movement_decider.py

Contains logic for interpreting ball position and size, and deciding how
the robot should move to approach and center the ball.
"""

import logging
from utils.logger import Logger
from config.motion import (
    TARGET_AREA,
    CENTER_THRESHOLD,
)


class MovementDecider:
    """
    Determines movement decisions based on object detection data.

    Attributes:
        target_area (int): Target bounding box area threshold to consider the ball 'close enough'.
        center_threshold (int): Pixel offset from center within which the ball is considered 'centered'.
        no_ball_count (int): Counter for how many frames have lacked ball detection.
        last_area (float): Area of the last seen ball.
    """

    def __init__(self, target_area=TARGET_AREA, center_threshold=CENTER_THRESHOLD):
        self.target_area = target_area
        self.center_threshold = center_threshold
        self.no_ball_count = 0
        self.max_no_ball_count = 2
        self.approach_distance = 0
        self.last_area = 0

        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide(self, offset, area):
        """
        Decide the next movement direction based on bounding box offset and area.

        Args:
            offset (float): Horizontal distance of ball center from camera center (pixels).
            area (float): Bounding box area of the detected ball.

        Returns:
            str: Movement command such as 'step_forward', 'micro_left', or 'stop'.
        """
        self.last_area = area

        if area > self.target_area * 0.2:
            self.no_ball_count = 0

        self.approach_distance = min(100, int((area / self.target_area) * 100))

        self.logger.debug(
            f"Offset: {offset}, Area: {area}, Approach: {self.approach_distance}%"
        )

        if area >= self.target_area:
            self.logger.info(
                f"[Decision] Stop — Ball close enough. Offset: {offset}, Area: {area}"
            )
            self.approach_distance = 0
            return "stop"

        if area > self.target_area * 0.7:
            if abs(offset) <= self.center_threshold:
                self.logger.info(
                    f"[Decision] Micro forward — Very close and centered. Offset: {offset}, Area: {area}"
                )
                return "micro_forward"

        if abs(offset) <= self.center_threshold:
            if area > self.target_area * 0.5:
                self.logger.info(
                    f"[Decision] Small forward — Centered and close. Offset: {offset}, Area: {area}"
                )
                return "small_forward"
            else:
                self.logger.info(
                    f"[Decision] Step forward — Centered and far. Offset: {offset}, Area: {area}"
                )
                return "step_forward"

        if area > self.target_area * 0.5:
            if offset < 0:
                self.logger.info(
                    f"[Decision] Micro left — Slightly left and close. Offset: {offset}, Area: {area}"
                )
                return "micro_left"
            else:
                self.logger.info(
                    f"[Decision] Micro right — Slightly right and close. Offset: {offset}, Area: {area}"
                )
                return "micro_right"
        else:
            if offset < 0:
                self.logger.info(
                    f"[Decision] Step left — Left and far. Offset: {offset}, Area: {area}"
                )
                return "step_left"
            else:
                self.logger.info(
                    f"[Decision] Step right — Right and far. Offset: {offset}, Area: {area}"
                )
                return "step_right"

    def handle_no_ball(self):
        self.no_ball_count += 1

        if self.last_area > self.target_area * 0.8:
            self.logger.info(
                "Ball likely close but below camera — committing to final forward."
            )
            self.last_area = 0  # Reset after using it
            self.no_ball_count = 0
            return "final_forward"

        if self.no_ball_count >= self.max_no_ball_count:
            self.logger.info("No ball seen for multiple frames — initiating search.")
            self.no_ball_count = 0
            return "search"

        self.logger.info("No ball seen — small forward.")
        return "micro_forward"
