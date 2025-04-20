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
        self.last_direction = None
        self.same_direction_count = 0
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
        direction = self.decide_direction(offset)
        distance_action = self.decide_distance_action(area)

        self.logger.debug(
            f"Offset: {offset}, Area: {area}, Direction: {direction}, Distance Action: {distance_action}"
        )

        # First check if we've reached the target
        if distance_action == "stop":
            self.last_direction = "stop"
            self.same_direction_count = 0
            return "stop"

        # Check if we're continuing in the same direction
        current_decision = None

        # If we're well within center threshold (less than half), go forward
        if abs(offset) < self.center_threshold / 2:
            current_decision = "forward"
        # If we're somewhat off-center but still within threshold, use gentle turning
        elif abs(offset) <= self.center_threshold:
            if offset < 0:
                current_decision = "gentle_left"
            else:
                current_decision = "gentle_right"
        # If we're way off center, use normal turning
        else:
            if offset < 0:
                current_decision = "left"
            else:
                current_decision = "right"

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
            or current_decision == "forward"
        ):
            self.last_direction = current_decision
            return current_decision
        else:
            # Otherwise, keep the last direction to reduce jitter
            return self.last_direction
