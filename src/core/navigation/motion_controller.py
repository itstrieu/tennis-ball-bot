"""
motion_controller.py

Controls the robot's motion through GPIO and PWM.
Manages wheel and fin motors for movement and steering.
"""

import time
import logging
import lgpio
from typing import Dict, Optional, Literal
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config


class MotionController:
    """
    MotionController manages wheel and fin motors via GPIO and PWM.
    Front wheels are standard; rear wheels have omnidirectional rollers but are still driven.

    You can adjust power balance between left/right wheels using
    `left_scale` and `right_scale` attributes.

    Attributes:
        config: RobotConfig instance for configuration values
        speed: Base speed (0-100)
        left_scale: Left wheel power scaling (1.0 = no change)
        right_scale: Right wheel power scaling (1.0 = no change)
        logger: Logger instance
    """

    def __init__(self, config=None):
        """
        Initialize the motion controller.
        
        Args:
            config: Optional RobotConfig instance
            
        Raises:
            RobotError: If GPIO initialization fails
        """
        self.config = config or default_config
        self.speed = self.config.speed
        self.left_scale = 1.0
        self.right_scale = 1.0
        self._is_moving = False
        self._gpio_handle = None
        self._pins_claimed = False
        self.logger = Logger.get_logger(name="motion", log_level=logging.INFO)
        
        try:
            self._initialize_gpio()
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {str(e)}")
            raise RobotError(f"GPIO initialization failed: {str(e)}", "motion_controller")

    @with_error_handling("motion_controller")
    def _initialize_gpio(self):
        """Initialize GPIO and claim pins."""
        if self._gpio_handle is None:
            self._gpio_handle = lgpio.gpiochip_open(0)
            
        if not self._pins_claimed:
            self._claim_output_pins()
            self._pins_claimed = True
            
        # Enable motor driver by setting standby pin to 1
        standby_pin = self.config.pins["standby"]
        result = lgpio.gpio_write(self._gpio_handle, standby_pin, 1)
        if result < 0:
            self.logger.error(f"Failed to enable motor driver (standby pin): {result}")
        else:
            self.logger.info("Motor driver enabled (standby pin set to 1)")
            
        self.logger.info("GPIO initialized successfully")

    @with_error_handling("motion_controller")
    def set_balance(self, left_scale: float, right_scale: float):
        """
        Adjust power balance between left and right wheels.
        
        Args:
            left_scale: Left wheel power scaling (1.0 = no change)
            right_scale: Right wheel power scaling (1.0 = no change)
        """
        self.left_scale = max(0.0, min(1.0, left_scale))
        self.right_scale = max(0.0, min(1.0, right_scale))
        self.logger.debug(f"Set wheel balance: left={self.left_scale}, right={self.right_scale}")

    @with_error_handling("motion_controller")
    def _apply_scale(self, motor_id: str, duty: float) -> float:
        """
        Apply power scaling to motor duty cycle.
        
        Args:
            motor_id: Motor identifier ("left" or "right")
            duty: Base duty cycle
            
        Returns:
            Scaled duty cycle
        """
        if motor_id.startswith("left"):
            return duty * self.left_scale
        return duty * self.right_scale

    @with_error_handling("motion_controller")
    def _claim_output_pins(self):
        """Claim and configure GPIO output pins."""
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "motion_controller")
            
        # Claim and configure pins
        for motor_pins in self.config.pins.values():
            if isinstance(motor_pins, dict):
                # Handle nested pin dictionaries (motors)
                for pin_name, pin in motor_pins.items():
                    result = lgpio.gpio_claim_output(self._gpio_handle, pin)
                    if result < 0:
                        self.logger.error(f"Failed to claim pin {pin_name} ({pin}): {result}")
                    else:
                        self.logger.debug(f"Successfully claimed pin {pin_name} ({pin})")
            else:
                # Handle single pin values (standby, etc.)
                result = lgpio.gpio_claim_output(self._gpio_handle, motor_pins)
                if result < 0:
                    self.logger.error(f"Failed to claim pin {motor_pins}: {result}")
                else:
                    self.logger.debug(f"Successfully claimed pin {motor_pins}")
            
        self.logger.info("Output pins claimed successfully")

    @with_error_handling("motion_controller")
    def _set_motor(self, in1: int, in2: int, pwm: int, direction: int, duty: float):
        """
        Set motor state and PWM duty cycle.
        
        Args:
            in1: First control pin
            in2: Second control pin
            pwm: PWM pin
            direction: Direction (1 = forward, -1 = backward, 0 = stop)
            duty: PWM duty cycle (0-100)
        """
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "motion_controller")
            
        self.logger.info(f"_set_motor called with in1={in1}, in2={in2}, pwm={pwm}, direction={direction}, duty={duty}")
            
        # Set direction
        if direction == 0:
            # Stop motor by setting both control pins to 0
            result1 = lgpio.gpio_write(self._gpio_handle, in1, 0)
            result2 = lgpio.gpio_write(self._gpio_handle, in2, 0)
            self.logger.debug(f"Stopping motor: in1={in1}({result1}), in2={in2}({result2})")
        else:
            # Set direction for forward/backward
            in1_val = 1 if direction > 0 else 0
            in2_val = 0 if direction > 0 else 1
            result1 = lgpio.gpio_write(self._gpio_handle, in1, in1_val)
            result2 = lgpio.gpio_write(self._gpio_handle, in2, in2_val)
            self.logger.debug(f"Setting motor direction: in1={in1}({result1})={in1_val}, in2={in2}({result2})={in2_val}")
        
        # Set PWM with higher frequency (20kHz)
        result = lgpio.tx_pwm(self._gpio_handle, pwm, 20000, duty)
        if result < 0:
            self.logger.error(f"Failed to set PWM on pin {pwm}: {result}")
        else:
            self.logger.debug(f"Set PWM on pin {pwm} to {duty}%")
            # Small delay to ensure PWM takes effect
            time.sleep(0.1)

    @with_error_handling("motion_controller")
    def _move_by_pattern(self, pattern: Dict[str, int], speed: Optional[int] = None):
        """
        Move motors according to a pattern.
        
        Args:
            pattern: Dictionary mapping motor IDs to directions
            speed: Optional speed override
        """
        if not self._pins_claimed:
            self._initialize_gpio()
            
        speed = speed or self.speed
        self._is_moving = True
        
        try:
            # Enable motor driver
            standby_pin = self.config.pins["standby"]
            result = lgpio.gpio_write(self._gpio_handle, standby_pin, 1)
            if result < 0:
                self.logger.error(f"Failed to enable motor driver (standby pin): {result}")
                raise RobotError("Failed to enable motor driver", "motion_controller")
            self.logger.debug("Motor driver enabled (standby pin set to 1)")
            
            for motor_id, direction in pattern.items():
                pins = self.config.pins[motor_id]
                duty = self._apply_scale(motor_id, speed)
                self._set_motor(pins["in1"], pins["in2"], pins["pwm"], direction, duty)
                
            self.logger.debug(f"Moving with pattern: {pattern}, speed: {speed}")
        except Exception as e:
            self._is_moving = False
            # Ensure motor driver is disabled on error
            self._disable_motor_driver()
            raise

    @with_error_handling("motion_controller")
    def move_forward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Move forward at specified speed for optional duration."""
        self.logger.info(f"move_forward called with speed={speed}, duration={duration}")
        pattern = {
            "front_left": -1,  # FL
            "front_right": 1,  # FR
            "rear_left": 1,    # RL
            "rear_right": -1   # RR
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def move_backward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Move backward at specified speed for optional duration."""
        self.logger.info(f"move_backward called with speed={speed}, duration={duration}")
        pattern = {
            "front_left": 1,   # FL
            "front_right": -1, # FR
            "rear_left": -1,   # RL
            "rear_right": 1    # RR
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def rotate_left(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Rotate left at specified speed for optional duration."""
        self.logger.info(f"rotate_left called with speed={speed}, duration={duration}")
        pattern = {
            "front_left": 1,   # FL
            "front_right": 1,  # FR
            "rear_left": 1,    # RL
            "rear_right": 1    # RR
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def rotate_right(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Rotate right at specified speed for optional duration."""
        self.logger.info(f"rotate_right called with speed={speed}, duration={duration}")
        pattern = {
            "front_left": -1,  # FL
            "front_right": -1, # FR
            "rear_left": -1,   # RL
            "rear_right": -1   # RR
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def stop(self, speed: int = 0, duration: Optional[float] = None):
        """Stop all motors."""
        self.logger.info("stop called")
        if self._is_moving:
            # First stop all motors
            for motor_id in ["front_left", "front_right", "rear_left", "rear_right"]:
                pins = self.config.pins[motor_id]
                lgpio.tx_pwm(self._gpio_handle, pins["pwm"], self.config.pwm_freq, 0)
            
            # Then disable motor driver
            self._disable_motor_driver()
            
            self._is_moving = False
            self.logger.debug("Motors stopped")
            
        if duration:
            time.sleep(duration)

    @with_error_handling("motion_controller")
    def _disable_motor_driver(self):
        """Disable motor driver by setting standby pin to 0."""
        if self._gpio_handle is None:
            return
            
        standby_pin = self.config.pins["standby"]
        result = lgpio.gpio_write(self._gpio_handle, standby_pin, 0)
        if result < 0:
            self.logger.error(f"Failed to disable motor driver (standby pin): {result}")
        else:
            self.logger.debug("Motor driver disabled (standby pin set to 0)")

    @with_error_handling("motion_controller")
    def fin_on(self, speed: Optional[int] = None):
        """Activate fins at specified speed."""
        if not self._pins_claimed:
            self._initialize_gpio()
            
        speed = speed or self.config.fin_speed
        pins = self.config.pins["fins"]
        
        try:
            lgpio.gpio_write(self._gpio_handle, pins["L_EN"], 1)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_L"], self.config.fin_pwm_freq, 0)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_R"], self.config.fin_pwm_freq, speed)
            self.logger.debug(f"Fins activated at speed {speed}")
        except Exception as e:
            self.logger.error(f"Failed to activate fins: {str(e)}")
            raise RobotError(f"Fin activation failed: {str(e)}", "motion_controller")

    @with_error_handling("motion_controller")
    def fin_off(self):
        """Deactivate fins."""
        if not self._pins_claimed:
            return
            
        pins = self.config.pins["fins"]
        
        try:
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_L"], self.config.fin_pwm_freq, 0)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_R"], self.config.fin_pwm_freq, 0)
            lgpio.gpio_write(self._gpio_handle, pins["L_EN"], 0)
            self.logger.debug("Fins deactivated")
        except Exception as e:
            self.logger.error(f"Failed to deactivate fins: {str(e)}")
            raise RobotError(f"Fin deactivation failed: {str(e)}", "motion_controller")

    @with_error_handling("motion_controller")
    def cleanup(self):
        """Clean up GPIO resources."""
        if self._gpio_handle is not None:
            try:
                self.stop()
                self.fin_off()
                lgpio.gpiochip_close(self._gpio_handle)
                self._gpio_handle = None
                self._pins_claimed = False
                self.logger.info("GPIO resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                raise RobotError(f"Cleanup failed: {str(e)}", "motion_controller")

    @with_error_handling("motion_controller")
    def verify_motor_control(self):
        """Verify motor control pins and their states."""
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "motion_controller")
            
        self.logger.info("Verifying motor control pins...")
        
        # Check standby pin
        standby_pin = self.config.pins["standby"]
        standby_state = lgpio.gpio_read(self._gpio_handle, standby_pin)
        self.logger.info(f"Standby pin ({standby_pin}) state: {standby_state}")
        
        # Check each motor's control pins
        for motor_id, pins in self.config.pins.items():
            if motor_id in ["front_left", "front_right", "rear_left", "rear_right"]:
                in1_state = lgpio.gpio_read(self._gpio_handle, pins["in1"])
                in2_state = lgpio.gpio_read(self._gpio_handle, pins["in2"])
                self.logger.info(f"Motor {motor_id}: in1={pins['in1']}({in1_state}), in2={pins['in2']}({in2_state})")
                
        self.logger.info("Motor control verification complete")

    @with_error_handling("motion_controller")
    def test_motors(self):
        """Test each motor by moving it forward, backward, and stopping."""
        self.logger.info("Starting motor test sequence...")
        
        # Test each motor
        for motor_name, pins in self.config.pins.items():
            if motor_name in ["fins", "standby", "ultrasonic"]:
                continue
                
            self.logger.info(f"Testing {motor_name} FORWARD")
            self._set_motor(pins["in1"], pins["in2"], pins["pwm"], 1, self.config.speed)
            time.sleep(1)
            self.verify_motor_control()
            
            self.logger.info(f"Testing {motor_name} BACKWARD")
            self._set_motor(pins["in1"], pins["in2"], pins["pwm"], -1, self.config.speed)
            time.sleep(1)
            self.verify_motor_control()
            
            self.logger.info(f"Testing {motor_name} STOP")
            self._set_motor(pins["in1"], pins["in2"], pins["pwm"], 0, 0)
            time.sleep(1)
            self.verify_motor_control()
            
        self.logger.info("Motor test sequence complete.")

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()
