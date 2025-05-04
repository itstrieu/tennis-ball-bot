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
        if motor_id == "left":
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
                for pin in motor_pins.values():
                    lgpio.gpio_claim_output(self._gpio_handle, pin)
            else:
                # Handle single pin values (standby, etc.)
                lgpio.gpio_claim_output(self._gpio_handle, motor_pins)
            
        self.logger.info("Output pins claimed successfully")

    @with_error_handling("motion_controller")
    def _set_motor(self, in1: int, in2: int, pwm: int, direction: int, duty: float):
        """
        Set motor state and PWM duty cycle.
        
        Args:
            in1: First control pin
            in2: Second control pin
            pwm: PWM pin
            direction: Direction (1 = forward, -1 = backward)
            duty: PWM duty cycle (0-100)
        """
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "motion_controller")
            
        # Set direction
        lgpio.gpio_write(self._gpio_handle, in1, 1 if direction > 0 else 0)
        lgpio.gpio_write(self._gpio_handle, in2, 0 if direction > 0 else 1)
        
        # Set PWM
        lgpio.tx_pwm(self._gpio_handle, pwm, self.config.pwm_freq, duty)

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
            for motor_id, direction in pattern.items():
                pins = self.config.pins[motor_id]
                duty = self._apply_scale(motor_id, speed)
                self._set_motor(pins["in1"], pins["in2"], pins["pwm"], direction, duty)
                
            self.logger.debug(f"Moving with pattern: {pattern}, speed: {speed}")
        except Exception as e:
            self._is_moving = False
            raise

    @with_error_handling("motion_controller")
    def move_forward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Move forward at specified speed for optional duration."""
        pattern = {
            "front_left": 1,
            "front_right": 1,
            "rear_left": 1,
            "rear_right": 1
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def move_backward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Move backward at specified speed for optional duration."""
        pattern = {
            "front_left": -1,
            "front_right": -1,
            "rear_left": -1,
            "rear_right": -1
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def rotate_left(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Rotate left at specified speed for optional duration."""
        pattern = {
            "front_left": -1,
            "front_right": 1,
            "rear_left": -1,
            "rear_right": 1
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def rotate_right(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Rotate right at specified speed for optional duration."""
        pattern = {
            "front_left": 1,
            "front_right": -1,
            "rear_left": 1,
            "rear_right": -1
        }
        self._move_by_pattern(pattern, speed)
        if duration:
            time.sleep(duration)
            self.stop()

    @with_error_handling("motion_controller")
    def stop(self, speed: int = 0, duration: Optional[float] = None):
        """Stop all motors."""
        if self._is_moving:
            # Set all motors to stop by setting both control pins to 0
            for motor_id in ["front_left", "front_right", "rear_left", "rear_right"]:
                pins = self.config.pins[motor_id]
                lgpio.gpio_write(self._gpio_handle, pins["in1"], 0)
                lgpio.gpio_write(self._gpio_handle, pins["in2"], 0)
                lgpio.tx_pwm(self._gpio_handle, pins["pwm"], self.config.pwm_freq, 0)
            
            self._is_moving = False
            self.logger.debug("Motors stopped")
            
        if duration:
            time.sleep(duration)

    @with_error_handling("motion_controller")
    def fin_on(self, speed: Optional[int] = None):
        """Activate fins at specified speed."""
        if not self._pins_claimed:
            self._initialize_gpio()
            
        speed = speed or self.config.fin_speed
        pins = self.config.pins["fins"]
        
        try:
            lgpio.gpio_write(self._gpio_handle, pins["L_EN"], 1)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_L"], self.config.fin_pwm_freq, speed)
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
            lgpio.gpio_write(self._gpio_handle, pins["L_EN"], 0)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_L"], self.config.fin_pwm_freq, 0)
            lgpio.tx_pwm(self._gpio_handle, pins["PWM_R"], self.config.fin_pwm_freq, 0)
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

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()
