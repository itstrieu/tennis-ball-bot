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
        self.max_no_ball_count = 8  # How many cycles before starting search mode
        self.approach_distance = 0  # Tracks approach to adjust step size

        # Set up logger
        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide(self, offset, area):
        """
        Decision logic with cautious approach:
        1. If ball is large enough, stop (collection successful)
        2. If ball is centered enough, move forward with progressively smaller steps
        3. Otherwise turn to center the ball
        """
        # Reset no ball counter when we see a ball
        self.no_ball_count = 0

        # Track approach distance - as area increases, we're closer to the ball
        # This helps determine how cautiously to approach
        self.approach_distance = min(100, int((area / self.target_area) * 100))

        self.logger.debug(
            f"Offset: {offset}, Area: {area}, Approach: {self.approach_distance}%"
        )

        # Check if ball is close enough to collect
        if area >= self.target_area:
            self.approach_distance = 0  # Reset approach tracking
            return "stop"  # Ball collected, stop

        # If we're getting close (over 70% of target area), use micro-steps
        if area > self.target_area * 0.7:
            if abs(offset) <= self.center_threshold:
                return "micro_forward"  # Very small steps when close

        # If ball is reasonably centered, move forward with appropriate step size
        if abs(offset) <= self.center_threshold:
            # If we're very close, use small steps
            if area > self.target_area * 0.5:
                return "small_forward"
            else:
                return "step_forward"  # Normal steps when farther away

        # If we're close but need to turn, use smaller turns
        if area > self.target_area * 0.5:
            if offset < 0:
                return "micro_left"
            else:
                return "micro_right"
        else:
            # Regular turning when farther away
            if offset < 0:
                return "step_left"
            else:
                return "step_right"

    def handle_no_ball(self):
        """Called when no ball is detected"""
        self.no_ball_count += 1

        # If we've gone several frames without seeing a ball, search
        if self.no_ball_count >= self.max_no_ball_count:
            self.no_ball_count = 0  # Reset counter
            return "search"

        # Otherwise just continue with last action
        return None
