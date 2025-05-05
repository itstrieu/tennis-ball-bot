"""
demo_robot.py

Main entry point for the robot demo.
Initializes and runs the robot components.
"""

import asyncio
import logging

from src.app.camera_manager import CameraManager
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.app.robot_controller import RobotController
from src.streaming.stream_server import StreamServer
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class DemoRobot:
    """
    Manages the lifecycle of the robot components.
    Handles initialization, running, and cleanup of the robot.

    Attributes:
        config: RobotConfig instance for configuration values
        logger: Logger instance
        camera: CameraManager instance
        motion: MotionController instance
        vision: VisionTracker instance
        decider: MovementDecider instance
        controller: RobotController instance
        stream_server: StreamServer instance
        _main_loop: asyncio event loop for main operations
        _cleanup_complete: bool indicating if cleanup is complete
        _cleanup_lock: asyncio Lock for preventing multiple cleanups
    """

    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger.get_logger(name="demo", log_level=logging.INFO)
        self.camera = None
        self.motion = None
        self.vision = None
        self.decider = None
        self.controller = None
        self.stream_server = None
        self._cleanup_complete = False
        self._main_loop = None

    async def initialize(self):
        """Initialize all robot components."""
        try:
            # Initialize camera
            self.logger.info("Initializing camera...")
            self.camera = CameraManager(self.config)
            await self.camera.initialize()
            await self.camera.start_streaming()  # Start camera streaming

            # Initialize motion controller
            self.logger.info("Initializing motion controller...")
            self.motion = MotionController(self.config)
            await self.motion.initialize()

            # Initialize vision tracker
            self.logger.info("Initializing vision tracker...")
            self.vision = VisionTracker(self.config)
            await self.vision.initialize()
            await self.vision.set_camera(self.camera)

            # Initialize movement decider
            self.logger.info("Initializing movement decider...")
            self.decider = MovementDecider(self.config)
            await self.decider.initialize()

            # Initialize robot controller
            self.logger.info("Initializing robot controller...")
            self.controller = RobotController(
                motion=self.motion,
                vision=self.vision,
                decider=self.decider,
                config=self.config,
                dev_mode=True,
            )
            await self.controller.initialize()

            self.logger.info("All components initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            await self.cleanup()
            raise RobotError(f"Initialization failed: {str(e)}", "demo_robot")

    async def run(self):
        """Run the robot demo."""
        try:
            # Store the main event loop
            self._main_loop = asyncio.get_event_loop()

            # Start streaming server in the background
            self.logger.info("Starting streaming server...")
            self.stream_server = StreamServer(self.config)
            self.stream_server.set_components(self.camera, self.vision)
            await self.stream_server.start()

            # Start the robot controller
            self.logger.info("Starting robot controller...")
            await self.controller.run()

        except Exception as e:
            self.logger.error(f"Error running demo: {str(e)}")
            await self.cleanup()
            raise RobotError(f"Demo run failed: {str(e)}", "demo_robot")

    async def cleanup(self):
        """Clean up all robot components."""
        if self._cleanup_complete:
            return

        try:
            # Stop the robot controller first
            if self.controller is not None:
                await self.controller.cleanup()
                self.controller = None

            # Stop the streaming server
            if self.stream_server is not None:
                await self.stream_server.stop()
                self.logger.info("Streaming server stopped")
                self.stream_server = None

            # Clean up the movement decider
            if self.decider is not None:
                await self.decider.cleanup()
                self.decider = None

            # Clean up the vision tracker (sync)
            if self.vision is not None:
                self.vision.cleanup()
                self.vision = None

            # Clean up the motion controller (sync)
            if self.motion is not None:
                self.motion.cleanup()
                self.motion = None

            # Clean up the camera
            if self.camera is not None:
                await self.camera.cleanup()
                self.camera = None

            self._cleanup_complete = True
            self.logger.info("Cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise RobotError(f"Cleanup failed: {str(e)}", "demo_robot")


async def main():
    """Main entry point for the robot demo."""
    robot = DemoRobot()
    main_task = None
    try:
        main_task = asyncio.create_task(robot.run(), name="RobotRun")
        # Initialization must happen before running the main task
        await robot.initialize()
        # Now wait for the main task to complete (or be cancelled)
        await main_task
    except (KeyboardInterrupt, asyncio.CancelledError):
        robot.logger.info("Shutdown signal received, cleaning up...")
        if main_task and not main_task.done():
            main_task.cancel()
            try:
                await main_task  # Allow cancellation to propagate
            except asyncio.CancelledError:
                robot.logger.info("Main task cancelled.")
    except Exception as e:
        Logger.get_logger(name="main", log_level=logging.ERROR).error(
            f"Error in main: {str(e)}"
        )
        raise
    finally:
        robot.logger.info("Executing final cleanup...")
        await robot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
