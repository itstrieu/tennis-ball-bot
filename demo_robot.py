from threading import Thread
import uvicorn
import logging

from src.app.camera_manager import get_camera
from src.app.robot_controller import RobotController
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.streaming import stream_client
from src.streaming.stream_client import app
from src.config import vision as vision_config, motion as motion_config


def main():
    # Only ONE camera init
    camera = get_camera()

    # Set up robot modules
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

    # Pass shared camera + vision to stream client
    stream_client.set_shared_components(camera, vision)

    # Start stream in background
    stream_thread = Thread(target=start_stream, daemon=True)
    stream_thread.start()

    # Run robot
    robot.run()

    # Cleanup
    motion.fin_off()
    camera.stop()


if __name__ == "__main__":
    main()
