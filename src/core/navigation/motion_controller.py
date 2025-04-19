import time
import logging
import lgpio
from utils.logger import Logger
from config.pins import FRONT_LEFT, FRONT_RIGHT, REAR_LEFT, REAR_RIGHT, FINS, STBY
from config.motion import FIN_PWM_FREQ, PWM_FREQ, SPEED, FIN_SPEED


class MotionController:
    """
    MotionController manages wheel and fin motors via GPIO and PWM.
    """

    def __init__(self):
        """
        Initialize the motion controller.

        - Sets up the logger for the motion control module.
        - Claims GPIO control for the motor-related pins.
        - Loads default speed from config.
        """
        # default movement speed (0–100)
        self.speed = SPEED

        # fins pins
        self.L_EN = FINS["L_EN"]
        self.PWM_L = FINS["PWM_L"]
        self.PWM_R = FINS["PWM_R"]

        # standby pin
        self.stby = STBY

        # set up logger
        motion_logger = Logger(name="motion", log_level=logging.INFO)
        self.logger = motion_logger.get_logger()

        # open GPIO chip
        self.chip = lgpio.gpiochip_open(0)

        # wheel motor pin groups
        self.motors = {
            "FL": FRONT_LEFT,  # front left
            "FR": FRONT_RIGHT,  # front right
            "RL": REAR_LEFT,  # rear left
            "RR": REAR_RIGHT,  # rear right
        }

        # movement direction patterns
        self.patterns = {
            "forward": {"FL": 1, "FR": -1, "RL": 1, "RR": -1},
            "backward": {"FL": -1, "FR": 1, "RL": -1, "RR": 1},
            "rotate_right": {"FL": 1, "FR": 1, "RL": -1, "RR": -1},
            "rotate_left": {"FL": -1, "FR": -1, "RL": 1, "RR": 1},
        }

        # claim all GPIO output pins
        self._claim_output_pins()

    def fin_on(self, speed=None):
        """
        Turn the fins on at the specified speed (duty cycle).
        If speed is None, uses FIN_SPEED from config.
        """
        duty = speed if speed is not None else FIN_SPEED
        self.logger.info(f"Enabling fins at {duty}% duty")
        lgpio.gpio_write(self.chip, self.L_EN, 1)
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, duty)

    def fin_off(self):
        """
        Turn the fins off.
        """
        self.logger.info("Disabling fins")
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, 0)
        lgpio.gpio_write(self.chip, self.L_EN, 0)

    def test_fins(self):
        """
        Manual test for fins control: turns fins on for 2 seconds, then off.
        """
        self.logger.info("Testing fins...")
        self.fin_on()
        time.sleep(2)
        self.fin_off()
        self.logger.info("Fins test complete.")

    def _claim_output_pins(self):
        """
        Claim all motor and fin pins as outputs, and the standby pin.
        """
        # wheels
        for grp in self.motors.values():
            for pin in grp.values():
                lgpio.gpio_claim_output(self.chip, pin)
        # standby
        lgpio.gpio_claim_output(self.chip, self.stby)
        # fins
        lgpio.gpio_claim_output(self.chip, self.L_EN)
        lgpio.gpio_claim_output(self.chip, self.PWM_L)
        lgpio.gpio_claim_output(self.chip, self.PWM_R)

    def _set_motor(self, in1, in2, pwm, direction, duty=None):
        """
        Low-level helper to control a single motor's direction and speed.

        Arguments:
        - in1, in2: GPIO pins for direction control
        - pwm: GPIO pin for PWM speed control
        - direction:  1 = forward; -1 = backward; 0 = stop
        - duty:       PWM duty cycle (0–100). If None, uses self.speed.
        """
        if duty is None:
            duty = self.speed
        duty = max(0, min(100, duty))
        self.logger.info(
            f"Setting motor IN1={in1}, IN2={in2}, PWM={pwm}, "
            f"Dir={direction}, Duty={duty}"
        )

        if direction == 1:
            lgpio.gpio_write(self.chip, in1, 1)
            lgpio.gpio_write(self.chip, in2, 0)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, duty)
        elif direction == -1:
            lgpio.gpio_write(self.chip, in1, 0)
            lgpio.gpio_write(self.chip, in2, 1)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, duty)
        else:
            lgpio.gpio_write(self.chip, in1, 0)
            lgpio.gpio_write(self.chip, in2, 0)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, 0)

    def _move_by_pattern(self, pattern, speed=None):
        """
        Drive each wheel according to the pattern.

        pattern: dict of motor IDs to multipliers (e.g. 1, -1, 0.5)
        speed:   base duty cycle (0–100). If None, uses self.speed.
        """
        base = speed if speed is not None else self.speed
        self.logger.info("Enabling motor driver (STBY HIGH)")
        lgpio.gpio_write(self.chip, self.stby, 1)

        for motor_id, mul in pattern.items():
            pins = self.motors[motor_id]
            direction = 1 if mul > 0 else -1 if mul < 0 else 0
            duty = abs(mul) * base
            self._set_motor(pins["IN1"], pins["IN2"], pins["PWM"], direction, duty)

    def move_forward(self, speed=None, duration=None):
        """
        Move forward at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Moving forward @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["forward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def move_backward(self, speed=None, duration=None):
        """
        Move backward at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Moving backward @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["backward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def strafe_left(self, speed=None, duration=None):
        """
        Strafe left at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Strafing left @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["strafe_left"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def strafe_right(self, speed=None, duration=None):
        """
        Strafe right at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Strafing right @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["strafe_right"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_left(self, speed=None, duration=None):
        """
        Rotate counter-clockwise at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Rotating left @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["rotate_left"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_right(self, speed=None, duration=None):
        """
        Rotate clockwise at given speed (or default). Optionally for a duration.
        """
        self.logger.info(f"Rotating right @ {speed or self.speed}%")
        self._move_by_pattern(self.patterns["rotate_right"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def stop(self):
        """
        Stop all wheel motors and disable driver.
        """
        self.logger.info("Stopping all motors")
        for pins in self.motors.values():
            self._set_motor(pins["IN1"], pins["IN2"], pins["PWM"], direction=0, duty=0)
        self.logger.info("Disabling motor driver (STBY LOW)")
        lgpio.gpio_write(self.chip, self.stby, 0)
        time.sleep(0.1)

    def move(self, direction, speed=None, duration=None):
        """
        General move by direction string ('forward', 'rotate_left', etc.).
        """
        pattern = self.patterns.get(direction)
        if not pattern:
            self.logger.warning(f"Invalid direction: {direction}")
            return
        self.logger.info(f"Moving {direction} @ {speed or self.speed}%")
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def cleanup(self):
        """
        Stop all motors and release GPIO resources.
        """
        self.logger.info("Cleaning up GPIO resources")
        self.stop()
        lgpio.gpiochip_close(self.chip)
