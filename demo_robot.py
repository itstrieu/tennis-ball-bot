# demo_robot.py

from src.core.navigation.motion_controller import MotionController
from src.core.detection.vision_tracker import VisionTracker
from src.core.strategy.movement_decider import MovementDecider
from src.app.robot_controller import RobotController

from src.config import motion as motion_config


def main():
    print("Starting Tennis Ball Bot Demo...")

    motion = MotionController()

    # Turn on fins at the start of the demo
    motion.fin_on(speed=motion_config.FIN_SPEED)

    vision = VisionTracker(
        model_path=vision_config.MODEL_PATH,
        frame_width=vision_config.FRAME_WIDTH,
        camera_offset=vision_config.CAMERA_OFFSET,
    )

    strategy = MovementDecider(
        target_area=demo_config.TARGET_AREA,
        center_threshold=demo_config.CENTER_THRESHOLD,
    )

    robot = RobotController(motion, vision, strategy)
    robot.run()

    # Turn off fins when the demo finishes
    motion.fin_off()


if __name__ == "__main__":
    main()
