import pygame
import RPi.GPIO as GPIO
import time

# GPIO Pin Definitions
ENA = 18  # PWM for Left Motor
IN1 = 23  # Forward Left
IN2 = 24  # Reverse Left
ENB = 19  # PWM for Right Motor
IN3 = 25  # Forward Right
IN4 = 26  # Reverse Right

# PWM Frequency
PWM_FREQ = 1000  # 1 kHz

# GPIO Setup
def setup_gpio():
    GPIO.setmode(GPIO.BCM)  # Use BCM numbering
    GPIO.setup([ENA, IN1, IN2, ENB, IN3, IN4], GPIO.OUT)  # Set all as outputs
    pwm_left = GPIO.PWM(ENA, PWM_FREQ)
    pwm_right = GPIO.PWM(ENB, PWM_FREQ)
    pwm_left.start(0)  # Start with 0% duty cycle
    pwm_right.start(0)
    return pwm_left, pwm_right

# Set Motor Speed and Direction
def set_motor(pwm, in1, in2, speed):
    if speed > 0:
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
    elif speed < 0:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.HIGH)
        speed = -speed  # Make speed positive for PWM duty cycle
    else:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.LOW)
    pwm.ChangeDutyCycle(speed)

# Map Joystick Axis Value to PWM Duty Cycle
def map_axis_to_duty(value):
    # Joystick axis range is -1.0 to 1.0; map to 0–100 (duty cycle)
    return int(abs(value) * 100)

# Main Function
def main():
    # GPIO and PWM Setup
    pwm_left, pwm_right = setup_gpio()

    # Initialize Pygame for Joystick Input
    pygame.init()
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick connected:", joystick.get_name())

    try:
        while True:
            pygame.event.pump()  # Update joystick events
            
            # Read Left Joystick Y-axis (Motor A)
            left_y = joystick.get_axis(1)  # Axis 1: Left joystick Y-axis
            left_speed = map_axis_to_duty(left_y)
            set_motor(pwm_left, IN1, IN2, left_y * 100)  # Scale to -100 to 100
            
            # Read Right Joystick Y-axis (Motor B)
            right_y = joystick.get_axis(4)  # Axis 4: Right joystick Y-axis
            right_speed = map_axis_to_duty(right_y)
            set_motor(pwm_right, IN3, IN4, right_y * 100)  # Scale to -100 to 100

            time.sleep(0.1)  # Small delay to reduce CPU usage

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Stop Motors and Cleanup
        pwm_left.stop()
        pwm_right.stop()
        GPIO.cleanup()
        pygame.quit()

if __name__ == "__main__":
    main()
