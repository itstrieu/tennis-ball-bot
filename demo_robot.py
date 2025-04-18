import logging
from threading import Thread
import uvicorn

from picamera2 import Picamera2
from src.app.camera_manager import get_camera
from src.app.robot_controller import RobotController
from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.streaming.stream_client import app
from src.config import vision as vision_config, motion as motion_config


def start_stream():
    # this will call get_camera() --- which returns the same Picamera2 instance
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def main():
    # initialize camera once
    camera = get_camera()

    # set up robot
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

    # start MJPEG stream in background thread
    stream_thread = Thread(target=start_stream, daemon=True)
    stream_thread.start()

    # run your control loop (blocks until you Ctrl+C)
    robot.run()

    # cleanup
    motion.fin_off()
    camera.stop()


if __name__ == "__main__":
    main()
