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
        Decide next action based solely on offset (px), area, and how many frames
        since last detection (internal counter).

        Args:
            offset (float|None): None if no detection this frame.
            area   (float):     latest bbox area, or last known area.

        Returns:
            str: one of MOVEMENT_STEPS keys (e.g. 'step_forward', 'search', etc.).
        """
        ratio = area / self.target_area
        self.last_area = area

        # Ball seen?
        if offset is not None:
            self.no_ball_count = 0

            # 1) Stop if fully in range
            if ratio >= THRESHOLDS["stop"]:
                self.logger.info(f"[DECIDE] stop (ratio={ratio:.2f})")
                return "stop"

            # 2) Centered → micro or small forward (be gentle)
            if abs(offset) <= self.center_threshold:
                if ratio >= THRESHOLDS["micro"]:
                    self.logger.info(
                        f"[DECIDE] micro_forward (ratio={ratio:.2f}, offset={offset})"
                    )
                    return "micro_forward"
                elif ratio >= THRESHOLDS["small"]:
                    self.logger.info(
                        f"[DECIDE] small_forward (ratio={ratio:.2f}, offset={offset})"
                    )
                    return "small_forward"
                else:
                    self.logger.info(
                        f"[DECIDE] micro_forward (default step, offset={offset}, ratio={ratio:.2f})"
                    )
                    return "micro_forward"

            # 3) Off-center → micro by default
            if abs(offset) > self.center_threshold:
                if abs(offset) > self.center_threshold * 2:
                    choice = "step_left" if offset < 0 else "step_right"
                else:
                    choice = "micro_left" if offset < 0 else "micro_right"
                self.logger.info(
                    f"[DECIDE] {choice} (offset={offset}, ratio={ratio:.2f})"
                )
                return choice

            # 4) Off-center → micro or full turn
            if ratio >= THRESHOLDS["small"]:
                choice = "micro_left" if offset < 0 else "micro_right"
            else:
                choice = "step_left" if offset < 0 else "step_right"
            self.logger.info(f"[DECIDE] {choice} (ratio={ratio:.2f}, offset={offset})")
            return choice

        # No ball seen:
        self.no_ball_count += 1

        # 5) Recovery push if it was recently close
        if ratio >= THRESHOLDS["recovery"]:
            self.logger.info(f"[DECIDE] recovery_forward (last_ratio={ratio:.2f})")
            self.no_ball_count = 0
            return "recovery_forward"

        # 6) If we’ve been without a detection long enough → search
        if self.no_ball_count >= self.max_no_ball:
            self.logger.info(f"[DECIDE] search (no_ball_count={self.no_ball_count})")
            self.no_ball_count = 0
            return "search"

        # 7) Otherwise keep searching by stepping
        self.logger.info(
            f"[DECIDE] search (default, no_ball_count={self.no_ball_count})"
        )
        return "search"
