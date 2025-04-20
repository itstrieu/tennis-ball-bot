import logging
import time
from utils.logger import Logger
from config.motion import (
    TARGET_AREA,
    CENTER_THRESHOLD,
)


class MovementDecider:
    def __init__(self, target_area=TARGET_AREA, center_threshold=CENTER_THRESHOLD):
        self.target_area = target_area
        self.center_threshold = center_threshold
        self.last_direction = None
        self.same_direction_count = 0
        self.last_ball_time = time.time()
        self.scan_interval = 5.0  # Time before starting to scan for new balls (seconds)
        self.forward_steps = (
            0  # Count forward movements to limit continuous forward motion
        )
        self.max_forward_steps = 3  # Maximum consecutive forward movements
        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide_direction(self, center_offset):
        # Use the center threshold from config (800px based on your settings)
        if abs(center_offset) > self.center_threshold:
            if center_offset < 0:
                return "left"
            else:
                return "right"
        else:
            return "center"

    def decide_distance_action(self, area):
        if area >= self.target_area:
            return "stop"
        else:
            return "move"

    def decide(self, offset, area):
        # Update last ball detection time
        self.last_ball_time = time.time()

        direction = self.decide_direction(offset)
        distance_action = self.decide_distance_action(area)

        self.logger.debug(
            f"Offset: {offset}, Area: {area}, Direction: {direction}, Distance Action: {distance_action}"
        )

        # First check if we've reached the target
        if distance_action == "stop":
            self.last_direction = "stop"
            self.same_direction_count = 0
            self.forward_steps = 0
            return "stop"

        # Check cautious movement patterns
        current_decision = None

        # If we're well within center threshold (less than half), go forward
        if abs(offset) < self.center_threshold / 2:
            # Reset turning counts when we start going forward
            if self.last_direction != "forward":
                self.forward_steps = 0

            # Increment forward step counter to limit continuous forward movement
            self.forward_steps += 1

            # If we've gone forward too many times, scan for other balls
            if self.forward_steps >= self.max_forward_steps:
                self.forward_steps = 0
                current_decision = (
                    "scan"  # Scan for other balls instead of going forward
                )
            else:
                current_decision = "forward"
        # If we're somewhat off-center but still within threshold, use gentle turning
        elif abs(offset) <= self.center_threshold:
            if offset < 0:
                current_decision = "gentle_left"
                self.forward_steps = 0
            else:
                current_decision = "gentle_right"
                self.forward_steps = 0
        # If we're way off center, use normal turning
        else:
            if offset < 0:
                current_decision = "left"
                self.forward_steps = 0
            else:
                current_decision = "right"
                self.forward_steps = 0

        # If we're continuing in the same direction, increment counter
        if current_decision == self.last_direction:
            self.same_direction_count += 1
        else:
            self.same_direction_count = 0

        # Only switch directions if we've been going the same way for a while
        # or if this is our first decision
        if (
            self.last_direction is None
            or self.same_direction_count >= 2
            or current_decision == "scan"
        ):
            self.last_direction = current_decision
            return current_decision
        else:
            # Otherwise, keep the last direction to reduce jitter
            return self.last_direction

    def check_scan_needed(self):
        """Check if we need to start scanning for new balls"""
        if time.time() - self.last_ball_time > self.scan_interval:
            self.last_ball_time = time.time()  # Reset timer
            self.forward_steps = 0
            return True
        return False
