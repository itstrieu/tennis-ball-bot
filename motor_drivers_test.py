import RPi.GPIO as GPIO
import time

# set up gpio
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(13, GPIO.OUT)    # PWMA
GPIO.setup(19, GPIO.OUT)    # AIN2    
GPIO.setup(26, GPIO.OUT)    # AIN1
GPIO.setup(21, GPIO.OUT)    # STBY

# enable board
GPIO.output(21, GPIO.HIGH)

# set PWMA high for testing can be set to a PWM output for motor speed control
GPIO.output(13, GPIO.HIGH)

# Run motor in direction A for 5 seconds
GPIO.output(19, GPIO.HIGH)
GPIO.output(26, GPIO.LOW)
time.sleep(5)

# stop motor for 5 seconds
GPIO.output(19, GPIO.HIGH)
GPIO.output(26, GPIO.HIGH)
time.sleep(5)

# Run motor in direction B for 5 seconds
GPIO.output(19, GPIO.LOW)
GPIO.output(26, GPIO.HIGH)
time.sleep(5)

# stop motor for 5 seconds
GPIO.output(19, GPIO.HIGH)
GPIO.output(26, GPIO.HIGH)
time.sleep(5)
