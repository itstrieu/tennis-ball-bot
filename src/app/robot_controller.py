"""
robot_controller.py

Main control logic for the robot. Coordinates vision, motion, and decision-making
to perform search-and-retrieve behaviors for tennis balls using a camera feed.
"""

import logging
import time
import signal
import sys
from typing import Optional, Tuple
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config
from src.app.camera_manager import CameraManager
from src.core.strategy.robot_state import RobotStateMachine, RobotState


class RobotController:
    """
    Coordinates motion, vision tracking, and decision logic to control the robot's behavior.

    Executes a cyclic process:
    - Rotates to scan surroundings.
    - Waits for ball detection.
    - Approaches and retrieves ball when found.
    - Resumes scanning after completing the retrieval cycle.

    Attributes:
        motion: Motion controller module for moving/rotating the robot.
        vision: Vision module for detecting balls via camera input.
        decider: MovementDecider instance for deciding how to respond to detections.
        config: RobotConfig instance for configuration values.
        dev_mode (bool): Whether development slowdown is active.
    """

    def __init__(self, motion, vision, decider, config=None, dev_mode=False):
        self.motion = motion
        self.vision = vision
        self.decider = decider
        self.config = config or default_config
        self.dev_mode = dev_mode
        self.dev_slowdown = self.config.dev_slowdown if dev_mode else 1.0
        self.is_running = False
        self.state_machine = RobotStateMachine(config=self.config)
        self._emergency_stop = False
        self._cleanup_complete = False
        self.logger = Logger.get_logger(name="robot", log_level=logging.INFO)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        self.logger.info("Received shutdown signal")
        self.emergency_stop()

    @with_error_handling("robot_controller")
    def emergency_stop(self):
        """Immediately stop all robot motion and cleanup resources."""
        if not self._cleanup_complete:
            self._emergency_stop = True
            self.is_running = False
            self.logger.warning("Emergency stop activated")
            
            try:
                # Stop any ongoing motion
                self.motion.stop()
                
                # Cleanup resources
                self.cleanup(force=True)
                
                self._cleanup_complete = True
                self.logger.info("Emergency stop completed")
            except Exception as e:
                self.logger.error(f"Error during emergency stop: {str(e)}")
                raise RobotError(f"Emergency stop failed: {str(e)}", "robot_controller")

    @with_error_handling("robot_controller")
    def run(self):
        """Main control loop for the robot."""
        if self.is_running:
            self.logger.warning("Robot is already running")
            return

        self.is_running = True
        self._emergency_stop = False
        self._cleanup_complete = False
        
        try:
            while self.is_running and not self._emergency_stop:
                # Get ball detection data
                ball_data = self.vision.detect_ball()
                
                # Update state machine
                self.state_machine.update(ball_data)
                
                # Decide and execute action
                action = self._decide_action(ball_data)
                self.execute_motion(action)
                
                # Development mode slowdown
                if self.dev_mode:
                    time.sleep(self.config.inter_step_pause * self.dev_slowdown)
                    
        except Exception as e:
            self.logger.error(f"Error in main control loop: {str(e)}")
            self.emergency_stop()
            raise RobotError(f"Control loop failed: {str(e)}", "robot_controller")
        finally:
            self.cleanup()

    @with_error_handling("robot_controller")
    def _decide_action(self, ball_data: Optional[Tuple[float, float]]) -> str:
        """Decide next action based on current state and ball data."""
        if self._emergency_stop:
            return "stop"
            
        if ball_data is None:
            return self.decider.decide(None, 0)
            
        offset, area = ball_data
        return self.decider.decide(offset, area)

    @with_error_handling("robot_controller")
    def execute_motion(self, action: str):
        """Execute the specified motion action."""
        if self._emergency_stop:
            return
            
        try:
            # Get movement parameters from config
            params = self.config.movement_steps.get(action)
            if not params:
                self.logger.error(f"Unknown action: {action}")
                return
                
            # Execute the movement
            method = getattr(self.motion, params['method'])
            method(speed=params['speed'], time=params['time'])
            
        except Exception as e:
            self.logger.error(f"Error executing motion {action}: {str(e)}")
            self.emergency_stop()
            raise RobotError(f"Motion execution failed: {str(e)}", "robot_controller")

    @with_error_handling("robot_controller")
    def cleanup(self, force: bool = False):
        """Cleanup resources and stop the robot."""
        if not force and self._cleanup_complete:
            return
            
        try:
            # Stop any ongoing motion
            self.motion.stop()
            
            # Cleanup camera
            CameraManager.cleanup()
            
            self._cleanup_complete = True
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            if force:
                raise RobotError(f"Cleanup failed: {str(e)}", "robot_controller")
