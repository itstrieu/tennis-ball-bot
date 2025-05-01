import time
import logging
import lgpio
from utils.logger import Logger
from config.pins import FRONT_LEFT, FRONT_RIGHT, REAR_LEFT, REAR_RIGHT, FINS, STBY
from config.motion import FIN_PWM_FREQ, PWM_FREQ, SPEED, FIN_SPEED


class MotionController:
    """
    MotionController manages wheel and fin motors via GPIO and PWM.
    Front wheels are standard; rear wheels have omnidirectional rollers but are still driven.

    You can adjust power balance between left/right wheels using
    `left_scale` and `right_scale` attributes.
    """

    def __init__(self):
        """
        Initialize the motion controller:
        - Sets up the logger
        - Claims GPIO pins
        - Loads default speed and scaling factors
        """
        # base speed (0–100)
        self.speed = SPEED
        # left/right power scaling (1.0 = no change)
        self.left_scale = 1.0
        self.right_scale = 1.0

        # fin control pins
        self.L_EN = FINS["L_EN"]
        self.PWM_L = FINS["PWM_L"]
        self.PWM_R = FINS["PWM_R"]
        # standby pin
        self.stby = STBY

        # logger
        motion_logger = Logger(name="motion", log_level=logging.INFO)
        self.logger = motion_logger.get_logger()
        # open gpio chip
        self.chip = lgpio.gpiochip_open(0)

        # motor pin groups
        self.motors = {
            "FL": FRONT_LEFT,
            "FR": FRONT_RIGHT,
            "RL": REAR_LEFT,
            "RR": REAR_RIGHT,
        }

        # movement patterns
        self.patterns = {
            "forward": {"FL": 1, "FR": -1, "RL": 1, "RR": -1},
            "backward": {"FL": -1, "FR": 1, "RL": -1, "RR": 1},
            "rotate_right": {"FL": 1, "FR": 1, "RL": 1, "RR": 1},
            "rotate_left": {"FL": -1, "FR": -1, "RL": -1, "RR": -1},
        }

        self._claim_output_pins()

    def set_balance(self, left_scale: float, right_scale: float):
        """
        Adjust power scaling factors for left and right wheels.
        Values >1.0 boost power; <1.0 reduce.
        """
        self.left_scale = left_scale
        self.right_scale = right_scale
        self.logger.info(f"Left/right power scales set to {left_scale}/{right_scale}")

    def _apply_scale(self, motor_id: str, duty: float) -> float:
        """
        Apply left/right scaling to the raw duty.
        """
        if motor_id.startswith("L"):
            return duty * self.left_scale
        else:
            return duty * self.right_scale

    def _claim_output_pins(self):
        """Claim GPIO pins for all motors, fins, and standby."""
        for grp in self.motors.values():
            for pin in grp.values():
                lgpio.gpio_claim_output(self.chip, pin)
        lgpio.gpio_claim_output(self.chip, self.stby)
        lgpio.gpio_claim_output(self.chip, self.L_EN)
        lgpio.gpio_claim_output(self.chip, self.PWM_L)
        lgpio.gpio_claim_output(self.chip, self.PWM_R)

    def _set_motor(self, in1, in2, pwm, direction, duty):
        """Low-level motor control."""
        # clamp and apply scale
        duty = max(0, min(100, duty))
        lgpio.gpio_write(self.chip, in1, 1 if direction > 0 else 0)
        lgpio.gpio_write(self.chip, in2, 1 if direction < 0 else 0)
        lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, duty)

    def _move_by_pattern(self, pattern, speed=None):
        """Drive wheels per pattern with optional base speed."""
        base = speed if speed is not None else self.speed
        lgpio.gpio_write(self.chip, self.stby, 1)
        for motor_id, direction in pattern.items():
            raw_duty = abs(direction) * base
            scaled = self._apply_scale(motor_id, raw_duty)
            pins = self.motors[motor_id]
            # direction multiplier preserves sign
            self._set_motor(pins["IN1"], pins["IN2"], pins["PWM"], direction, scaled)

    def move_forward(self, speed=None, duration=None):
        self.logger.info("Moving forward")
        self._move_by_pattern(self.patterns["forward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def move_backward(self, speed=None, duration=None):
        self.logger.info("Moving backward")
        self._move_by_pattern(self.patterns["backward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_left(self, speed=None, duration=None):
        self.logger.info("Rotating left")
        self._move_by_pattern(self.patterns["rotate_left"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_right(self, speed=None, duration=None):
        self.logger.info("Rotating right")
        self._move_by_pattern(self.patterns["rotate_right"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def stop(self):
        """Halt motors and disable driver."""
        lgpio.gpio_write(self.chip, self.stby, 0)
        for pins in self.motors.values():
            lgpio.tx_pwm(self.chip, pins["PWM"], PWM_FREQ, 0)

    def fin_on(self, speed=None):
        duty = speed if speed is not None else FIN_SPEED
        lgpio.gpio_write(self.chip, self.L_EN, 1)
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, duty)

    def fin_off(self):
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, 0)
        lgpio.gpio_write(self.chip, self.L_EN, 0)

    def cleanup(self):
        self.stop()
        lgpio.gpiochip_close(self.chip)
