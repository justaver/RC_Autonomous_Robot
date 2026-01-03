import pigpio
import pygame
import time
import serial
import threading

# -----------------------------
# Motor GPIO Pins
# -----------------------------
ENA = 18
IN1 = 23
IN2 = 24

ENB = 19
IN3 = 25
IN4 = 26

# -----------------------------
# TF-Luna UART settings
# -----------------------------
LIDAR_PORT = "/dev/serial0"
LIDAR_BAUD = 115200
CONTINUOUS_MODE_COMMAND = bytes([0x5A, 0x05, 0x07, 0x01, 0x00, 0x66])

STOP_DISTANCE_CM = 35
LIDAR_TIMEOUT_SEC = 0.25  # if data older than this, treat as stale

# -----------------------------
# pigpio
# -----------------------------
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    raise SystemExit(1)

for pin in [IN1, IN2, IN3, IN4]:
    pi.set_mode(pin, pigpio.OUTPUT)

def set_motor(ena, in1, in2, speed):
    # speed: -100..100
    if speed > 0:
        pi.write(in1, 1)
        pi.write(in2, 0)
    elif speed < 0:
        pi.write(in1, 0)
        pi.write(in2, 1)
        speed = -speed
    else:
        pi.write(in1, 0)
        pi.write(in2, 0)

    duty = int(max(0, min(100, speed)) * 2.55)
    pi.set_PWM_dutycycle(ena, duty)

def map_axis_to_duty(value):
    return int(value * 100)

# -----------------------------
# TF-Luna reader (robust sync)
# -----------------------------
def read_tfluna_frame_sync(ser):
    b = ser.read(1)
    if not b:
        return None

    while b[0] != 0x59:
        b = ser.read(1)
        if not b:
            return None

    b2 = ser.read(1)
    if not b2 or b2[0] != 0x59:
        return None

    payload = ser.read(7)
    if len(payload) != 7:
        return None

    frame = bytes([0x59, 0x59]) + payload
    chk = sum(frame[:8]) & 0xFF
    if chk != frame[8]:
        return None

    dist_cm = frame[2] + (frame[3] << 8)
    strength = frame[4] + (frame[5] << 8)
    return dist_cm, strength

# Shared LiDAR state
lidar_lock = threading.Lock()
lidar_dist_cm = None
lidar_strength = None
lidar_last_time = 0.0
lidar_ok = 0
lidar_bad = 0

stop_threads = False

def lidar_thread_fn():
    global lidar_dist_cm, lidar_strength, lidar_last_time, lidar_ok, lidar_bad

    ser = serial.Serial(LIDAR_PORT, LIDAR_BAUD, timeout=0.05)
    time.sleep(0.2)

    # Force continuous output (like your smooth test)
    ser.reset_input_buffer()
    ser.write(CONTINUOUS_MODE_COMMAND)
    ser.flush()
    time.sleep(0.1)

    while not stop_threads:
        out = read_tfluna_frame_sync(ser)
        with lidar_lock:
            if out:
                lidar_ok += 1
                lidar_dist_cm, lidar_strength = out
                lidar_last_time = time.time()
            else:
                lidar_bad += 1

    ser.close()

def main():
    global stop_threads

    # Start LiDAR thread
    t = threading.Thread(target=lidar_thread_fn, daemon=True)
    t.start()

    # Joystick setup
    pygame.init()
    pygame.joystick.init()
    while pygame.joystick.get_count() == 0:
        print("Waiting for controller...")
        time.sleep(1)
        pygame.joystick.quit()
        pygame.joystick.init()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick connected:", joystick.get_name())

    # MAIN LOOP
    last_debug = 0

    try:
        while True:
            pygame.event.pump()

            left_speed  = map_axis_to_duty(joystick.get_axis(1))
            right_speed = map_axis_to_duty(joystick.get_axis(3))

            # Determine which sign means "forward" on YOUR setup:
            # If pushing stick forward makes speeds negative, keep this:
            forward_commanded = (left_speed < 0) or (right_speed < 0)
            # If it blocks the wrong direction, flip to > 0.

            # Get latest LiDAR
            with lidar_lock:
                dist = lidar_dist_cm
                strength = lidar_strength
                age = time.time() - lidar_last_time if lidar_last_time else 999
                ok = lidar_ok
                bad = lidar_bad

            # Guard
            lidar_fresh = age <= LIDAR_TIMEOUT_SEC

            if forward_commanded:
                if (not lidar_fresh) or (dist is None):
                    left_speed = 0
                    right_speed = 0
                elif dist <= STOP_DISTANCE_CM:
                    left_speed = 0
                    right_speed = 0

            # Drive motors
            set_motor(ENA, IN1, IN2, left_speed)
            set_motor(ENB, IN3, IN4, right_speed)

            # Minimal debug (prints 2x/sec so it won't kill the loop)
            now = time.time()
            if now - last_debug > 0.5:
                last_debug = now
                print(f"dist={dist}cm strength={strength} age={age:.2f}s OK/Bad={ok}/{bad} L={left_speed} R={right_speed}")

            time.sleep(0.02)

    finally:
        stop_threads = True
        time.sleep(0.1)
        set_motor(ENA, IN1, IN2, 0)
        set_motor(ENB, IN3, IN4, 0)
        pi.stop()
        pygame.quit()

if __name__ == "__main__":
    main()
