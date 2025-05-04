"""
robot_state.py

Implements a state machine for the robot's behavior.
Defines states, transitions, and state-specific behavior.
"""

from enum import Enum, auto
from typing import Optional, Tuple, List
import logging
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config

class RobotState(Enum):
    """Possible states of the robot."""
    INITIALIZING = auto()
    SEARCHING = auto()      # Looking for a ball
    APPROACHING = auto()    # Moving toward a detected ball
    CENTERING = auto()      # Adjusting position to center on ball
    RECOVERING = auto()     # Lost sight of ball, trying to recover
    STOPPED = auto()        # Ball is close enough to stop
    ERROR = auto()          # Error state

class RobotStateMachine:
    """
    State machine for controlling robot behavior.
    Manages state transitions and state-specific behavior.
    """

    def __init__(self, config=None):
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
    def update(self, ball_data: Optional[List[Tuple[float, float, float, float]]]) -> None:
        """
        Update the state machine with new ball detection data.
        
        Args:
            ball_data: List of bounding boxes if ball detected, None otherwise
        """
        self._handle_state_transition(ball_data)
        self._update_state_data(ball_data)

    def _handle_state_transition(self, ball_data: Optional[List[Tuple[float, float, float, float]]]) -> None:
        """Handle state transitions based on current state and ball data."""
        if self.current_state == RobotState.ERROR:
            return  # Stay in error state until reset

        if ball_data is None or not ball_data:
            self._handle_no_ball()
        else:
            self._handle_ball_detected(ball_data)

    def _handle_no_ball(self) -> None:
        """Handle state transitions when no ball is detected."""
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

    def _handle_ball_detected(self, ball_data: List[Tuple[float, float, float, float]]) -> None:
        """Handle state transitions when a ball is detected."""
        # Use the largest ball (by area)
        largest_ball = max(ball_data, key=lambda bbox: bbox[2] * bbox[3])
        x, y, w, h = largest_ball
        
        # Calculate offset and area
        bbox_center_x = x + (w / 2)
        offset = bbox_center_x - self.config.camera_offset - (self.config.frame_width / 2)
        area = w * h
        
        if self.current_state == RobotState.SEARCHING:
            self._search_count = 0
            self._transition_to_state(RobotState.CENTERING)
        elif self.current_state == RobotState.RECOVERING:
            self._recovery_attempts = 0
            self._transition_to_state(RobotState.CENTERING)
        elif self.current_state == RobotState.CENTERING:
            if abs(offset) < self.config.center_threshold:  # Ball is centered
                self._transition_to_state(RobotState.APPROACHING)
        elif self.current_state == RobotState.APPROACHING:
            if area > self.config.target_area * self.config.thresholds["stop"]:  # Ball is close enough
                self._transition_to_state(RobotState.STOPPED)

    def _update_state_data(self, ball_data: Optional[List[Tuple[float, float, float, float]]]) -> None:
        """Update state-specific data."""
        if ball_data is not None and ball_data:
            self._last_ball_data = ball_data

    def _transition_to_state(self, new_state: RobotState) -> None:
        """Transition to a new state with logging."""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.logger.info(f"State transition: {self.previous_state.name} -> {self.current_state.name}")

    def _transition_to_error(self, error_message: str) -> None:
        """Transition to error state with error message."""
        self.error_message = error_message
        self._transition_to_state(RobotState.ERROR)
        self.logger.error(f"Error state entered: {error_message}")

    def reset(self) -> None:
        """Reset the state machine to initial state."""
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