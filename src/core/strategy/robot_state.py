"""
robot_state.py

Implements a state machine for the robot's behavior.
Defines states, transitions, and state-specific behavior.

This module provides:
- State machine implementation for robot behavior
- State transition logic
- State-specific data management
- Error handling and recovery
"""

from enum import Enum, auto
from typing import Optional, Tuple, List
import logging
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class RobotState(Enum):
    """
    Possible states of the robot.

    States:
    - INITIALIZING: Initial setup state
    - SEARCHING: Looking for a ball
    - APPROACHING: Moving toward a detected ball
    - CENTERING: Adjusting position to center on ball
    - RECOVERING: Lost sight of ball, trying to recover
    - STOPPED: Ball is close enough to stop
    - ERROR: Error state requiring intervention
    """

    INITIALIZING = auto()
    SEARCHING = auto()  # Looking for a ball
    APPROACHING = auto()  # Moving toward a detected ball
    CENTERING = auto()  # Adjusting position to center on ball
    RECOVERING = auto()  # Lost sight of ball, trying to recover
    STOPPED = auto()  # Ball is close enough to stop
    ERROR = auto()  # Error state


class RobotStateMachine:
    """
    State machine for controlling robot behavior.
    Manages state transitions and state-specific behavior.

    This class provides:
    - State transition management
    - State-specific data tracking
    - Error handling and recovery
    - State query methods

    The state machine implements the following behavior:
    1. Starts in SEARCHING state
    2. Transitions to CENTERING when ball is detected
    3. Moves to APPROACHING when ball is centered
    4. Enters STOPPED when ball is close enough
    5. Handles recovery when ball is lost
    6. Manages error states and recovery

    Attributes:
        config: RobotConfig instance for configuration values
        current_state: Current state of the robot
        previous_state: Previous state before last transition
        error_message: Error message if in ERROR state
        _search_count: Counter for search attempts
        _last_ball_data: Last known ball position and size
        _recovery_attempts: Counter for recovery attempts
        logger: Logger instance for logging operations
    """

    def __init__(self, config=None):
        """
        Initialize the state machine.

        This method:
        1. Sets up configuration
        2. Initializes state tracking
        3. Configures logging

        Args:
            config: Optional RobotConfig instance
        """
        self.config = config or default_config
        self.logger = Logger.get_logger(name="state", log_level=logging.INFO)
        self.current_state = RobotState.SEARCHING
        self.previous_state = None
        self.error_message = None

        # State-specific data
        self._search_count = 0
        self._last_ball_data = None  # (offset, area)
        self._recovery_attempts = 0

    @with_error_handling("state_machine")
    def update(
        self, ball_data: Optional[List[Tuple[float, float, float, float]]]
    ) -> None:
        """
        Update the state machine with new ball detection data.

        This method:
        1. Handles state transitions
        2. Updates state-specific data
        3. Manages error conditions

        Args:
            ball_data: List of bounding boxes if ball detected, None otherwise
                      Each box is (x, y, width, height)

        Raises:
            RobotError: If state update fails
        """
        self._handle_state_transition(ball_data)
        self._update_state_data(ball_data)

    def _handle_state_transition(
        self, ball_data: Optional[List[Tuple[float, float, float, float]]]
    ) -> None:
        """
        Handle state transitions based on current state and ball data.

        This method:
        1. Checks for error state
        2. Routes to appropriate handler based on ball detection
        3. Manages state transitions

        Args:
            ball_data: List of bounding boxes if ball detected, None otherwise
        """
        if self.current_state == RobotState.ERROR:
            return  # Stay in error state until reset

        if ball_data is None or not ball_data:
            self._handle_no_ball()
        else:
            self._handle_ball_detected(ball_data)

    def _handle_no_ball(self) -> None:
        """
        Handle state transitions when no ball is detected.

        This method:
        1. Transitions APPROACHING/CENTERING to RECOVERING
        2. Moves STOPPED to SEARCHING
        3. Manages recovery attempts
        4. Updates search count
        """
        if self.current_state == RobotState.APPROACHING:
            self._transition_to_state(RobotState.RECOVERING)
        elif self.current_state == RobotState.CENTERING:
            self._transition_to_state(RobotState.RECOVERING)
        elif self.current_state == RobotState.STOPPED:
            self._transition_to_state(RobotState.SEARCHING)
        elif self.current_state == RobotState.RECOVERING:
            if self._recovery_attempts >= self.config.max_recovery_attempts:
                self._transition_to_state(RobotState.SEARCHING)
                self._recovery_attempts = 0
            else:
                self._recovery_attempts += 1
        elif self.current_state == RobotState.SEARCHING:
            self._search_count += 1

    def _handle_ball_detected(
        self, ball_data: List[Tuple[float, float, float, float]]
    ) -> None:
        """
        Handle state transitions when a ball is detected.

        This method:
        1. Analyzes ball position and size
        2. Manages state transitions based on ball state
        3. Resets recovery attempts when ball found

        Args:
            ball_data: List of bounding boxes for detected balls
        """
        # Filter out invalid bounding boxes (e.g., empty tuples or not enough elements)
        valid_ball_data = [
            bbox for bbox in ball_data if isinstance(bbox, tuple) and len(bbox) == 4
        ]

        if not valid_ball_data:
            self.logger.warning(
                "Received ball_data with invalid bbox structures. "
                "Treating as no ball detected."
            )
            self._handle_no_ball()
            return

        # Use the largest ball (by area) to handle multiple detections
        largest_ball = max(valid_ball_data, key=lambda bbox: bbox[2] * bbox[3])
        x, y, w, h = largest_ball

        # Calculate offset from center and area
        bbox_center_x = x + (w / 2)
        camera_offset = self.config.camera_offset
        frame_width_half = self.config.frame_width / 2
        offset = bbox_center_x - camera_offset - frame_width_half
        area = w * h

        if self.current_state == RobotState.SEARCHING:
            self._search_count = 0
            self._transition_to_state(RobotState.CENTERING)
        elif self.current_state == RobotState.RECOVERING:
            self._recovery_attempts = 0
            self._transition_to_state(RobotState.CENTERING)
        elif self.current_state == RobotState.CENTERING:
            # Ball is centered
            if abs(offset) < self.config.center_threshold:
                self._transition_to_state(RobotState.APPROACHING)
        elif self.current_state == RobotState.APPROACHING:
            # Ball is close enough
            stop_threshold = self.config.thresholds["stop"]
            if area > self.config.target_area * stop_threshold:
                self._transition_to_state(RobotState.STOPPED)

    def _update_state_data(
        self, ball_data: Optional[List[Tuple[float, float, float, float]]]
    ) -> None:
        """
        Update state-specific data.

        This method:
        1. Updates last known ball data
        2. Maintains state history

        Args:
            ball_data: List of bounding boxes if ball detected, None otherwise
        """
        if ball_data is not None and ball_data:
            self._last_ball_data = ball_data

    def _transition_to_state(self, new_state: RobotState) -> None:
        """
        Transition to a new state with logging.

        This method:
        1. Updates state history
        2. Logs state transition
        3. Updates current state

        Args:
            new_state: The state to transition to
        """
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.logger.info(
                f"State transition: {self.previous_state.name} -> {self.current_state.name}"
            )

    def _transition_to_error(self, error_message: str) -> None:
        """
        Transition to error state with error message.

        This method:
        1. Sets error message
        2. Transitions to ERROR state
        3. Logs error condition

        Args:
            error_message: Description of the error
        """
        self.error_message = error_message
        self._transition_to_state(RobotState.ERROR)
        self.logger.error(f"Error state entered: {error_message}")

    def reset(self) -> None:
        """
        Reset the state machine to initial state.

        This method:
        1. Resets all state tracking
        2. Clears error conditions
        3. Returns to SEARCHING state
        """
        self.current_state = RobotState.SEARCHING
        self.previous_state = None
        self.error_message = None
        self._search_count = 0
        self._last_ball_data = None
        self._recovery_attempts = 0
        self.logger.info("State machine reset")

    @property
    def should_search(self) -> bool:
        """Whether the robot should be in search mode."""
        return self.current_state in [RobotState.SEARCHING, RobotState.RECOVERING]

    @property
    def should_approach(self) -> bool:
        """Whether the robot should be approaching the ball."""
        return self.current_state == RobotState.APPROACHING

    @property
    def should_center(self) -> bool:
        """Whether the robot should be centering on the ball."""
        return self.current_state == RobotState.CENTERING

    @property
    def should_stop(self) -> bool:
        """Whether the robot should stop."""
        return self.current_state == RobotState.STOPPED

    @property
    def is_in_error(self) -> bool:
        """Whether the robot is in an error state."""
        return self.current_state == RobotState.ERROR
