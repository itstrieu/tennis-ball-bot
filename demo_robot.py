"""
demo_robot.py

Main entry point for the robot demo.
Initializes and runs the robot components.
"""

import asyncio
import signal
import atexit
import logging
from typing import Optional

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
        self._main_loop = None
        self._cleanup_complete = False
        self._cleanup_lock = asyncio.Lock()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            if self._main_loop and not self._cleanup_complete:
                self._main_loop.create_task(self.cleanup())
                
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        # Register cleanup with atexit
        atexit.register(lambda: asyncio.run(self.cleanup()) if not self._cleanup_complete else None)

    async def initialize(self):
        """Initialize all robot components."""
        try:
            # Create main event loop
            self._main_loop = asyncio.get_event_loop()
            
            # Initialize camera
            self.camera = CameraManager(self.config)
            await self.camera.initialize()
            
            # Initialize motion controller
            self.motion = MotionController(self.config)
            await self.motion.initialize()
            
            # Initialize vision tracker
            self.vision = VisionTracker(self.config)
            await self.vision.initialize()
            await self.vision.set_camera(self.camera)  # Set the camera instance
            
            # Initialize movement decider
            self.decider = MovementDecider(self.config)
            await self.decider.initialize()
            
            # Initialize robot controller
            self.controller = RobotController(
                motion=self.motion,
                vision=self.vision,
                decider=self.decider,
                config=self.config,
                dev_mode=True
            )
            await self.controller.initialize()
            
            # Initialize streaming server
            self.stream_server = StreamServer(self.config)
            self.stream_server.set_components(self.camera, self.vision)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            await self.cleanup()
            raise RobotError(f"Initialization failed: {str(e)}", "demo_robot")

    async def run(self):
        """Run the robot demo."""
        try:
            # Start streaming server
            self.logger.info("Streaming server started")
            await self.stream_server.start()
            
            # Run robot controller
            await self.controller.run()
            
        except Exception as e:
            self.logger.error(f"Error running demo: {str(e)}")
            await self.cleanup()
            raise RobotError(f"Demo run failed: {str(e)}", "demo_robot")

    async def cleanup(self):
        """Clean up all robot components."""
        async with self._cleanup_lock:
            if self._cleanup_complete:
                return
                
            try:
                # Stop the robot controller first to prevent any new operations
                if self.controller:
                    await self.controller.cleanup()
                    
                # Stop the streaming server
                if self.stream_server:
                    await self.stream_server.stop()
                    self.logger.info("Streaming server stopped")
                    
                # Clean up the movement decider
                if self.decider:
                    await self.decider.cleanup()
                    
                # Clean up the vision tracker (which uses the camera)
                if self.vision:
                    await self.vision.cleanup()
                    
                # Clean up the motion controller
                if self.motion:
                    await self.motion.cleanup()
                    
                # Clean up the camera last since other components depend on it
                if self.camera:
                    await self.camera.cleanup()
                    
                self._cleanup_complete = True
                self.logger.info("Cleanup completed successfully")
                
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                raise RobotError(f"Cleanup failed: {str(e)}", "demo_robot")


async def main():
    """Main entry point for the robot demo."""
    try:
        # Create and run robot
        robot = DemoRobot()
        await robot.initialize()
        await robot.run()
        
    except Exception as e:
        Logger.get_logger(name="main", log_level=logging.ERROR).error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
