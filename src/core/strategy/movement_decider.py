import logging
from utils.logger import Logger
from config.motion import (
    TARGET_AREA,
    CENTER_THRESHOLD,
)


class MovementDecider:
    def __init__(self, target_area=TARGET_AREA, center_threshold=CENTER_THRESHOLD):
        self.target_area = target_area
        self.center_threshold = center_threshold
        self.no_ball_count = 0
        self.max_no_ball_count = 10  # How many cycles before starting search mode

        # Set up logger
        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide(self, offset, area):
        """
        Simple decision logic:
        1. If ball is large enough, stop (collection successful)
        2. If ball is centered enough, move forward
        3. Otherwise turn to center the ball
        """
        # Reset no ball counter when we see a ball
        self.no_ball_count = 0

        self.logger.debug(f"Offset: {offset}, Area: {area}")

        # Check if ball is close enough to collect
        if area >= self.target_area:
            return "stop"  # Ball collected, stop

        # If ball is reasonably centered, move forward
        if abs(offset) <= self.center_threshold:
            return "forward"

        # Otherwise, turn to center the ball
        if offset < 0:
            return "left"
        else:
            return "right"

    def handle_no_ball(self):
        """Called when no ball is detected"""
        self.no_ball_count += 1

        # If we've gone several frames without seeing a ball, search
        if self.no_ball_count >= self.max_no_ball_count:
            self.no_ball_count = 0  # Reset counter
            return "search"

        # Otherwise just continue with last action
        return None
