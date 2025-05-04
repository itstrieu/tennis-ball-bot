"""
demo_robot.py

Main entry point for the robot demo. Initializes all components and starts the robot.
Also sets up the streaming server for camera feed.
"""

import signal
import sys
from threading import Thread, Event
import logging
import time
import atexit

import uvicorn
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config
from src.app.camera_manager import CameraManager
from src.app.robot_controller import RobotController
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.streaming.stream_server import StreamServer


class DemoRobot:
    """
    Main demo robot class that manages all components and their lifecycle.
    
    Attributes:
        config: RobotConfig instance for configuration values
        camera: CameraManager instance
        motion: MotionController instance
        vision: VisionTracker instance
        decider: MovementDecider instance
        robot: RobotController instance
        stream_server: StreamServer instance
        logger: Logger instance
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.logger = Logger(name="demo", log_level=logging.INFO).get_logger()
        self.camera = None
        self.motion = None
        self.vision = None
        self.decider = None
        self.robot = None
        self.stream_server = None
        self._cleanup_complete = False
        self._stop_event = Event()
        self._server_thread = None
        self._original_sigint = None
        self._original_sigterm = None

    @with_error_handling("demo_robot")
    def initialize(self):
        """Initialize all robot components."""
        try:
            # Initialize camera first
            self.camera = CameraManager(config=self.config)
            self.camera.initialize()
            
            # Give camera time to stabilize
            time.sleep(1)
            
            # Initialize motion controller
            self.motion = MotionController()
            self.motion.fin_on(speed=self.config.fin_speed)
            
            # Initialize vision tracker
            self.vision = VisionTracker(config=self.config)
            self.vision.set_camera(self.camera)
            
            # Initialize movement decider
            self.decider = MovementDecider(config=self.config)
            
            # Initialize robot controller
            self.robot = RobotController(
                motion=self.motion,
                vision=self.vision,
                decider=self.decider,
                config=self.config
            )
            
            # Initialize streaming server
            self.stream_server = StreamServer(config=self.config)
            self.stream_server.set_components(self.camera, self.vision)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            self.cleanup()
            raise RobotError(f"Initialization failed: {str(e)}", "demo_robot")

    @with_error_handling("demo_robot")
    def run(self):
        """Run the robot and streaming server."""
        if not all([self.camera, self.motion, self.vision, self.decider, self.robot, self.stream_server]):
            self.initialize()
            
        try:
            # Start streaming server in a separate thread
            self._server_thread = Thread(
                target=lambda: uvicorn.run(
                    self.stream_server.app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="info"
                )
            )
            self._server_thread.daemon = True
            self._server_thread.start()
            
            # Run the robot
            self.robot.run()
            
        except Exception as e:
            self.logger.error(f"Error during robot operation: {str(e)}")
            raise RobotError(f"Robot operation failed: {str(e)}", "demo_robot")
        finally:
            self.cleanup()

    @with_error_handling("demo_robot")
    def cleanup(self):
        """Clean up all resources."""
        if self._cleanup_complete:
            return
            
        try:
            # Stop motion first
            if self.motion:
                self.motion.fin_off()
                self.motion = None
                
            # Stop camera and streaming
            if self.stream_server:
                self.stream_server.stop()
                self.stream_server = None
                
            if self.camera:
                self.camera.cleanup()
                self.camera = None
                
            # Wait for server thread to finish
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)
                
            # Restore original signal handlers
            if self._original_sigint:
                signal.signal(signal.SIGINT, self._original_sigint)
            if self._original_sigterm:
                signal.signal(signal.SIGTERM, self._original_sigterm)
                
            self._cleanup_complete = True
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise RobotError(f"Cleanup failed: {str(e)}", "demo_robot")


def main():
    """Main entry point for the demo robot."""
    # Create and run the demo robot
    demo = DemoRobot()
    
    # Set up signal handlers
    def handle_signal(signum, frame):
        demo.logger.info(f"Received signal {signum}, initiating shutdown")
        demo.cleanup()
        sys.exit(0)
        
    # Store original signal handlers
    demo._original_sigint = signal.getsignal(signal.SIGINT)
    demo._original_sigterm = signal.getsignal(signal.SIGTERM)
    
    # Set new signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Register cleanup with atexit
    atexit.register(demo.cleanup)
    
    # Run the robot
    demo.run()


if __name__ == "__main__":
    main()
