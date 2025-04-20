import logging
from utils.logger import Logger
import time
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    SEARCH_ROTATE_DURATION,
    CENTER_ROTATE_SPEED,
    NO_BALL_PAUSE,
    SWITCH_DELAY,
    SPEED,
)
from src.app.camera_manager import get_camera


class RobotController:
    """
    RobotController ties together motion, vision, and decision modules,
    looping on camera input and driving the robot accordingly.
    """

    def __init__(self, motion_controller, vision_tracker, movement_decider):
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider
        self.current_direction = None

        # Set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

    def run(self):
        """
        Main control loop:
        - capture frame
        - detect tennis balls
        - decide movement
        - execute movement

        Press Ctrl+C to exit.
        """
        self.logger.info("RobotController started. Press Ctrl+C to stop.")
        try:
            self.motion.stop()
            no_ball_frames = 0

            while True:
                frame = self.vision.get_frame()  # Get the frame from the shared camera
                bboxes = self.vision.detect_ball(frame)

                if not bboxes:
                    no_ball_frames += 1
                    # Only take action if we've missed the ball for several frames
                    if no_ball_frames >= 3:
                        self.logger.info(
                            "❌ No tennis balls detected for multiple frames."
                        )
                        if self.current_direction != "searching":
                            self.motion.stop()
                            time.sleep(NO_BALL_PAUSE)
                            self.logger.info(
                                f"Searching: rotate left @ {SEARCH_ROTATE_SPEED}% for {SEARCH_ROTATE_DURATION}s"
                            )
                            self.motion.rotate_left(
                                speed=SEARCH_ROTATE_SPEED,
                                duration=SEARCH_ROTATE_DURATION,
                            )
                            self.current_direction = "searching"
                    continue
                else:
                    no_ball_frames = 0  # Reset counter when we see a ball

                largest = max(bboxes, key=self.vision.calculate_area)
                offset = self.vision.get_center_offset(largest)
                area = self.vision.calculate_area(largest)
                new_direction = self.decider.decide(offset, area)

                self.logger.debug(
                    f"Offset: {offset:.2f}, Area: {area:.2f}, Direction: {new_direction}"
                )

                # Only change direction if it's actually different
                if new_direction != self.current_direction:
                    self._move(new_direction)
                    self.current_direction = new_direction

        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received: stopping robot...")
        finally:
            self.motion.stop()
            self.logger.info("RobotController shutdown complete.")

    def _move(self, direction):
        """
        Translate a direction string into a motion_controller call.
        """
        # Only stop fully when switching between forward and turning
        significant_change = False
        if (
            self.current_direction in ["forward"]
            and direction in ["left", "right", "gentle_left", "gentle_right"]
        ) or (
            self.current_direction in ["left", "right", "gentle_left", "gentle_right"]
            and direction == "forward"
        ):
            self.motion.stop()
            time.sleep(SWITCH_DELAY / 2)  # Reduced delay time
            significant_change = True

        if direction == "left":
            self.logger.info(f"Rotating left @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_left(speed=CENTER_ROTATE_SPEED)
        elif direction == "gentle_left":
            gentle_speed = CENTER_ROTATE_SPEED // 2
            self.logger.info(f"Rotating left gently @ {gentle_speed}%")
            self.motion.rotate_left(speed=gentle_speed)
        elif direction == "right":
            self.logger.info(f"Rotating right @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_right(speed=CENTER_ROTATE_SPEED)
        elif direction == "gentle_right":
            gentle_speed = CENTER_ROTATE_SPEED // 2
            self.logger.info(f"Rotating right gently @ {gentle_speed}%")
            self.motion.rotate_right(speed=gentle_speed)
        elif direction == "forward":
            self.logger.info("Moving forward @ default speed")
            self.motion.move_forward()
        elif direction == "stop":
            self.logger.info("Stopping robot")
            self.motion.stop()
        else:
            self.logger.info("Stopping: unknown direction")
            self.motion.stop()
