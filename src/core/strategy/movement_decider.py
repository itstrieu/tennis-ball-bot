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
        self.no_ball_count = 0  # Tracks how many consecutive frames had no ball
        self.last_area = 0  # Area of last seen ball
        self.last_seen_valid = (
            False  # True only if the ball was seen in the previous frame
        )

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
        ratio = area / self.target_area if self.target_area > 0 else 0

        # === Case 1: Ball is detected this frame ===
        if offset is not None:
            self.no_ball_count = 0
            self.last_area = area
            self.last_seen_valid = True  # Mark that we just saw the ball

            # 1. Stop if the ball is close enough
            if ratio >= THRESHOLDS["stop"]:
                self.logger.info(f"[DECIDE] stop (ratio={ratio:.2f})")
                return "stop"

            # 2. If centered, move forward (how much depends on distance)
            if abs(offset) <= self.center_threshold:
                if ratio >= THRESHOLDS["micro"]:
                    self.logger.info(
                        f"[DECIDE] micro_forward (centered + close, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "micro_forward"
                else:
                    self.logger.info(
                        f"[DECIDE] small_forward (centered, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "small_forward"

            # 3. If off-center, rotate to center
            if abs(offset) > self.center_threshold:
                if abs(offset) > self.center_threshold * 2:
                    choice = "step_left" if offset < 0 else "step_right"
                else:
                    choice = "micro_left" if offset < 0 else "micro_right"
                self.logger.info(
                    f"[DECIDE] {choice} (off-center, offset={offset:.2f}, ratio={ratio:.2f})"
                )
                return choice

        # === Case 2: No ball detected this frame ===
        self.no_ball_count += 1

        # 4. If we just lost the ball, and it was close, take a single blind step forward
        if (
            self.last_seen_valid
            and self.last_area / self.target_area >= THRESHOLDS["recovery"]
        ):
            self.logger.info(
                f"[DECIDE] step_forward (blind follow-up, last_ratio={self.last_area / self.target_area:.2f})"
            )
            self.last_seen_valid = False  # Prevent repeating this action
            return "step_forward"

        # 5. If we've gone too long without seeing the ball, enter search mode
        if self.no_ball_count >= self.max_no_ball:
            self.logger.info(f"[DECIDE] search (no_ball_count={self.no_ball_count})")
            self.no_ball_count = 0
            self.last_seen_valid = False
            return "search"

        # 6. Otherwise, continue slow scanning/searching
        self.logger.info(
            f"[DECIDE] search (default, no_ball_count={self.no_ball_count})"
        )
        return "search"
