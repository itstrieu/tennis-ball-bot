"""
robot_controller.py

Main control logic for the robot. Coordinates vision, motion, and decision-making
to perform search-and-retrieve behaviors for tennis balls using a camera feed.
"""

import logging
import time
from utils.logger import Logger
from src.config.motion import (
    SEARCH_ROTATE_SPEED,
    CENTER_ROTATE_SPEED,
    SPEED,
)
from src.app.camera_manager import get_camera


class RobotController:
    """
    Coordinates motion, vision tracking, and decision logic to control the robot's behavior.

    Executes a cyclic process:
    - Rotates to scan surroundings.
    - Waits for ball detection.
    - Approaches and retrieves ball when found.
    - Resumes scanning after completing the retrieval cycle.

    Attributes:
        motion: Motion controller module for moving/rotating the robot.
        vision: Vision module for detecting balls via camera input.
        decider: MovementDecider instance for deciding how to respond to detections.
        dev_mode (bool): Whether development slowdown is active.
    """

    def __init__(
        self, motion_controller, vision_tracker, movement_decider, dev_mode=False
    ):
        self.motion = motion_controller
        self.vision = vision_tracker
        self.decider = movement_decider
        self.current_direction = None

        # Movement duration parameters
        self.forward_step_time = 1.0
        self.small_forward_time = 0.8
        self.micro_forward_time = 0.7
        self.turn_step_time = 0.3
        self.micro_turn_time = 0.1

        self.assess_pause_time = 0.2
        self.approach_speed = SPEED

        # Dev mode slowdown factor
        self.dev_mode = dev_mode
        self.dev_slowdown = 2.0 if dev_mode else 1.0  # adjust globally here

        self.last_area = 0  # For deciding post-ball-disappearance behavior

        # Set up logger
        robot_logger = Logger(name="robot", log_level=logging.INFO)
        self.logger = robot_logger.get_logger()

    def run(self):
        """
        Main control loop.

        States:
            - scanning: Rotates the robot to search for a ball.
            - waiting_for_ball: Waits and reacts to ball detection.
            - wait_then_restart: Waits briefly before restarting the scan cycle.

        The loop continues until interrupted (e.g., Ctrl+C).
        """
        self.logger.info("RobotController started. Press Ctrl+C to stop.")
        try:
            self.motion.stop()
            state = "scanning"
            rotate_steps = 0
            max_rotate_steps = int(360 / 30)  # Assuming ~30° per step

            while True:
                if state == "scanning":
                    if rotate_steps < max_rotate_steps:
                        self.logger.info(
                            f"Rotating right (step {rotate_steps + 1}/{max_rotate_steps})"
                        )
                        self.motion.rotate_right(speed=SEARCH_ROTATE_SPEED)
                        time.sleep(0.3 * self.dev_slowdown)
                        self.motion.stop()
                        rotate_steps += 1
                    else:
                        self.logger.info("Full rotation complete. Waiting for ball.")
                        state = "waiting_for_ball"

                elif state == "waiting_for_ball":
                    frame = self.vision.get_frame()
                    bboxes = self.vision.detect_ball(frame)

                    if bboxes:
                        largest = max(bboxes, key=self.vision.calculate_area)
                        offset = self.vision.get_center_offset(largest)
                        area = self.vision.calculate_area(largest)

                        direction = self.decider.decide(offset, area)
                        self._execute_step(direction)

                        self.last_area = area
                        self.motion.stop()
                        time.sleep(self.assess_pause_time * self.dev_slowdown)

                    else:
                        if self.last_area > self.decider.target_area * 0.8:
                            self.logger.info(
                                "Ball likely just out of view — pushing forward."
                            )
                            self.motion.move_forward(speed=SPEED)
                            time.sleep(1.0 * self.dev_slowdown)
                            self.motion.stop()
                            self.last_area = 0
                            state = "wait_then_restart"
                        else:
                            self.logger.info("No ball — standing by.")
                            time.sleep(0.5 * self.dev_slowdown)

                elif state == "wait_then_restart":
                    self.logger.info("Waiting 2 seconds before restarting scan.")
                    time.sleep(2.0 * self.dev_slowdown)
                    rotate_steps = 0
                    state = "scanning"

        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received: stopping robot...")
        finally:
            self.motion.stop()
            self.logger.info("RobotController shutdown complete.")

    def _execute_step(self, direction):
        """
        Executes a discrete movement step based on the provided direction command.

        Args:
            direction (str): Movement decision returned by the MovementDecider.
                             One of ['step_forward', 'small_forward', 'micro_forward',
                             'step_left', 'micro_left', 'step_right', 'micro_right', 'stop'].
        """
        reduced_speed = int(SPEED * 0.7)
        micro_speed = int(SPEED * 0.5)

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
            time.sleep(1.0)
