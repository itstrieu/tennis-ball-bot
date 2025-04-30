"""
movement_decider.py

Contains logic for interpreting ball position and size, and deciding how
the robot should move to approach and center the ball.
"""

import logging
from utils.logger import Logger
from config.motion import TARGET_AREA, CENTER_THRESHOLD, THRESHOLDS


class MovementDecider:
    """
    Determines movement decisions based on object detection data.

    Attributes:
        target_area (int): Target bounding box area threshold to consider the ball 'close enough'.
        center_threshold (int): Pixel offset from center within which the ball is considered 'centered'.
        no_ball_count (int): Counter for how many frames have lacked ball detection.
        last_area (float): Area of the last seen ball.
    """

    def __init__(
        self, target_area=TARGET_AREA, center_threshold=CENTER_THRESHOLD, max_no_ball=3
    ):
        self.target_area = target_area
        self.center_threshold = center_threshold
        self.max_no_ball = max_no_ball
        self.no_ball_count = 0
        self.last_area = 0

        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide(self, offset, area):
        """
        Decide next action based on current detection offset, size ratio, and no-ball history.

        Args:
            offset (float|None): Horizontal distance of ball from center (None if no ball seen).
            area (float): Bounding box area of the ball or last seen ball.

        Returns:
            str: One of the keys in MOVEMENT_STEPS (e.g., 'small_forward', 'micro_left', 'search').
        """
        ratio = area / self.target_area
        self.last_area = area

        # Ball detected this frame
        if offset is not None:
            self.no_ball_count = 0

            # 1) Stop if ball is large enough
            if ratio >= THRESHOLDS["stop"]:
                self.logger.info(f"[DECIDE] stop (ratio={ratio:.2f})")
                return "stop"

            # 2) If centered
            if abs(offset) <= self.center_threshold:
                if ratio >= THRESHOLDS["micro"]:
                    # Ball is close and centered → fine-grained forward
                    self.logger.info(
                        f"[DECIDE] micro_forward (close + centered, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "micro_forward"
                else:
                    # Centered but far → gentle small step forward
                    self.logger.info(
                        f"[DECIDE] small_forward (centered, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "small_forward"

            # 3) If off-center
            if abs(offset) > self.center_threshold:
                if abs(offset) > self.center_threshold * 2:
                    # Far off-center → larger correction
                    choice = "step_left" if offset < 0 else "step_right"
                else:
                    # Slightly off-center → micro correction
                    choice = "micro_left" if offset < 0 else "micro_right"
                self.logger.info(
                    f"[DECIDE] {choice} (off-center, offset={offset}, ratio={ratio:.2f})"
                )
                return choice

        # No ball seen in this frame
        self.no_ball_count += 1

        # 4) If ball was recently close enough → take a confident step forward
        if ratio >= THRESHOLDS["recovery"]:
            self.logger.info(f"[DECIDE] step_forward (last_ratio={ratio:.2f})")
            self.no_ball_count = 0
            return "step_forward"

        # 5) If we've gone too long without detection → start search
        if self.no_ball_count >= self.max_no_ball:
            self.logger.info(f"[DECIDE] search (no_ball_count={self.no_ball_count})")
            self.no_ball_count = 0
            return "search"

        # 6) Otherwise continue scanning
        self.logger.info(
            f"[DECIDE] search (default, no_ball_count={self.no_ball_count})"
        )
        return "search"`