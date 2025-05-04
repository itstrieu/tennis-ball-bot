"""
ultrasonic.py

Handles ultrasonic sensor operations for obstacle detection.
"""

import time
import logging
import lgpio
from typing import Optional
from utils.logger import Logger
from utils.error_handler import with_error_handling, RobotError
from config.robot_config import default_config

class UltrasonicSensor:
    """
    UltrasonicSensor manages the HC-SR04 ultrasonic sensor for obstacle detection.
    The sensor is mounted at an angle to distinguish between ground and obstacles.
    """
    
    def __init__(self, config=None, gpio_handle=None):
        """
        Initialize the ultrasonic sensor.
        
        Args:
            config: Optional RobotConfig instance
            gpio_handle: Optional GPIO handle from MotionController
        """
        self.config = config or default_config
        self._gpio_handle = gpio_handle
        self.logger = Logger.get_logger(name="ultrasonic", log_level=logging.INFO)
        
        try:
            self._initialize_gpio()
        except Exception as e:
            self.logger.error(f"Failed to initialize ultrasonic sensor: {str(e)}")
            raise RobotError(f"Ultrasonic sensor initialization failed: {str(e)}", "ultrasonic")

    @with_error_handling("ultrasonic")
    def _initialize_gpio(self):
        """Initialize GPIO for ultrasonic sensor."""
        if self._gpio_handle is None:
            self._gpio_handle = lgpio.gpiochip_open(0)
            self.logger.info("Opened GPIO chip")
            
        # Configure trigger pin as output
        trigger_pin = self.config.pins["ultrasonic"]["trigger"]
        result = lgpio.gpio_claim_output(self._gpio_handle, trigger_pin)
        if result < 0:
            self.logger.error(f"Failed to claim trigger pin {trigger_pin}: {result}")
            raise RobotError(f"Failed to claim trigger pin {trigger_pin}", "ultrasonic")
        self.logger.info(f"Claimed trigger pin {trigger_pin}")
            
        # Configure echo pin as input
        echo_pin = self.config.pins["ultrasonic"]["echo"]
        result = lgpio.gpio_claim_input(self._gpio_handle, echo_pin)
        if result < 0:
            self.logger.error(f"Failed to claim echo pin {echo_pin}: {result}")
            raise RobotError(f"Failed to claim echo pin {echo_pin}", "ultrasonic")
        self.logger.info(f"Claimed echo pin {echo_pin}")
            
        # Test trigger pin
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 1)
        time.sleep(0.1)
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 0)
        self.logger.info("Trigger pin test complete")
            
        self.logger.info("Ultrasonic sensor GPIO initialized successfully")

    @with_error_handling("ultrasonic")
    def get_distance(self) -> Optional[float]:
        """
        Get distance measurement from ultrasonic sensor.
        
        Returns:
            Distance in centimeters, or None if measurement failed
        """
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "ultrasonic")
            
        trigger_pin = self.config.pins["ultrasonic"]["trigger"]
        echo_pin = self.config.pins["ultrasonic"]["echo"]
        
        # Send trigger pulse
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 1)
        time.sleep(0.00001)  # 10 microseconds
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 0)
        
        # Wait for echo to start
        start_time = time.time()
        while lgpio.gpio_read(self._gpio_handle, echo_pin) == 0:
            if time.time() - start_time > 0.1:  # Timeout after 100ms
                self.logger.warning("Timeout waiting for echo start")
                return None
            time.sleep(0.00001)
        pulse_start = time.time()
        
        # Wait for echo to end
        while lgpio.gpio_read(self._gpio_handle, echo_pin) == 1:
            if time.time() - pulse_start > 0.1:  # Timeout after 100ms
                self.logger.warning("Timeout waiting for echo end")
                return None
            time.sleep(0.00001)
        pulse_end = time.time()
        
        # Calculate distance (speed of sound = 34300 cm/s)
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2
        
        self.logger.debug(f"Distance measurement: pulse_duration={pulse_duration:.6f}s, distance={distance:.1f}cm")
        return distance

    @with_error_handling("ultrasonic")
    def is_obstacle(self) -> bool:
        """
        Check if there's an obstacle in front of the robot.
        
        Returns:
            True if obstacle detected, False otherwise
        """
        distance = self.get_distance()
        if distance is None:
            return False
            
        # If distance is less than obstacle threshold, it's an obstacle
        is_obstacle = distance < self.config.obstacle_threshold
        
        if is_obstacle:
            self.logger.info(f"Obstacle detected at {distance:.1f} cm")
        return is_obstacle

    @with_error_handling("ultrasonic")
    def cleanup(self):
        """Clean up GPIO resources."""
        if self._gpio_handle is not None:
            try:
                # Only release ultrasonic pins, don't close the handle
                trigger_pin = self.config.pins["ultrasonic"]["trigger"]
                echo_pin = self.config.pins["ultrasonic"]["echo"]
                lgpio.gpio_free(self._gpio_handle, trigger_pin)
                lgpio.gpio_free(self._gpio_handle, echo_pin)
                self._gpio_handle = None
                self.logger.info("Ultrasonic sensor GPIO resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                raise RobotError(f"Cleanup failed: {str(e)}", "ultrasonic")

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup() 