"""
ultrasonic.py

Handles ultrasonic sensor operations for obstacle detection.
Provides distance measurement and obstacle detection capabilities.

This module provides:
- Distance measurement using HC-SR04 ultrasonic sensor
- Obstacle detection with configurable thresholds
- GPIO management for sensor operations
- Error handling and resource cleanup
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

    This class provides:
    - Distance measurement in centimeters
    - Obstacle detection with configurable thresholds
    - GPIO pin management for trigger and echo
    - Resource cleanup and error handling

    Attributes:
        config: RobotConfig instance for configuration values
        _gpio_handle: Handle for GPIO operations
        logger: Logger instance for logging operations
    """

    def __init__(self, config=None, gpio_handle=None):
        """
        Initialize the ultrasonic sensor.

        This method:
        1. Sets up configuration
        2. Initializes GPIO
        3. Configures trigger and echo pins

        Args:
            config: Optional RobotConfig instance
            gpio_handle: Optional GPIO handle from MotionController

        Raises:
            RobotError: If initialization fails
        """
        self.config = config or default_config
        self._gpio_handle = gpio_handle
        self.logger = Logger.get_logger(name="ultrasonic", log_level=logging.INFO)

        try:
            self._initialize_gpio()
        except Exception as e:
            self.logger.error(f"Failed to initialize ultrasonic sensor: {str(e)}")
            raise RobotError(
                f"Ultrasonic sensor initialization failed: {str(e)}", "ultrasonic"
            )

    @with_error_handling("ultrasonic")
    def _initialize_gpio(self):
        """
        Initialize GPIO for ultrasonic sensor.

        This method:
        1. Opens GPIO chip if needed
        2. Configures trigger pin as output
        3. Configures echo pin as input
        4. Tests trigger functionality

        Raises:
            RobotError: If GPIO initialization fails
        """
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

        # Test trigger pin functionality
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 1)
        time.sleep(0.1)
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 0)
        self.logger.info("Trigger pin test complete")

        self.logger.info("Ultrasonic sensor GPIO initialized successfully")

    @with_error_handling("ultrasonic")
    def get_distance(self) -> Optional[float]:
        """
        Get distance measurement from ultrasonic sensor.

        This method:
        1. Sends a trigger pulse
        2. Measures echo pulse duration
        3. Calculates distance based on sound speed
        4. Handles timeouts and errors

        Returns:
            Distance in centimeters, or None if measurement failed

        Raises:
            RobotError: If GPIO is not initialized
        """
        if self._gpio_handle is None:
            raise RobotError("GPIO not initialized", "ultrasonic")

        trigger_pin = self.config.pins["ultrasonic"]["trigger"]
        echo_pin = self.config.pins["ultrasonic"]["echo"]

        # Send 10 microsecond trigger pulse
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 1)
        time.sleep(0.00001)  # 10 microseconds
        lgpio.gpio_write(self._gpio_handle, trigger_pin, 0)

        # Wait for echo to start with timeout
        start_time = time.time()
        while lgpio.gpio_read(self._gpio_handle, echo_pin) == 0:
            if time.time() - start_time > 0.1:  # Timeout after 100ms
                self.logger.warning("Timeout waiting for echo start")
                return None
            time.sleep(0.00001)
        pulse_start = time.time()

        # Wait for echo to end with timeout
        while lgpio.gpio_read(self._gpio_handle, echo_pin) == 1:
            if time.time() - pulse_start > 0.1:  # Timeout after 100ms
                self.logger.warning("Timeout waiting for echo end")
                return None
            time.sleep(0.00001)
        pulse_end = time.time()

        # Calculate distance using speed of sound (34300 cm/s)
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2  # Divide by 2 for round trip

        self.logger.debug(
            f"Distance measurement: pulse_duration={pulse_duration:.6f}s, distance={distance:.1f}cm"
        )
        return distance

    @with_error_handling("ultrasonic")
    def is_obstacle(self) -> bool:
        """
        Check if there's an obstacle in front of the robot.

        This method:
        1. Gets distance measurement
        2. Compares with obstacle threshold
        3. Logs obstacle detection

        Returns:
            True if obstacle detected, False otherwise
        """
        distance = self.get_distance()
        if distance is None:
            return False

        # Check if distance is less than configured threshold
        is_obstacle = distance < self.config.obstacle_threshold

        if is_obstacle:
            self.logger.info(f"Obstacle detected at {distance:.1f} cm")
        return is_obstacle

    @with_error_handling("ultrasonic")
    def cleanup(self):  # Synchronous cleanup
        """
        Clean up GPIO resources.

        This method:
        1. Releases ultrasonic pins
        2. Does NOT clear or close the shared GPIO handle
        3. Handles cleanup errors

        Raises:
            RobotError: If cleanup fails
        """
        # Only proceed if the handle exists (might be None if init failed)
        if self._gpio_handle is not None:
            try:
                trigger_pin = self.config.pins["ultrasonic"]["trigger"]
                echo_pin = self.config.pins["ultrasonic"]["echo"]
                # Attempt to free pins, ignore errors if already freed/invalid handle
                try:
                    lgpio.gpio_free(self._gpio_handle, trigger_pin)
                except lgpio.error as e:
                    self.logger.warning(
                        f"Ignoring error freeing trigger pin {trigger_pin}: {e}"
                    )
                try:
                    lgpio.gpio_free(self._gpio_handle, echo_pin)
                except lgpio.error as e:
                    self.logger.warning(
                        f"Ignoring error freeing echo pin {echo_pin}: {e}"
                    )
                # DO NOT set self._gpio_handle = None here - it's owned by MotionController
                self.logger.info("Ultrasonic sensor GPIO resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
                # Avoid raising if the error is due to handle already closed
                if "unknown handle" not in str(e) and "GPIO not allocated" not in str(
                    e
                ):
                    raise RobotError(f"Cleanup failed: {str(e)}", "ultrasonic")
                else:
                    self.logger.warning(
                        f"Ignoring ultrasonic cleanup error (handle likely closed): {e}"
                    )
        else:
            self.logger.info("Ultrasonic sensor GPIO handle is None, skipping cleanup.")

    def __del__(self):
        """Ensure cleanup on object destruction."""
        # Avoid cleanup in __del__ due to potential issues with shared handles/async
        pass  # self.cleanup()
