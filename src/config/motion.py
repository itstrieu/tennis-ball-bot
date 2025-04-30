"""
motion.py

Motion configuration constants for controlling robot behavior,
including speed levels, turning thresholds, and target detection criteria.
These are used by both the RobotController and Motion modules.
"""

# Fin Configuration
FIN_PWM_FREQ = 6000
FIN_SPEED = 85

# Wheels
PWM_FREQ = 10000

# Basic speeds & thresholds
SPEED = 50
CENTER_ROTATE_SPEED = 55
SEARCH_ROTATE_SPEED = 70
INTER_STEP_PAUSE = 0.5  # seconds, tune as needed (higher = slower)

TARGET_AREA = 12000
CENTER_THRESHOLD = 25

# Movement parameters, one source of truth
MOVEMENT_STEPS = {
    "step_forward": {"method": "move_forward", "speed": SPEED, "time": 0.7},
    "small_forward": {"method": "move_forward", "speed": int(SPEED * 0.8), "time": 0.6},
    "micro_forward": {
        "method": "move_forward",
        "speed": int(SPEED * 0.6),
        "time": 0.4,
    },
    "step_left": {
        "method": "rotate_left",
        "speed": int(CENTER_ROTATE_SPEED * 0.7),
        "time": 0.2,
    },
    "micro_left": {
        "method": "rotate_left",
        "speed": int(CENTER_ROTATE_SPEED * 0.7),
        "time": 0.1,
    },
    "step_right": {
        "method": "rotate_right",
        "speed": int(CENTER_ROTATE_SPEED * 0.7),
        "time": 0.2,
    },
    "micro_right": {
        "method": "rotate_right",
        "speed": int(CENTER_ROTATE_SPEED * 0.7),
        "time": 0.1,
    },
    "stop": {"method": "stop", "time": 1.0},
    "search": {
        "method": "rotate_right",
        "speed": int(SEARCH_ROTATE_SPEED),
        "time": 0.3,
    },
}

# Ratios of TARGET_AREA to trigger decisions
THRESHOLDS = {
    "stop": 1.0,
    "micro": 0.7,
    "small": 0.5,
    "recovery": 0.2,
}

# Dev‐only slowdown factor (optional)
DEV_SLOWDOWN = 2.0
