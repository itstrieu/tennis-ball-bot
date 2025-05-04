"""
robot_controller.py

Main control logic for the robot. Coordinates vision, motion, and decision-making
to perform search-and-retrieve behaviors for tennis balls using a camera feed.
"""

import logging
import time
import signal
import sys
import asyncio
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
        self._cleanup_lock = asyncio.Lock()
        self.logger = Logger.get_logger(name="robot", log_level=logging.INFO)
        self._initialized = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        self.logger.info("Received shutdown signal")
        asyncio.create_task(self.emergency_stop())

    @with_error_handling("robot_controller")
    async def emergency_stop(self):
        """Immediately stop all robot motion and cleanup resources."""
        if not self._cleanup_complete:
            self._emergency_stop = True
            self.is_running = False
            self.logger.warning("Emergency stop activated")
            
            try:
                # Stop any ongoing motion
                self.motion.stop()
                
                # Cleanup resources
                await self.cleanup(force=True)
                
                self._cleanup_complete = True
                self.logger.info("Emergency stop completed")
            except Exception as e:
                self.logger.error(f"Error during emergency stop: {str(e)}")
                raise RobotError(f"Emergency stop failed: {str(e)}", "robot_controller")

    @with_error_handling("robot_controller")
    async def run(self):
        """Main control loop for the robot."""
        if not self._initialized:
            raise RobotError("Robot controller not initialized", "robot_controller")
            
        if self.is_running:
            self.logger.warning("Robot is already running")
            return

        self.is_running = True
        self._emergency_stop = False
        self._cleanup_complete = False
        
        try:
            # Verify motor control and fins are active before starting main loop
            self.logger.info("Verifying motor control and activating fins...")
            self.motion.verify_motor_control()
            self.motion.fin_on()
            
            self.logger.info("Starting main control loop...")
            while self.is_running and not self._emergency_stop:
                # Get frame from camera
                self.logger.debug("Capturing frame...")
                frame = await self.vision.get_frame()
                
                # Get ball detection data
                self.logger.debug("Detecting balls...")
                ball_data = await self.vision.detect_ball(frame)
                
                # Update state machine
                self.logger.debug("Updating state machine...")
                self.state_machine.update(ball_data)
                
                # Decide and execute action
                self.logger.debug("Deciding action...")
                action = self.decider.decide(ball_data)
                self.logger.info(f"Executing action: {action}")
                self.execute_motion(action)
                
                # Development mode slowdown
                if self.dev_mode:
                    time.sleep(self.config.inter_step_pause * self.dev_slowdown)
                    
        except Exception as e:
            self.logger.error(f"Error in main control loop: {str(e)}")
            self.emergency_stop()
            raise RobotError(f"Control loop failed: {str(e)}", "robot_controller")
        finally:
            await self.cleanup()

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
                
            # Check for obstacles before any forward movement
            if params['method'] == 'move_forward' and self.motion.ultrasonic.is_obstacle():
                self.logger.warning("Obstacle detected, stopping movement")
                self.motion.stop()
                return
                
            # Execute the movement
            method = getattr(self.motion, params['method'])
            method(speed=params['speed'], duration=params['time'])
            
        except Exception as e:
            self.logger.error(f"Error executing motion {action}: {str(e)}")
            self.emergency_stop()
            raise RobotError(f"Motion execution failed: {str(e)}", "robot_controller")

    @with_error_handling("robot_controller")
    async def cleanup(self, force: bool = False):
        """Cleanup resources and stop the robot."""
        async with self._cleanup_lock:
            if not force and self._cleanup_complete:
                return
                
            try:
                # Stop any ongoing motion
                self.motion.stop()
                
                # Deactivate fins
                self.motion.fin_off()
                
                # Cleanup camera
                if hasattr(self, 'vision') and self.vision is not None:
                    await self.vision.cleanup()
                
                self._cleanup_complete = True
                self._initialized = False
                self.logger.info("Cleanup completed successfully")
                
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                if force:
                    raise RobotError(f"Cleanup failed: {str(e)}", "robot_controller")

    async def initialize(self):
        """Initialize the robot controller components."""
        try:
            # Verify motor control before starting
            self.motion.verify_motor_control()
            
            # Activate fins at start
            self.motion.fin_on()
            
            self._initialized = True
            self.logger.info("Robot controller initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize robot controller: {str(e)}")
            raise RobotError(f"Robot controller initialization failed: {str(e)}", "robot_controller")
