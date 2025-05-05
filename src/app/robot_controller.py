"""
robot_controller.py

Main control logic for the robot. Coordinates vision, motion, and decision-making
to perform search-and-retrieve behaviors for tennis balls using a camera feed.

This module implements the core control logic for the robot, including:
- State machine management
- Emergency stop handling
- Motion execution
- Resource cleanup
"""

import logging
import asyncio
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config
from src.core.strategy.robot_state import RobotStateMachine


class RobotController:
    """
    Coordinates motion, vision tracking, and decision logic to control the robot's behavior.

    This class serves as the central coordinator for the robot's operations:
    1. Manages the state machine for behavior control
    2. Handles emergency stops and graceful shutdown
    3. Coordinates between vision, motion, and decision components
    4. Implements the main control loop

    Executes a cyclic process:
    - Rotates to scan surroundings
    - Waits for ball detection
    - Approaches and retrieves ball when found
    - Resumes scanning after completing the retrieval cycle

    Attributes:
        motion: Motion controller module for moving/rotating the robot
        vision: Vision module for detecting balls via camera input
        decider: MovementDecider instance for deciding how to respond to detections
        config: RobotConfig instance for configuration values
        dev_mode: Whether development slowdown is active
        dev_slowdown: Slowdown factor for development mode
        is_running: Flag indicating if the robot is active
        state_machine: RobotStateMachine instance for behavior control
        _emergency_stop: Flag for emergency stop state
        _cleanup_complete: Flag for cleanup completion
        _cleanup_lock: asyncio.Lock for thread-safe cleanup
        logger: Logger instance for logging operations
        _initialized: Flag for initialization state
    """

    def __init__(self, motion, vision, decider, config=None, dev_mode=False):
        """
        Initialize the RobotController with its components.

        Args:
            motion: Motion controller instance
            vision: Vision tracker instance
            decider: Movement decider instance
            config: Optional RobotConfig instance
            dev_mode: Whether to enable development mode
        """
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

        # Signal handling removed; rely on main() cleanup

    @with_error_handling("robot_controller")
    async def emergency_stop(self, from_cancel: bool = False):
        """
        Immediately stop all robot motion and initiate cleanup.
        Args:
            from_cancel: If called due to task cancellation.
        """
        if not self._cleanup_complete:
            self.logger.warning(
                f"Emergency stop activated {'(from cancellation)' if from_cancel else ''}"
            )
            self._emergency_stop = True
            self.is_running = False

            # Immediately stop physical motion
            if self.motion:
                # Await async stop/fin_off methods
                await self.motion.stop()
                await self.motion.fin_off()

            # Initiate the full cleanup process
            # Cleanup is now handled by DemoRobot after emergency stop finishes

            self.logger.info("Emergency stop process completed")

    @with_error_handling("robot_controller")
    async def run(self):
        """
        Main control loop for the robot.
        """
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
            if self.motion:
                await self.motion.verify_motor_control()
                await self.motion.fin_on()

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
                await self.execute_motion(action)

                # Development mode slowdown
                if self.dev_mode:
                    await asyncio.sleep(
                        self.config.inter_step_pause * self.dev_slowdown
                    )

        except asyncio.CancelledError:
            self.logger.info("Control loop cancelled.")
            # Ensure resources are released immediately on cancellation
            await self.emergency_stop(from_cancel=True)
            raise  # Re-raise CancelledError
        except Exception as e:
            self.logger.error(f"Error in main control loop: {str(e)}")
            await self.emergency_stop()  # Attempt graceful stop on other errors
            raise RobotError(f"Control loop failed: {str(e)}", "robot_controller")
        finally:
            # General cleanup moved to DemoRobot, only stop loop flag here
            self.is_running = False

    @with_error_handling("robot_controller")
    async def execute_motion(self, action: str):
        """
        Execute the specified motion action.
        """
        if self._emergency_stop:
            return

        try:
            # Get movement parameters from config
            params = self.config.movement_steps.get(action)
            if not params:
                self.logger.error(f"Unknown action: {action}")
                return

            # Check for obstacles before any forward movement
            if (
                params["method"] == "move_forward"
                and self.motion.ultrasonic.is_obstacle()
            ):
                self.logger.warning("Obstacle detected, stopping movement")
                self.motion.stop()
                return

            # Execute the movement
            method = getattr(self.motion, params["method"])
            await method(speed=params["speed"], duration=params["time"])

        except Exception as e:
            self.logger.error(f"Error executing motion {action}: {str(e)}")
            # Stop immediately on motion error
            self.motion.stop()
            self.is_running = False  # Signal loop to stop
            raise RobotError(f"Motion execution failed: {str(e)}", "robot_controller")

    @with_error_handling("robot_controller")
    async def cleanup(self, force: bool = False, from_cancel: bool = False):
        """
        Clean up resources and stop all operations.

        Args:
            force: Whether to force cleanup (e.g., during emergency stop)
            from_cancel: Indicates if cleanup is due to task cancellation
        """
        if not self._cleanup_complete:
            try:
                # Stop any ongoing motion
                if self.motion:
                    await self.motion.stop()

                # Set flags to stop loops/tasks
                self.is_running = False
                self._emergency_stop = True  # Ensure loops terminate

                # Cleanup camera and vision if available
                if self.vision is not None:
                    try:
                        # Vision cleanup is synchronous
                        self.vision.cleanup()
                    except Exception as e:
                        self.logger.error(f"Error cleaning up vision: {str(e)}")
                        if force:
                            raise

                self._cleanup_complete = True
                self._initialized = False
                self.logger.info("Cleanup completed successfully")

            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                if force:
                    raise RobotError(f"Cleanup failed: {str(e)}", "robot_controller")

    async def initialize(self):
        """
        Initialize the robot controller components.
        """
        try:
            # Initialize vision tracker first (loads YOLO model)
            await self.vision.initialize()

            # Initialize movement decider
            await self.decider.initialize()

            # Await async motion methods
            if self.motion:
                await self.motion.verify_motor_control()
                await self.motion.fin_on()

            # Set up camera in vision tracker
            if hasattr(self.vision, "camera") and self.vision.camera is not None:
                await self.vision.set_camera(self.vision.camera)
            else:
                self.logger.warning(
                    "Vision tracker does not have a camera instance set."
                )

            self._initialized = True
            self.logger.info("Robot controller initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize robot controller: {str(e)}")
            raise RobotError(
                f"Robot controller initialization failed: {str(e)}", "robot_controller"
            )
