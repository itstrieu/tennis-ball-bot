# === TB6612FNG Motor Driver (Driver 1: Front Motors) ===
FRONT_RIGHT = {
    "IN1": 16,  # DRIVER_1_AIN1
    "IN2": 20,  # DRIVER_1_AIN2
    "PWM": 12,  # DRIVER_1_PWMA
}

FRONT_LEFT = {
    "IN1": 21,  # DRIVER_1_BIN1
    "IN2": 26,  # DRIVER_1_BIN2
    "PWM": 13,  # DRIVER_1_PWMB
}

# === TB6612FNG Motor Driver (Driver 2: Rear Motors) ===
REAR_LEFT = {
    "IN1": 3,  # DRIVER_2_AIN1
    "IN2": 4,  # DRIVER_2_AIN2
    "PWM": 6,  # DRIVER_2_PWMA
}

REAR_RIGHT = {
    "IN1": 22,  # DRIVER_2_BIN1
    "IN2": 27,  # DRIVER_2_BIN2
    "PWM": 5,  # DRIVER_2_PWMB
}

# === BTS7960 Motor Driver (Fins) ===
FINS = {
    "L_EN": 14,
    "PWM_L": 18,
    "PWM_R": 19,
    "R_EN": None,  # Not connected / not in use
}

# === Control ===
STBY = 17

# === Ultrasonic Sensor ===
ULTRASONIC = {"TRIG": 23, "ECHO": 24}

# === Encoder Sensors (Hall Effect) ===
ENCODERS = {
    "FRONT_LEFT": {
        "SIG1": 23,  # Orange (NO1)
        "SIG2": 24,  # Blue (NO2)
    },
    "FRONT_RIGHT": {
        "SIG1": 25,
        "SIG2": 8,
    },
    "REAR_LEFT": {
        "SIG1": 9,
        "SIG2": 10,
    },
    "REAR_RIGHT": {
        "SIG1": 11,
        "SIG2": 7,
    },
}
