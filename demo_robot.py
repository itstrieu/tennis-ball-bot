# demo_robot.py

import signal
import sys
from threading import Thread

import uvicorn
from src.app.camera_manager import get_camera
from src.app.robot_controller import RobotController
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.streaming.stream_server import app, set_shared_components
from src.config import vision as vision_config, motion as motion_config

# Module‐level refs for cleanup
_camera = None
_motion = None


def run_robot():
    global _camera, _motion
    # Initialize camera + logic
    camera = get_camera()
    motion = MotionController()
    motion.fin_on(speed=motion_config.FIN_SPEED)
    vision = VisionTracker(
        model_path=vision_config.MODEL_PATH,
        frame_width=vision_config.FRAME_WIDTH,
        camera=camera,
        camera_offset=vision_config.CAMERA_OFFSET,
    )
    strategy = MovementDecider(
        target_area=motion_config.TARGET_AREA,
        center_threshold=motion_config.CENTER_THRESHOLD,
    )
    robot = RobotController(motion, vision, strategy)

    # Share with stream server
    set_shared_components(camera, vision)

    # Save for shutdown
    _camera = camera
    _motion = motion

    try:
        robot.run()
    finally:
        motion.fin_off()
        camera.stop()


def handle_exit(signum, frame):
    print("\n🛑 Shutdown signal received, cleaning up...")
    if _motion:
        _motion.fin_off()
    if _camera:
        _camera.stop()
    sys.exit(0)


if __name__ == "__main__":
    # Catch CTRL+C in main thread
    signal.signal(signal.SIGINT, handle_exit)

    # Start robot logic in the background
    robot_thread = Thread(target=run_robot, daemon=True)
    robot_thread.start()

    # Run FastAPI (blocks until CTRL+C)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
