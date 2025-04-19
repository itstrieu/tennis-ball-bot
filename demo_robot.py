# demo_robot.py

from picamera2 import Picamera2

from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.app.robot_controller import RobotController

from src.config import vision as vision_config
from src.config import motion as motion_config


def main():
    print("Starting Tennis Ball Bot Demo...")

    motion = MotionController()

    # Turn on fins at the start of the demo
    motion.fin_on(speed=motion_config.FIN_SPEED)

    # Shared camera instance
    camera = Picamera2()
    camera.configure(
        camera.create_preview_configuration(
            main={"format": "BGR888", "size": (640, 480)}
        )
    )
    camera.start()

    vision = VisionTracker(
        model_path=vision_config.MODEL_PATH,
        frame_width=vision_config.FRAME_WIDTH,
        camera_offset=vision_config.CAMERA_OFFSET,
        camera=camera,  # Pass camera explicitly
    )

    strategy = MovementDecider(
        target_area=motion_config.TARGET_AREA,
        center_threshold=motion_config.CENTER_THRESHOLD,
    )

    robot = RobotController(motion, vision, strategy)
    robot.run()

    # Turn off fins when the demo finishes
    motion.fin_off()
    camera.stop()


if __name__ == "__main__":
    main()
