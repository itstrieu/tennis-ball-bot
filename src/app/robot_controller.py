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
        self.search_direction = "left"  # Start searching to the left
        self.search_cycles = 0

        # Movement duration parameters - multiple step sizes
        self.forward_step_time = 0.4  # Standard forward step time
        self.small_forward_time = 0.2  # Smaller step when getting close
        self.micro_forward_time = 0.1  # Micro step when very close

        self.turn_step_time = 0.3  # Standard turn time
        self.micro_turn_time = 0.1  # Micro turn when close to target

        self.assess_pause_time = 0.2  # Time to pause and assess after movement
        self.approach_speed = SPEED  # Default approach speed

        # Set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

    def run(self):
        """
        Main control loop with cautious approach logic
        """
        self.logger.info("RobotController started. Press Ctrl+C to stop.")
        try:
            self.motion.stop()

            while True:
                # Get frame and detect balls
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

                # Execute the stepped movement
                self._execute_step(direction)

                # After executing a step, always stop and assess
                self.motion.stop()
                time.sleep(self.assess_pause_time)

        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received: stopping robot...")
        finally:
            self.motion.stop()
            self.logger.info("RobotController shutdown complete.")

    def _search_for_balls(self):
        """Search for tennis balls by rotating in steps"""
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
            if self.search_cycles % 6 == 0:  # Less frequent forward movements
                self.logger.info("Moving forward to search new area")
                self.motion.move_forward()
                time.sleep(0.8)  # Move forward briefly
                self.motion.stop()
                time.sleep(self.assess_pause_time)  # Pause to assess

        # Execute the rotation step
        if self.search_direction == "left":
            self.motion.rotate_left(speed=SEARCH_ROTATE_SPEED)
            time.sleep(SEARCH_ROTATE_DURATION)
            self.motion.stop()
        else:
            self.motion.rotate_right(speed=SEARCH_ROTATE_SPEED)
            time.sleep(SEARCH_ROTATE_DURATION)
            self.motion.stop()

        # Pause briefly to assess after each search movement
        time.sleep(self.assess_pause_time)

    def _execute_step(self, direction):
        """
        Execute movement with different step sizes based on proximity to target
        """
        reduced_speed = int(SPEED * 0.7)  # 70% of normal speed for careful approach
        micro_speed = int(SPEED * 0.5)  # 50% of normal speed for micro adjustments

        if direction == "step_forward":
            self.logger.info(f"Step forward for {self.forward_step_time}s @ {SPEED}%")
            self.motion.move_forward(speed=SPEED)
            time.sleep(self.forward_step_time)

        elif direction == "small_forward":
            self.logger.info(
                f"Small step forward for {self.small_forward_time}s @ {reduced_speed}%"
            )
            self.motion.move_forward(speed=reduced_speed)
            time.sleep(self.small_forward_time)

        elif direction == "micro_forward":
            self.logger.info(
                f"Micro step forward for {self.micro_forward_time}s @ {micro_speed}%"
            )
            self.motion.move_forward(speed=micro_speed)
            time.sleep(self.micro_forward_time)

        elif direction == "step_left":
            self.logger.info(
                f"Step left for {self.turn_step_time}s @ {CENTER_ROTATE_SPEED}%"
            )
            self.motion.rotate_left(speed=CENTER_ROTATE_SPEED)
            time.sleep(self.turn_step_time)

        elif direction == "micro_left":
            self.logger.info(
                f"Micro step left for {self.micro_turn_time}s @ {micro_speed}%"
            )
            self.motion.rotate_left(speed=micro_speed)
            time.sleep(self.micro_turn_time)

        elif direction == "step_right":
            self.logger.info(
                f"Step right for {self.turn_step_time}s @ {CENTER_ROTATE_SPEED}%"
            )
            self.motion.rotate_right(speed=CENTER_ROTATE_SPEED)
            time.sleep(self.turn_step_time)

        elif direction == "micro_right":
            self.logger.info(
                f"Micro step right for {self.micro_turn_time}s @ {micro_speed}%"
            )
            self.motion.rotate_right(speed=micro_speed)
            time.sleep(self.micro_turn_time)

        elif direction == "stop":
            self.logger.info("Stopping (target reached)")
            self.motion.stop()
            # Add a longer pause when we reach a target (collected a ball)
            time.sleep(1.0)  # Longer pause at collection
