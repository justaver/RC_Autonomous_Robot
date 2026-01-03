import pigpio
import pygame
import time

# GPIO Pins for Motors
ENA = 18  # PWM for Left Motor
IN1 = 23  # Left Motor Forward
IN2 = 24  # Left Motor Reverse
ENB = 19  # PWM for Right Motor
IN3 = 25  # Right Motor Forward
IN4 = 26  # Right Motor Reverse

# Setup pigpio
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

# Set up direction pins
for pin in [IN1, IN2, IN3, IN4]:
    pi.set_mode(pin, pigpio.OUTPUT)

# Function to set motor speed and direction
def set_motor(pi, ena, in1, in2, speed):
    if speed > 0:
        pi.write(in1, 1)
        pi.write(in2, 0)
    elif speed < 0:
        pi.write(in1, 0)
        pi.write(in2, 1)
        speed = -speed  # Make speed positive for PWM duty cycle
    else:
        pi.write(in1, 0)
        pi.write(in2, 0)
    pi.set_PWM_dutycycle(ena, int(speed * 2.55))  # Convert 0–100 to 0–255

# Map Joystick Axis Value to PWM Duty Cycle
def map_axis_to_duty(value):
    # Joystick axis range is -1.0 to 1.0; map to -100 to 100 (duty cycle)
    return int(value * 100)

# Main Function
def main():
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
            set_motor(pi, ENA, IN1, IN2, left_speed)

            # Read Right Joystick Y-axis (Motor B)
            right_y = joystick.get_axis(4)  # Axis 4: Right joystick Y-axis
            right_speed = map_axis_to_duty(right_y)
            set_motor(pi, ENB, IN3, IN4, right_speed)

            time.sleep(0.1)  # Small delay to reduce CPU usage

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Stop Motors and Cleanup
        set_motor(pi, ENA, IN1, IN2, 0)
        set_motor(pi, ENB, IN3, IN4, 0)
        pi.stop()
        pygame.quit()

if __name__ == "__main__":
    main()

