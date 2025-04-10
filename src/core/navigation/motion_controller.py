import time
import logging
import lgpio
from utils.logger import Logger
from config.pins import FRONT_LEFT, FRONT_RIGHT, REAR_LEFT, REAR_RIGHT, FINS, STBY
from config.motion import FIN_PWM_FREQ, PWM_FREQ, DEFAULT_DUTY, FIN_SPEED


class MotionController:
    def __init__(self):
        """
        Initialize the motion controller.

        - Sets up the logger for the motion control module.
        - Claims GPIO control for the motor-related pins.
        """
        
        self.L_EN = FINS["L_EN"]
        self.PWM_L = FINS["PWM_L"]
        self.PWM_R = FINS["PWM_R"]

        # Set up the logger
        motion_logger = Logger(name="motion", log_level=logging.INFO)
        self.logger = motion_logger.get_logger()

        self.chip = lgpio.gpiochip_open(0)  # Open GPIO chip 0
        self.stby = STBY  # Pin that enables/disables motor driver

        # Motor pin groups for each wheel (IN1, IN2, PWM)
        self.motors = {
            "FL": FRONT_LEFT,  # Front Left
            "FR": FRONT_RIGHT,  # Front Right
            "RL": REAR_LEFT,  # Rear Left
            "RR": REAR_RIGHT,  # Rear Right
        }

        # Direction patterns for movement
        self.patterns = {
            "forward": {"FL": 1, "FR": -1, "RL": 1, "RR": -1},  # Corrected: FR and RR are reversed
            "backward": {"FL": -1, "FR": 1, "RL": -1, "RR": 1},
            "strafe_left": {"FL": -1, "FR": 1, "RL": 1, "RR": -1},
            "strafe_right": {"FL": 1, "FR": -1, "RL": -1, "RR": 1},
            "rotate_right": {"FL": 1, "FR": 1, "RL": -1, "RR": -1},
            "rotate_left": {"FL": -1, "FR": -1, "RL": 1, "RR": 1},
            "diagonal_fr": {"FL": 1.0, "FR": 0.5, "RL": 0.5, "RR": 1.0},
            "diagonal_fl": {"FL": 0.5, "FR": 1.0, "RL": 1.0, "RR": 0.5},
            "diagonal_br": {"FL": -0.5, "FR": -1.0, "RL": -1.0, "RR": -0.5},
            "diagonal_bl": {"FL": -1.0, "FR": -0.5, "RL": -0.5, "RR": -1.0},
        }

        # Claim GPIO control over all motor-related pins
        self._claim_output_pins()
    
    def fin_on(self, speed):
        """Turn the fins on at the specified speed."""
        print(f"Enabling fins at speed {speed}")
        # Enable the left motor
        lgpio.gpio_write(self.chip, self.L_EN, 1)  # Activate L_EN pin
        # Set PWM for the left motor (right motor is not connected in this case)
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, FIN_SPEED)  # Right motor off (if not used)
        print(f"Fins enabled on L_EN: {self.L_EN}, PWM_L: {self.PWM_L}, speed: {speed}")

    def fin_off(self):
        """Turn the fins off."""
        print(f"Disabling fins")
        # Disable the fins by stopping PWM and turning off the enable pin
        lgpio.tx_pwm(self.chip, self.PWM_L, FIN_PWM_FREQ, 0)
        lgpio.tx_pwm(self.chip, self.PWM_R, FIN_PWM_FREQ, 0)
        lgpio.gpio_write(self.chip, self.L_EN, 0)
        print(f"Fins disabled on L_EN: {self.L_EN}, PWM_L: {self.PWM_L}")
        
    # Manual test for fins control
    def test_fins(self):
        """Test the fins manually by activating them with PWM."""
        print("Testing fins...")
    
        # Turn fins ON with 50% speed
        self.fin_on(speed=100)
        time.sleep(5)  # Keep the fins on for 2 seconds
    
        # Turn fins OFF
        self.fin_off()
        print("Fins test complete.")


    def _claim_output_pins(self):
        """
        Set all motor control pins (IN1, IN2, PWM) to output mode.
        Also claim the standby pin to enable the motor driver.
        Claims the fins' pins as well.
        """
        # Claim pins for the wheels (motor control)
        for group in self.motors.values():
            for pin in group.values():
                lgpio.gpio_claim_output(self.chip, pin)
        
        # Claim the standby pin (STBY)
        lgpio.gpio_claim_output(self.chip, self.stby)
        
        # Claim pins for the fins (PWM and L_EN)
        lgpio.gpio_claim_output(self.chip, self.L_EN)
        lgpio.gpio_claim_output(self.chip, self.PWM_L)
        lgpio.gpio_claim_output(self.chip, self.PWM_R)  # Even though not connected, claimed for consistency



    def _set_motor(self, in1, in2, pwm, direction, duty=DEFAULT_DUTY):
        """
        Low-level helper to control a single motor's direction and speed.

        Arguments:
        - in1, in2: Direction control pins for the motor
        - pwm: PWM pin for speed control
        - direction: 1 for forward, -1 for backward, 0 to stop
        - duty: PWM duty cycle (0-100)  controls motor speed
        """
        # Clamp the duty cycle between 0 and 100 to avoid invalid PWM values
        duty = max(0, min(100, duty))

        # Debugging log for direction and PWM signal
        self.logger.info(f"Setting motor with pins: IN1={in1}, IN2={in2}, PWM={pwm}, Direction={direction}, Duty={duty}")

        if direction == 1:
            lgpio.gpio_write(self.chip, in1, 1)
            lgpio.gpio_write(self.chip, in2, 0)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, duty)  # Ensure valid PWM frequency
        elif direction == -1:
            lgpio.gpio_write(self.chip, in1, 0)
            lgpio.gpio_write(self.chip, in2, 1)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, duty)  # Ensure valid PWM frequency
        else:
            lgpio.gpio_write(self.chip, in1, 0)
            lgpio.gpio_write(self.chip, in2, 0)
            lgpio.tx_pwm(self.chip, pwm, PWM_FREQ, 0)  # Ensure PWM is stopped


    def _move_by_pattern(self, pattern, speed):
        """
        Drive each motor according to the given movement pattern.
    
        pattern: Dict mapping motor IDs to direction multipliers (e.g., 1.0, -1.0, 0)
        speed: Base PWM duty cycle (0-100)
        """
        self.logger.info(f"Setting STBY to 1 (HIGH) to enable motor driver.")
        lgpio.gpio_write(self.chip, self.stby, 1)  # Enable motor driver
        
        # Loop through each motor and apply the movement pattern
        for motor_id, multiplier in pattern.items():
            pins = self.motors[motor_id]
            direction = 0 if multiplier == 0 else (1 if multiplier > 0 else -1)
            duty = abs(multiplier) * speed if multiplier != 0 else 0
            duty = max(0, min(100, duty))  # Ensure duty cycle is between 0 and 100
            self._set_motor(pins["IN1"], pins["IN2"], pins["PWM"], direction, duty)
    


    def move_forward(self, speed, duration=None):
        """Move the robot forward."""
        self.logger.info(f"Moving forward at speed {speed}.")
        self._move_by_pattern(self.patterns["forward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def move_backward(self, speed, duration=None):
        """Move the robot backward."""
        self.logger.info(f"Moving backward at speed {speed}.")
        self._move_by_pattern(self.patterns["backward"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def strafe_left(self, speed, duration=None):
        """Move the robot sideways to the left."""
        self.logger.info(f"Strafing left at speed {speed}.")
        self._move_by_pattern(self.patterns["strafe_left"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def strafe_right(self, speed, duration=None):
        """Move the robot sideways to the right."""
        self.logger.info(f"Strafing right at speed {speed}.")
        self._move_by_pattern(self.patterns["strafe_right"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_left(self, speed, duration=None):
        """Rotate the robot counter-clockwise."""
        self.logger.info(f"Rotating left at speed {speed}.")
        self._move_by_pattern(self.patterns["rotate_left"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def rotate_right(self, speed, duration=None):
        """Rotate the robot clockwise."""
        self.logger.info(f"Rotating right at speed {speed}.")
        self._move_by_pattern(self.patterns["rotate_right"], speed)
        if duration:
            time.sleep(duration)
            self.stop()

    def stop(self):
        """Stop all motors and reset motor pins."""
        self.logger.info("Stopping all motors.")
        for pins in self.motors.values():
            self._set_motor(pins["IN1"], pins["IN2"], pins["PWM"], direction=0)
        self.logger.info(f"Setting STBY to 0 (LOW) to disable motor driver.")
        lgpio.gpio_write(self.chip, self.stby, 0)
        time.sleep(1)  # Add a small delay to reset the motor driver


    def move(self, direction, speed, duration=None):
        """General movement by direction string (e.g., 'forward')."""
        pattern = self.patterns.get(direction)
        if pattern:
            self.logger.info(f"Moving {direction} at speed {speed}.")
            self._move_by_pattern(pattern, speed)
            if duration:
                time.sleep(duration)
                self.stop()
        else:
            self.logger.warning(f"Invalid direction: {direction}")

    def cleanup(self):
        """Stop all motors and release GPIO resources."""
        self.logger.info("Cleaning up GPIO resources.")
        self.stop()
        lgpio.gpiochip_close(self.chip)
