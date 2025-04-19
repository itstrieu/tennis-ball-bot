import logging
from utils.logger import Logger
from config.motion import (
    TARGET_AREA,
    CENTER_THRESHOLD,
)


class MovementDecider:
    """
    MovementDecider uses configurable thresholds to decide robot actions based on
    object offset and area.
    """

    def __init__(
        self,
        target_area: float = TARGET_AREA,
        center_threshold: int = CENTER_THRESHOLD,
    ):
        """
        Initialize decider with parameters from config.motion

        Args:
            target_area (float): area at which object is considered "close enough"
            center_threshold (int): pixel offset threshold for "centered"
        """
        self.target_area = target_area
        self.center_threshold = center_threshold

        decider_logger = Logger(name="decider", log_level=logging.DEBUG)
        self.logger = decider_logger.get_logger()

    def _effective_threshold(self, area: float) -> int:
        """
        Compute dynamic threshold based on object size.
        Scales with sqrt(area) and caps at center_threshold.
        """
        dynamic = int((area**0.5) * 0.5)
        return min(self.center_threshold, dynamic)

    def decide(self, offset: float, area: float) -> str:
        """
        Decide action based on object offset and area.

        Returns:
            'left', 'right', 'forward', or 'stop'
        """
        self.logger.debug(f"Offset: {offset:.2f}, Area: {area:.2f}")

        # stop if object is close enough
        if area >= self.target_area:
            return "stop"

        threshold = self._effective_threshold(area)
        self.logger.debug(f"Effective threshold: {threshold}")

        # forward if within threshold
        if abs(offset) <= threshold:
            return "forward"

        # otherwise turn
        return "left" if offset < 0 else "right"
