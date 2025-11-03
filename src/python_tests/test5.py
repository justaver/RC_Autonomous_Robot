import pigpio
import pygame
import time

# GPIO Pins for Motors
ENA = 18  # PWM for Left Motor (Motor A)
IN1 = 23  # Left Motor Forward
IN2 = 24  # Left Motor Reverse
ENB = 19  # PWM for Right Motor (Motor B)
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

    # Debug: Print the duty cycle for the PWM pin
    if ena == ENA:
        print(f"GPIO18 (ENA): Speed = {speed}, PWM Duty Cycle = {int(speed * 2.55)}")
    elif ena == ENB:
        print(f"GPIO19 (ENB): Speed = {speed}, PWM Duty Cycle = {int(speed * 2.55)}")
    pi.set_PWM_dutycycle(ena, int(speed * 2.55))  # Convert 0–100 to 0–255

# Map Joystick Axis Value to PWM Duty Cycle
def map_axis_to_duty(value):
    # Joystick axis range is -1.0 to 1.0; map to -100 to 100
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

        # Debug: Print all joystick axis values
            for i in range(joystick.get_numaxes()):
                print(f"Axis {i}: {joystick.get_axis(i):.2f}")

        # Read Left Joystick Y-axis (Motor A)
            left_y = joystick.get_axis(1)  # Axis 1: Left joystick Y-axis
            left_speed = map_axis_to_duty(left_y)
            print(f"Left Motor: Speed = {left_speed}")
            set_motor(pi, ENA, IN1, IN2, left_speed)

        # Read Right Joystick Y-axis (Motor B)
            right_y = joystick.get_axis(3)  # Axis 4: Right joystick Y-axis
            right_speed = map_axis_to_duty(right_y)
            print(f"Right Motor: Speed = {right_speed}")
            set_motor(pi, ENB, IN3, IN4, right_speed)

            time.sleep(0.1)

    finally:
        set_motor(pi, ENA, IN1, IN2, 0)
        set_motor(pi, ENB, IN3, IN4, 0)
        pi.stop()
        pygame.quit()

if __name__ == "__main__":
    main()

