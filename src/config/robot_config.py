"""
robot_config.py

Centralized configuration for the robot.
Contains all parameters and thresholds used across different components.

This module provides:
- Vision system configuration
- Motion control parameters
- Sensor thresholds
- GPIO pin mappings
- Movement step definitions
"""

from dataclasses import dataclass
from typing import Dict, TypedDict, Literal

# Type definitions
MovementMethod = Literal["move_forward", "move_backward", "rotate_left", "rotate_right", "stop"]
MovementParams = TypedDict('MovementParams', {
    'method': MovementMethod,
    'speed': int,
    'time': float
})

@dataclass
class RobotConfig:
    """
    Centralized configuration for the robot.
    
    This class provides:
    - Vision system parameters
    - Motion control settings
    - Sensor configurations
    - GPIO pin mappings
    - Movement step definitions
    
    The configuration is organized into sections:
    1. Vision: Camera and detection settings
    2. Motion: Motor and movement parameters
    3. Sensors: Ultrasonic sensor settings
    4. Streaming: Video streaming configuration
    5. GPIO: Pin mappings and control
    
    Attributes:
        vision_model_path: Path to YOLO model file
        confidence_threshold: Minimum confidence for detections
        frame_width: Camera frame width
        camera_offset: Camera center offset
        fin_pwm_freq: PWM frequency for fins
        fin_speed: Fin motor speed
        pwm_freq: PWM frequency for wheels
        speed: Base movement speed
        center_rotate_speed: Speed for centering rotations
        search_rotate_speed: Speed for search rotations
        inter_step_pause: Pause between movement steps
        ground_distance: Expected distance to ground
        obstacle_threshold: Minimum distance for obstacles
        error_threshold: Allowed ground distance error
        target_area: Target ball area
        center_threshold: Centering tolerance
        max_no_ball: Maximum consecutive no-ball detections
        max_recovery_attempts: Maximum recovery attempts
        movement_steps: Movement step definitions
        thresholds: Area ratio thresholds
        dev_slowdown: Development mode slowdown factor
        streaming_fps: Streaming frame rate
        streaming_quality: JPEG quality
        max_bandwidth: Maximum streaming bandwidth
        target_fps: Target camera frame rate
        frame_buffer_size: Frame buffer size
        pins: GPIO pin mappings
    """
    
    # === Vision Configuration ===
    vision_model_path: str = "models/current_best.pt"
    confidence_threshold: float = 0.9
    frame_width: int = 640
    camera_offset: int = 0
    
    # === Motion Configuration ===
    # Fin Configuration
    fin_pwm_freq: int = 6000
    fin_speed: int = 85
    
    # Wheels
    pwm_freq: int = 10000  # 10kHz frequency for motor control
    
    # Basic speeds & thresholds
    speed: int = 85  # Higher base speed
    center_rotate_speed: int = 60  # Higher rotation speed
    search_rotate_speed: int = 60  # Higher search speed
    inter_step_pause: float = 0.5
    
    # Ultrasonic Sensor Configuration
    ground_distance: int = 50  # Expected distance to ground in cm
    obstacle_threshold: int = 15  # If distance < this, likely an obstacle
    error_threshold: int = 5  # Allowable error in ground distance
    
    # Target areas and thresholds
    target_area: int = 12000
    center_threshold: int = 25
    max_no_ball: int = 3
    max_recovery_attempts: int = 3
    
    # Movement parameters
    movement_steps: Dict[str, MovementParams] = None
    
    # Ratios of TARGET_AREA to trigger decisions
    thresholds: Dict[str, float] = None
    
    # Dev‐only slowdown factor (optional)
    dev_slowdown: float = 2
    
    # === Streaming Configuration ===
    streaming_fps: int = 30
    streaming_quality: int = 85  # JPEG quality (0-100)
    max_bandwidth: int = 1000000  # 1 Mbps
    target_fps: int = 30  # Target frame rate for camera
    frame_buffer_size: int = 2  # Number of frames to buffer
    
    # === GPIO Configuration ===
    pins: Dict[str, Dict[str, int]] = None
    
    def __post_init__(self):
        """
        Initialize default values for complex types.
        
        This method:
        1. Sets up movement step definitions
        2. Configures area ratio thresholds
        3. Maps GPIO pins
        
        The movement steps define:
        - Forward/backward movements
        - Left/right rotations
        - Search patterns
        - Stop commands
        
        The thresholds define:
        - Stop condition
        - Micro adjustments
        - Small movements
        - Recovery triggers
        """
        if self.movement_steps is None:
            self.movement_steps = {
                "step_forward": {"method": "move_forward", "speed": self.speed, "time": 1.5},
                "small_forward": {"method": "move_forward", "speed": self.speed, "time": 1.0},
                "micro_forward": {"method": "move_forward", "speed": self.speed, "time": 1.0},
                "step_left": {"method": "rotate_left", "speed": self.center_rotate_speed, "time": 0.3},
                "micro_left": {"method": "rotate_left", "speed": self.center_rotate_speed, "time": 0.1},
                "step_right": {"method": "rotate_right", "speed": self.center_rotate_speed, "time": 0.3},
                "micro_right": {"method": "rotate_right", "speed": self.center_rotate_speed, "time": 0.1},
                "stop": {"method": "stop", "speed": 0, "time": 1.0},
                "search": {"method": "rotate_right", "speed": self.search_rotate_speed, "time": 0.8},
            }
            
        if self.thresholds is None:
            self.thresholds = {
                "stop": 1.0,    # Full target area
                "micro": 0.7,   # 70% of target area
                "small": 0.5,   # 50% of target area
                "recovery": 0.2, # 20% of target area
            }
            
        if self.pins is None:
            self.pins = {
                # Front left motor pins
                "front_left": {
                    "in1": 21,  # DRIVER_1_BIN1
                    "in2": 26,  # DRIVER_1_BIN2
                    "pwm": 13,  # DRIVER_1_PWMB
                },
                # Front right motor pins
                "front_right": {
                    "in1": 16,  # DRIVER_1_AIN1
                    "in2": 20,  # DRIVER_1_AIN2
                    "pwm": 12,  # DRIVER_1_PWMA
                },
                # Rear left motor pins
                "rear_left": {
                    "in1": 3,   # DRIVER_2_AIN1
                    "in2": 4,   # DRIVER_2_AIN2
                    "pwm": 6,   # DRIVER_2_PWMA
                },
                # Rear right motor pins
                "rear_right": {
                    "in1": 22,  # DRIVER_2_BIN1
                    "in2": 27,  # DRIVER_2_BIN2
                    "pwm": 5,   # DRIVER_2_PWMB
                },
                # Fin control pins
                "fins": {
                    "L_EN": 14,
                    "PWM_L": 18,
                    "PWM_R": 19,
                },
                "standby": 17,  # STBY
                # Ultrasonic sensor pins
                "ultrasonic": {
                    "trigger": 2,
                    "echo": 15,
                }
            }

# Create default configuration
default_config = RobotConfig() 