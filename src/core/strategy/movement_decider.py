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
        self.max_no_ball_count = 8
        self.approach_distance = 0

        self.logger = Logger(name="decider", log_level=logging.INFO).get_logger()

    def decide(self, offset, area):
        self.no_ball_count = 0
        self.approach_distance = min(100, int((area / self.target_area) * 100))

        self.logger.debug(
            f"Offset: {offset}, Area: {area}, Approach: {self.approach_distance}%"
        )

        if area >= self.target_area:
            self.logger.info("Ball is close enough — stopping.")
            self.approach_distance = 0
            return "stop"

        if area > self.target_area * 0.7:
            if abs(offset) <= self.center_threshold:
                self.logger.info("Ball is very close and centered — micro forward.")
                return "micro_forward"

        if abs(offset) <= self.center_threshold:
            if area > self.target_area * 0.5:
                self.logger.info("Ball centered and close — small forward.")
                return "small_forward"
            else:
                self.logger.info("Ball centered and farther — normal forward.")
                return "step_forward"

        if area > self.target_area * 0.5:
            if offset < 0:
                self.logger.info("Ball slightly left and close — micro left.")
                return "micro_left"
            else:
                self.logger.info("Ball slightly right and close — micro right.")
                return "micro_right"
        else:
            if offset < 0:
                self.logger.info("Ball left and farther — step left.")
                return "step_left"
            else:
                self.logger.info("Ball right and farther — step right.")
                return "step_right"

    def handle_no_ball(self):
        self.no_ball_count += 1

        if self.no_ball_count >= self.max_no_ball_count:
            self.logger.info("No ball seen for multiple frames — initiating search.")
            self.no_ball_count = 0
            return "search"

        self.logger.debug(f"No ball detected — count: {self.no_ball_count}")
        return None
