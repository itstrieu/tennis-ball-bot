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
SPEED = 60  # Default forward movement speed

# Vision-to-motion logic thresholds
SELF_TURN_THRESHOLD = 30  # Pixel offset to trigger turning
CENTER_THRESHOLD = 25  # Max offset from center to be considered "centered"

# Rotational behavior
SEARCH_ROTATE_SPEED = 70  # Speed during scanning rotation
CENTER_ROTATE_SPEED = 60  # Speed used when centering on target
SEARCH_ROTATE_DURATION = 0.5  # Duration of each rotation step during scanning
SWITCH_DELAY = 0.3  # Delay between switching directions
NO_BALL_PAUSE = 0.3  # Delay after losing sight of a ball

# Ball detection
TARGET_AREA = 12000  # Minimum area to stop approaching the ball
