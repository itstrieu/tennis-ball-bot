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
    confidence_threshold: float = 0.7
    frame_width: int = 640
    camera_offset: int = 0
    
    # === Motion Configuration ===
    # Fin Configuration
    fin_pwm_freq: int = 6000
    fin_speed: int = 85
    
    # Wheels
    pwm_freq: int = 1000  # Lower frequency for better motor control
    
    # Basic speeds & thresholds
    speed: int = 85  # Higher base speed
    center_rotate_speed: int = 70  # Higher rotation speed
    search_rotate_speed: int = 70  # Higher search speed
    inter_step_pause: float = 0.2
    
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
                    "in1": 17,
                    "in2": 27,
                    "pwm": 22
                },
                "front_right": {
                    "in1": 23,
                    "in2": 24,
                    "pwm": 25
                },
                "rear_left": {
                    "in1": 5,
                    "in2": 6,
                    "pwm": 13
                },
                "rear_right": {
                    "in1": 19,
                    "in2": 26,
                    "pwm": 12
                },
                "fins": {
                    "L_EN": 16,
                    "PWM_L": 20,
                    "PWM_R": 21
                },
                "standby": 4,
                "ultrasonic": {
                    "trigger": 18,
                    "echo": 7
                }
            }

# Create default configuration
default_config = RobotConfig() 