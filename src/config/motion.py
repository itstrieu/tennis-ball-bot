"""
motion.py

Motion configuration constants for controlling robot behavior,
including speed levels, turning thresholds, and target detection criteria.
These are used by both the RobotController and Motion modules.
"""

from typing import Dict, TypedDict, Literal
from dataclasses import dataclass

# Type definitions
MovementMethod = Literal["move_forward", "move_backward", "rotate_left", "rotate_right", "stop"]
MovementParams = TypedDict('MovementParams', {
    'method': MovementMethod,
    'speed': int,
    'time': float
})

# Fin Configuration
FIN_PWM_FREQ = 6000
FIN_SPEED = 85

# Wheels
PWM_FREQ = 10000

# Basic speeds & thresholds
SPEED = 70
CENTER_ROTATE_SPEED = 50
SEARCH_ROTATE_SPEED = 50
INTER_STEP_PAUSE = 0.2

TARGET_AREA = 12000
CENTER_THRESHOLD = 25

# Movement parameters
MOVEMENT_STEPS: Dict[str, MovementParams] = {
    "step_forward": {"method": "move_forward", "speed": SPEED, "time": 1.5},
    "small_forward": {"method": "move_forward", "speed": SPEED, "time": 1.0},
    "micro_forward": {"method": "move_forward", "speed": SPEED, "time": 1.0},
    "step_left": {"method": "rotate_left", "speed": CENTER_ROTATE_SPEED, "time": 0.3},
    "micro_left": {"method": "rotate_left", "speed": CENTER_ROTATE_SPEED, "time": 0.1},
    "step_right": {"method": "rotate_right", "speed": CENTER_ROTATE_SPEED, "time": 0.3},
    "micro_right": {"method": "rotate_right", "speed": CENTER_ROTATE_SPEED, "time": 0.1},
    "stop": {"method": "stop", "speed": 0, "time": 1.0},
    "search": {"method": "rotate_right", "speed": SEARCH_ROTATE_SPEED, "time": 0.8},
}

# Ratios of TARGET_AREA to trigger decisions
THRESHOLDS = {
    "stop": 1.0,
    "micro": 0.7,
    "small": 0.5,
    "recovery": 0.2,
}

# Dev‐only slowdown factor (optional)
DEV_SLOWDOWN = 2

def validate_movement_params(params: MovementParams) -> None:
    """
    Validate movement parameters.
    
    Args:
        params: Movement parameters to validate
        
    Raises:
        ValueError: If any parameter is invalid
    """
    if not isinstance(params['speed'], int):
        raise ValueError(f"Speed must be an integer, got {type(params['speed'])}")
    if not 0 <= params['speed'] <= 100:
        raise ValueError(f"Speed must be between 0 and 100, got {params['speed']}")
    if not isinstance(params['time'], (int, float)):
        raise ValueError(f"Time must be a number, got {type(params['time'])}")
    if params['time'] <= 0:
        raise ValueError(f"Time must be positive, got {params['time']}")
    if params['method'] not in ["move_forward", "move_backward", "rotate_left", "rotate_right", "stop"]:
        raise ValueError(f"Invalid movement method: {params['method']}")

# Validate all movement steps on import
for action, params in MOVEMENT_STEPS.items():
    validate_movement_params(params)
