"""
robot_config.py

Centralized configuration for the robot.
Contains all parameters and thresholds used across different components.
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
    """Centralized configuration for the robot."""
    
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
        """Initialize default values for complex types."""
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
                "stop": 1.0,
                "micro": 0.7,
                "small": 0.5,
                "recovery": 0.2,
            }
            
        if self.pins is None:
            self.pins = {
                "front_left": {
                    "in1": 21,  # DRIVER_1_BIN1
                    "in2": 26,  # DRIVER_1_BIN2
                    "pwm": 13,  # DRIVER_1_PWMB
                },
                "front_right": {
                    "in1": 16,  # DRIVER_1_AIN1
                    "in2": 20,  # DRIVER_1_AIN2
                    "pwm": 12,  # DRIVER_1_PWMA
                },
                "rear_left": {
                    "in1": 3,   # DRIVER_2_AIN1
                    "in2": 4,   # DRIVER_2_AIN2
                    "pwm": 6,   # DRIVER_2_PWMA
                },
                "rear_right": {
                    "in1": 22,  # DRIVER_2_BIN1
                    "in2": 27,  # DRIVER_2_BIN2
                    "pwm": 5,   # DRIVER_2_PWMB
                },
                "fins": {
                    "L_EN": 14,
                    "PWM_L": 18,
                    "PWM_R": 19,
                },
                "standby": 17,  # STBY
                "ultrasonic": {
                    "trigger": 2,
                    "echo": 15,
                }
            }

# Create default configuration
default_config = RobotConfig() 