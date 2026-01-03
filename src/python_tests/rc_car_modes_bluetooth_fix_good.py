# rc_car_modes.py
#
# One script with:
# - Threaded TF-Luna LiDAR reader (smooth continuous stream)
# - MANUAL mode (tank drive)
# - GUARD mode (soft slowdown + hard stop when obstacle ahead)
# - AUTO mode (simple "roomba-lite" forward/avoid/turn)
# - Mode switching + safety controls via your confirmed Xbox button mapping
# - Controller disconnect/reconnect handling (no need to restart the script)
#
# Your confirmed button mapping (pygame):
#   A  = 0
#   B  = 1
#   X  = 3
#   Y  = 4
#   LB = 6
#   RB = 7
#
# Controls:
#   A  -> Arm / Disarm motors (toggle)
#   B  -> Emergency Stop (disarm + stop)
#   X  -> Cycle mode: MANUAL -> GUARD -> AUTO -> MANUAL
#   LB -> Decrease STOP_DISTANCE_CM by 5
#   RB -> Increase STOP_DISTANCE_CM by 5
#   Y  -> currently unused (free to map later)
#
# Notes:
# - If forward direction feels inverted, change FORWARD_IS_NEGATIVE.
# - AUTO speeds increased so it won't "need a nudge" to start moving.

import time
import serial
import threading
import random
import pigpio
import pygame

# =============================
# USER TUNABLE SETTINGS
# =============================

# Motor pins
ENA = 18
IN1 = 23
IN2 = 24
ENB = 19
IN3 = 25
IN4 = 26

# Joystick axes
LEFT_AXIS_Y  = 1
RIGHT_AXIS_Y = 3

# Joystick behavior
DEADZONE = 0.12            # ignore tiny stick drift
MAX_SPEED = 100            # -100..100
LOOP_DT = 0.02             # main loop sleep (~50 Hz)

# If forward is negative on your controller (common), keep True
FORWARD_IS_NEGATIVE = True

# LiDAR (TF-Luna)
LIDAR_PORT = "/dev/serial0"
LIDAR_BAUD = 115200
CONTINUOUS_MODE_COMMAND = bytes([0x5A, 0x05, 0x07, 0x01, 0x00, 0x66])

# Guard distances (cm)
STOP_DISTANCE_CM = 30      # hard stop threshold (tune)
SLOW_DISTANCE_CM = 60      # start slowing down when closer than this
LIDAR_TIMEOUT_SEC = 0.25   # if lidar data older than this, treat stale

# Strength filter (optional) - set to 0 to disable
MIN_STRENGTH = 0

# AUTO mode behavior
AUTO_FWD_SPEED = 60
AUTO_REV_SPEED = -60
AUTO_TURN_SPEED = 55
AUTO_STOP_CM = 35
AUTO_REVERSE_SEC = 0.6
AUTO_TURN_SEC_MIN = 0.4
AUTO_TURN_SEC_MAX = 0.9

# =============================
# BUTTONS (YOUR CONFIRMED MAPPING)
# =============================
BTN_A  = 0   # Arm toggle
BTN_B  = 1   # Emergency stop (disarm)
BTN_X  = 3   # Cycle mode
BTN_Y  = 4   # Unused (free)
BTN_LB = 6   # Threshold down
BTN_RB = 7   # Threshold up

# =============================
# INTERNALS
# =============================
MODE_MANUAL = 0
MODE_GUARD  = 1
MODE_AUTO   = 2
MODE_NAMES = {0: "MANUAL", 1: "GUARD", 2: "AUTO"}

# pigpio setup
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    raise SystemExit(1)

for pin in [IN1, IN2, IN3, IN4]:
    pi.set_mode(pin, pigpio.OUTPUT)

def set_motor(ena, in1, in2, speed):
    """speed: -100..100"""
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

def stop_motors():
    set_motor(ENA, IN1, IN2, 0)
    set_motor(ENB, IN3, IN4, 0)

def apply_deadzone(x, dz=DEADZONE):
    if abs(x) < dz:
        return 0.0
    return x

def axis_to_speed(axis_val):
    v = apply_deadzone(axis_val)
    return int(max(-1.0, min(1.0, v)) * MAX_SPEED)

def forward_commanded(left_speed, right_speed):
    if FORWARD_IS_NEGATIVE:
        return (left_speed < 0) or (right_speed < 0)
    else:
        return (left_speed > 0) or (right_speed > 0)

def clamp_forward_by_lidar(speed, dist_cm):
    """Soft slowdown + hard stop (forward only). Reverse always allowed."""
    if dist_cm is None:
        return speed

    is_fwd = (speed < 0) if FORWARD_IS_NEGATIVE else (speed > 0)
    if not is_fwd:
        return speed

    if dist_cm <= STOP_DISTANCE_CM:
        return 0

    if dist_cm < SLOW_DISTANCE_CM:
        span = max(1, (SLOW_DISTANCE_CM - STOP_DISTANCE_CM))
        factor = (dist_cm - STOP_DISTANCE_CM) / span
        factor = max(0.0, min(1.0, factor))
        return int(speed * factor)

    return speed

# -----------------------------
# Controller reconnect helpers
# -----------------------------
def init_joystick():
    """Return an initialized joystick or None if none present."""
    pygame.joystick.quit()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        return None
    j = pygame.joystick.Joystick(0)
    j.init()
    print("Joystick connected:", j.get_name())
    return j

# -----------------------------
# TF-Luna threaded reader
# -----------------------------
lidar_lock = threading.Lock()
lidar_dist_cm = None
lidar_strength = None
lidar_last_time = 0.0
lidar_ok = 0
lidar_bad = 0
stop_threads = False

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

def lidar_thread_fn():
    global lidar_dist_cm, lidar_strength, lidar_last_time, lidar_ok, lidar_bad

    ser = serial.Serial(LIDAR_PORT, LIDAR_BAUD, timeout=0.05)
    time.sleep(0.2)

    # Force continuous streaming
    ser.reset_input_buffer()
    ser.write(CONTINUOUS_MODE_COMMAND)
    ser.flush()
    time.sleep(0.1)

    while not stop_threads:
        out = read_tfluna_frame_sync(ser)
        now = time.time()
        with lidar_lock:
            if out:
                d, s = out
                if MIN_STRENGTH and s < MIN_STRENGTH:
                    lidar_bad += 1
                else:
                    lidar_ok += 1
                    lidar_dist_cm = d
                    lidar_strength = s
                    lidar_last_time = now
            else:
                lidar_bad += 1

    ser.close()

def get_lidar():
    with lidar_lock:
        dist = lidar_dist_cm
        strength = lidar_strength
        age = (time.time() - lidar_last_time) if lidar_last_time else 999.0
        ok = lidar_ok
        bad = lidar_bad
    return dist, strength, age, ok, bad

# -----------------------------
# AUTO state machine
# -----------------------------
AUTO_STATE_FWD = 0
AUTO_STATE_REV = 1
AUTO_STATE_TURN = 2

def main():
    global stop_threads, STOP_DISTANCE_CM

    # Start LiDAR thread
    t = threading.Thread(target=lidar_thread_fn, daemon=True)
    t.start()

    # Init pygame + joystick
    pygame.init()
    pygame.joystick.init()

    joy = init_joystick()
    while joy is None:
        print("Waiting for controller...")
        time.sleep(1)
        joy = init_joystick()

    armed = False
    mode = MODE_MANUAL

    # Button edge detection (reinitialized on reconnect)
    prev_buttons = [0] * joy.get_numbuttons()

    # Auto state
    auto_state = AUTO_STATE_FWD
    auto_state_until = 0.0
    auto_turn_dir = 1

    last_status = 0.0

    try:
        while True:
            pygame.event.pump()

            # ---- Controller disconnect / reconnect handling ----
            if pygame.joystick.get_count() == 0:
                if armed:
                    armed = False
                    stop_motors()
                    print("[CTRL] Controller disconnected -> DISARMED + MOTORS STOPPED")

                # Wait and attempt reconnect
                time.sleep(0.5)
                joy = init_joystick()
                if joy is not None:
                    prev_buttons = [0] * joy.get_numbuttons()
                    print("[CTRL] Controller reconnected")
                continue

            # Read buttons with edge detect
            buttons = [joy.get_button(i) for i in range(joy.get_numbuttons())]

            def pressed(btn):
                return btn < len(buttons) and buttons[btn] == 1 and prev_buttons[btn] == 0

            # A toggles arm
            if pressed(BTN_A):
                armed = not armed
                if not armed:
                    stop_motors()
                print(f"[ARM] {'ARMED' if armed else 'DISARMED'}")

            # B emergency stop
            if pressed(BTN_B):
                armed = False
                stop_motors()
                print("[E-STOP] DISARMED + MOTORS STOPPED")

            # X cycles mode
            if pressed(BTN_X):
                mode = (mode + 1) % 3
                print(f"[MODE] {MODE_NAMES[mode]}")
                if mode == MODE_AUTO:
                    auto_state = AUTO_STATE_FWD
                    auto_state_until = 0.0

            # RB/LB tune stop distance
            if pressed(BTN_RB):
                STOP_DISTANCE_CM = min(200, STOP_DISTANCE_CM + 5)
                print(f"[TUNE] STOP_DISTANCE_CM = {STOP_DISTANCE_CM}")

            if pressed(BTN_LB):
                STOP_DISTANCE_CM = max(5, STOP_DISTANCE_CM - 5)
                print(f"[TUNE] STOP_DISTANCE_CM = {STOP_DISTANCE_CM}")

            prev_buttons = buttons

            # Read LiDAR
            dist, strength, age, ok, bad = get_lidar()
            lidar_fresh = age <= LIDAR_TIMEOUT_SEC

            left_speed = 0
            right_speed = 0

            # If not armed, always stop motors
            if not armed:
                stop_motors()
                time.sleep(LOOP_DT)
                continue

            # MODE: MANUAL / GUARD
            if mode in (MODE_MANUAL, MODE_GUARD):
                left_speed = axis_to_speed(joy.get_axis(RIGHT_AXIS_Y))
                right_speed = axis_to_speed(joy.get_axis(LEFT_AXIS_Y))

                if mode == MODE_GUARD:
                    if forward_commanded(left_speed, right_speed) and not lidar_fresh:
                        left_speed = 0
                        right_speed = 0
                    else:
                        left_speed = clamp_forward_by_lidar(left_speed, dist)
                        right_speed = clamp_forward_by_lidar(right_speed, dist)

            # MODE: AUTO
            elif mode == MODE_AUTO:
                now = time.time()

                if not lidar_fresh or dist is None:
                    left_speed = 0
                    right_speed = 0
                else:
                    if auto_state == AUTO_STATE_FWD:
                        fwd = AUTO_FWD_SPEED if not FORWARD_IS_NEGATIVE else -AUTO_FWD_SPEED
                        left_speed = fwd
                        right_speed = fwd

                        if dist <= AUTO_STOP_CM:
                            auto_state = AUTO_STATE_REV
                            auto_state_until = now + AUTO_REVERSE_SEC

                    elif auto_state == AUTO_STATE_REV:
                        rev = AUTO_REV_SPEED if not FORWARD_IS_NEGATIVE else -AUTO_REV_SPEED
                        left_speed = rev
                        right_speed = rev

                        if now >= auto_state_until:
                            auto_state = AUTO_STATE_TURN
                            auto_turn_dir = random.choice([-1, 1])
                            auto_state_until = now + random.uniform(AUTO_TURN_SEC_MIN, AUTO_TURN_SEC_MAX)

                    elif auto_state == AUTO_STATE_TURN:
                        base = AUTO_TURN_SPEED
                        if FORWARD_IS_NEGATIVE:
                            left_speed = (-base) * auto_turn_dir
                            right_speed = (base) * auto_turn_dir
                        else:
                            left_speed = (base) * auto_turn_dir
                            right_speed = (-base) * auto_turn_dir

                        if now >= auto_state_until:
                            auto_state = AUTO_STATE_FWD

            # Apply motors
            set_motor(ENA, IN1, IN2, left_speed)
            set_motor(ENB, IN3, IN4, right_speed)

            # Status print (2x/sec)
            now = time.time()
            if now - last_status > 0.5:
                last_status = now
                print(f"[{MODE_NAMES[mode]}] armed={armed} dist={dist}cm age={age:.2f}s OK/Bad={ok}/{bad} STOP={STOP_DISTANCE_CM} L={left_speed} R={right_speed}")

            time.sleep(LOOP_DT)

    finally:
        stop_threads = True
        time.sleep(0.1)
        stop_motors()
        pi.stop()
        pygame.quit()

if __name__ == "__main__":
    main()
