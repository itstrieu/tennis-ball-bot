"""
movement_decider.py

Contains logic for interpreting ball position and size, and deciding how
the robot should move to approach and center the ball.

This module provides:
- Ball position and size analysis
- Movement decision making
- Search and recovery strategies
- State tracking for ball detection
"""

import logging
import time
from typing import Optional, Tuple, List
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class MovementDecider:
    """
    Determines movement decisions based on object detection data.

    This class provides:
    - Ball position and size analysis
    - Movement decision making
    - Search and recovery strategies
    - State tracking for ball detection

    The decider uses a hierarchical approach:
    1. Ball detection and size analysis
    2. Position offset calculation
    3. Movement decision based on thresholds
    4. Search and recovery strategies when ball is lost

    Attributes:
        config: RobotConfig instance for configuration values
        no_ball_count: Counter for consecutive frames without ball detection
        last_area: Area of the last seen ball
        last_seen_valid: Whether the last ball detection was valid
        max_no_ball_count: Maximum frames without ball before search
        _initialized: Flag for initialization state
        logger: Logger instance for logging operations
    """

    def __init__(self, config=None):
        """
        Initialize the movement decider.

        This method:
        1. Sets up configuration
        2. Initializes state tracking
        3. Configures logging

        Args:
            config: Optional RobotConfig instance
        """
        self.config = config or default_config
        self.logger = Logger.get_logger(name="decider", log_level=logging.INFO)
        self.no_ball_count = 0  # Tracks how many consecutive frames had no ball
        self.last_area = 0  # Area of last seen ball
        self.last_seen_valid = (
            False  # True only if the ball was seen in the previous frame
        )
        self.max_no_ball_count = self.config.max_no_ball  # Use max_no_ball from config
        self._initialized = False

    async def initialize(self):
        """
        Initialize the movement decider components.

        This method:
        1. Sets initialization flag
        2. Verifies configuration
        3. Prepares for operation

        Raises:
            RobotError: If initialization fails
        """
        try:
            self._initialized = True
            self.logger.info("Movement decider initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize movement decider: {str(e)}")
            raise RobotError(
                f"Movement decider initialization failed: {str(e)}", "movement_decider"
            )

    async def cleanup(self):
        """
        Clean up resources used by the movement decider.

        This method:
        1. Resets state tracking
        2. Clears initialization flag
        3. Handles cleanup errors

        Raises:
            RobotError: If cleanup fails
        """
        try:
            self._initialized = False
            self.logger.info("Movement decider cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during movement decider cleanup: {str(e)}")
            raise RobotError(
                f"Movement decider cleanup failed: {str(e)}", "movement_decider"
            )

    @with_error_handling("movement_decider")
    def decide(
        self, ball_data: Optional[List[Tuple[float, float, float, float]]]
    ) -> str:
        """
        Decide next action based on current detection offset, size ratio, and no-ball history.

        This method implements a hierarchical decision-making process:
        1. Ball detection and size analysis
        2. Position offset calculation
        3. Movement decision based on thresholds
        4. Search and recovery strategies when ball is lost

        The decision hierarchy:
        - Stop if ball is close enough
        - Move forward if centered (speed based on distance)
        - Rotate to center if off-center
        - Take blind step if ball was just lost
        - Enter search mode if ball lost for too long

        Args:
            ball_data: List of bounding boxes if ball detected, None otherwise
                      Each box is (x, y, width, height)

        Returns:
            str: One of the keys in movement_steps (e.g., 'small_forward', 'micro_left', 'search')

        Raises:
            RobotError: If decision making fails
        """
        valid_ball_data = []
        if ball_data:
            valid_ball_data = [
                bbox for bbox in ball_data if isinstance(bbox, tuple) and len(bbox) == 4
            ]
            if not valid_ball_data:
                self.logger.warning(
                    "Received ball_data with invalid bbox structures in MovementDecider."
                )
                # Fall through to "No ball detected this frame" logic by effectively making ball_data empty

        # === Case 1: Ball is detected this frame ===
        if valid_ball_data:  # Check against the filtered list
            self.no_ball_count = 0

            # Use the largest ball (by area) to handle multiple detections
            largest_ball = max(valid_ball_data, key=lambda bbox: bbox[2] * bbox[3])
            x, y, w, h = largest_ball

            # Calculate offset from center and area ratio
            bbox_center_x = x + (w / 2)
            offset = (
                bbox_center_x
                - self.config.camera_offset
                - (self.config.frame_width / 2)
            )
            area = w * h
            ratio = area / self.config.target_area if self.config.target_area > 0 else 0

            self.last_area = area
            self.last_seen_valid = True  # Mark that we just saw the ball

            # 1. Stop if the ball is close enough (based on size ratio)
            if ratio >= self.config.thresholds["stop"]:
                self.logger.info(f"[DECIDE] stop (ratio={ratio:.2f})")
                return "stop"

            # 2. If centered, move forward (speed depends on distance)
            if abs(offset) <= self.config.center_threshold:
                if ratio >= self.config.thresholds["micro"]:
                    self.logger.info(
                        f"[DECIDE] micro_forward (centered + close, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "micro_forward"
                else:
                    self.logger.info(
                        f"[DECIDE] small_forward (centered, ratio={ratio:.2f}, offset={offset})"
                    )
                    return "small_forward"

            # 3. If off-center, rotate to center (speed depends on offset)
            if abs(offset) > self.config.center_threshold:
                if abs(offset) > self.config.center_threshold * 2:
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
            and self.last_area / self.config.target_area
            >= self.config.thresholds["recovery"]
        ):
            self.logger.info(
                f"[DECIDE] step_forward (blind follow-up, last_ratio={self.last_area / self.config.target_area:.2f})"
            )
            self.last_seen_valid = False  # Prevent repeating this action
            return "step_forward"

        # 5. If we've gone too long without seeing the ball, enter search mode
        if self.no_ball_count >= self.config.max_no_ball:
            self.logger.info(f"[DECIDE] search (no_ball_count={self.no_ball_count})")
            self.no_ball_count = 0
            self.last_seen_valid = False
            return "search"

        # 6. Otherwise, continue slow scanning/searching
        self.logger.info(
            f"[DECIDE] search (default, no_ball_count={self.no_ball_count})"
        )
        return "search"
