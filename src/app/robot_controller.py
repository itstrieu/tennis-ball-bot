import logging
from utils.logger import Logger
import time
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    SEARCH_ROTATE_DURATION,
    CENTER_ROTATE_SPEED,
    NO_BALL_PAUSE,
    SWITCH_DELAY,
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
        self.search_direction = "left"  # Start searching to the left
        self.search_cycles = 0

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

            while True:
                frame = self.vision.get_frame()
                bboxes = self.vision.detect_ball(frame)

                if not bboxes:
                    # No balls detected, handle this case
                    action = self.decider.handle_no_ball()

                    if action == "search":
                        self._search_for_balls()
                    continue

                # Found at least one ball
                largest = max(bboxes, key=self.vision.calculate_area)
                offset = self.vision.get_center_offset(largest)
                area = self.vision.calculate_area(largest)

                # Decide how to move
                direction = self.decider.decide(offset, area)

                # Execute the movement if it's different from current
                if direction != self.current_direction:
                    self._move(direction)
                    self.current_direction = direction

        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received: stopping robot...")
        finally:
            self.motion.stop()
            self.logger.info("RobotController shutdown complete.")

    def _search_for_balls(self):
        """Search for tennis balls by rotating"""
        self.logger.info(f"No balls found. Searching: rotating {self.search_direction}")

        # Switch search direction periodically for better coverage
        self.search_cycles += 1
        if self.search_cycles >= 3:
            self.search_cycles = 0
            # Toggle search direction
            self.search_direction = (
                "right" if self.search_direction == "left" else "left"
            )

            # Occasionally move forward when searching
            if self.search_cycles % 4 == 0:
                self.logger.info("Moving forward to search new area")
                self.motion.move_forward()
                time.sleep(1.0)  # Move forward for 1 second
                self.motion.stop()

        # Execute the rotation
        if self.search_direction == "left":
            self.motion.rotate_left(
                speed=SEARCH_ROTATE_SPEED, duration=SEARCH_ROTATE_DURATION
            )
        else:
            self.motion.rotate_right(
                speed=SEARCH_ROTATE_SPEED, duration=SEARCH_ROTATE_DURATION
            )

        # Update current direction
        self.current_direction = "searching"

    def _move(self, direction):
        """
        Execute movement based on direction.
        """
        # First stop if we're changing directions
        if self.current_direction != direction:
            self.motion.stop()
            time.sleep(SWITCH_DELAY)

        if direction == "forward":
            self.logger.info("Moving forward")
            self.motion.move_forward()
        elif direction == "left":
            self.logger.info(f"Rotating left @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_left(speed=CENTER_ROTATE_SPEED)
        elif direction == "right":
            self.logger.info(f"Rotating right @ {CENTER_ROTATE_SPEED}%")
            self.motion.rotate_right(speed=CENTER_ROTATE_SPEED)
        elif direction == "stop":
            self.logger.info("Stopping")
            self.motion.stop()
