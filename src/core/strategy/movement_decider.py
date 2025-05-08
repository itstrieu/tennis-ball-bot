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
from typing import Optional, Tuple, List, Any
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
        self.last_seen_valid = False  # True only if the last ball detection was valid
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
    def decide(self, ball_data: Optional[List[Any]]) -> str:
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
            ball_data: List of detections. Expected: [((x,y,w,h), conf, label), ...] or None

        Returns:
            str: One of the keys in movement_steps (e.g., 'small_forward', 'micro_left', 'search')

        Raises:
            RobotError: If decision making fails
        """
        self.logger.info(f"Raw ball_data received in MovementDecider: {ball_data}")

        processed_bboxes = []
        if ball_data:  # ball_data can be None here, so check first
            for item in ball_data:
                # Expect item to be like ((x,y,w,h), confidence, label)
                if (
                    isinstance(item, tuple)
                    and len(item) > 0
                    and isinstance(item[0], tuple)
                    and len(item[0]) == 4
                ):
                    all_coords_are_numbers = all(
                        isinstance(coord, (int, float)) for coord in item[0]
                    )
                    if all_coords_are_numbers:
                        processed_bboxes.append(item[0])  # Add the actual bbox tuple
                    else:
                        self.logger.warning(
                            f"Invalid coordinate types in bbox: {item[0]} from {item}"
                        )
                else:
                    self.logger.warning(f"Skipping malformed item in ball_data: {item}")

        # === Case 1: Ball is detected this frame ===
        if processed_bboxes:  # Check against the filtered and processed list
            self.no_ball_count = 0

            # Sort balls by area (w*h) in descending order
            processed_bboxes.sort(key=lambda bbox: bbox[2] * bbox[3], reverse=True)

            chosen_ball = None
            if len(processed_bboxes) > 1:
                largest_ball_bbox = processed_bboxes[0]
                second_largest_ball_bbox = processed_bboxes[1]

                largest_area = largest_ball_bbox[2] * largest_ball_bbox[3]
                second_largest_area = (
                    second_largest_ball_bbox[2] * second_largest_ball_bbox[3]
                )

                # Check for division by zero, though largest_area should be > 0 if a ball is detected
                if (
                    largest_area > 0
                    and (second_largest_area / largest_area)
                    >= self.config.multiple_ball_area_similarity_threshold
                ):
                    # More than one ball of similar size, choose the one closest to the center
                    self.logger.info(
                        "Multiple similar-sized balls detected. Choosing closest to center."
                    )
                    # Consider only balls that are similar in size to the largest
                    similar_sized_balls = [
                        b
                        for b in processed_bboxes
                        if (b[2] * b[3] / largest_area)
                        >= self.config.multiple_ball_area_similarity_threshold
                    ]

                    min_offset_ball = None
                    min_abs_offset_val = float("inf")

                    for ball_bbox in similar_sized_balls:
                        ball_x, _, ball_w, _ = ball_bbox
                        bbox_center_x = ball_x + (ball_w / 2)
                        current_offset = (
                            bbox_center_x
                            - self.config.camera_offset
                            - (self.config.frame_width / 2)
                        )
                        if abs(current_offset) < min_abs_offset_val:
                            min_abs_offset_val = abs(current_offset)
                            min_offset_ball = ball_bbox

                    if min_offset_ball:
                        chosen_ball = min_offset_ball
                        self.logger.info(
                            f"Chose ball {chosen_ball} closest to center from similar sized balls."
                        )
                    else:  # Should not happen if similar_sized_balls is not empty
                        chosen_ball = largest_ball_bbox
                        self.logger.warning(
                            "Could not determine closest ball among similar ones, defaulting to largest."
                        )
                else:
                    # Largest ball is significantly larger or only one/two balls and not similar
                    chosen_ball = largest_ball_bbox
                    self.logger.info(f"Choosing largest ball: {chosen_ball}")
            elif processed_bboxes:  # Only one ball detected
                chosen_ball = processed_bboxes[0]
                self.logger.info(f"Only one ball detected: {chosen_ball}")

            if not chosen_ball:
                # This case should ideally not be reached if processed_bboxes is not empty.
                # Fallback or log error, then decide to search or handle appropriately.
                self.logger.warning(
                    "No ball chosen despite detection. Defaulting to search."
                )
                # Transition to no ball detected logic or return search
                # For now, let's increment no_ball_count and proceed to Case 2 logic
                self.no_ball_count += 1
                # The rest of Case 2 logic will handle what to do next
            else:
                x, y, w, h = (
                    chosen_ball  # Use the chosen ball for subsequent calculations
                )

                # Calculate offset from center and area ratio
                bbox_center_x = x + (w / 2)
                offset = (
                    bbox_center_x
                    - self.config.camera_offset
                    - (self.config.frame_width / 2)
                )
                area = w * h
                ratio = (
                    area / self.config.target_area if self.config.target_area > 0 else 0
                )

                self.last_area = area
                self.last_seen_valid = True  # Mark that we just saw the ball

                # Ensure thresholds are available
                if self.config.thresholds is None:
                    self.logger.error("Thresholds configuration is missing!")
                    return "search"  # Or some other safe default action

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
