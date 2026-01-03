import serial
import time

SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 115200

# Command you already used: enable continuous output mode
CONTINUOUS_MODE_COMMAND = bytes([0x5A, 0x05, 0x07, 0x01, 0x00, 0x66])

def send_command(ser, command):
    # Clear any old bytes so we don't mis-parse
    ser.reset_input_buffer()
    ser.write(command)
    ser.flush()
    time.sleep(0.1)  # give it a moment

def read_frame_sync(ser):
    """
    Robust frame sync for TF-Luna:
    Wait for header 0x59 0x59 then read remaining 7 bytes.
    Returns (dist_cm, strength, temp_c) or None.
    """
    # Scan for first 0x59
    b = ser.read(1)
    if not b:
        return None
    while b[0] != 0x59:
        b = ser.read(1)
        if not b:
            return None

    # Check second 0x59
    b2 = ser.read(1)
    if not b2 or b2[0] != 0x59:
        return None

    payload = ser.read(7)
    if len(payload) != 7:
        return None

    frame = bytes([0x59, 0x59]) + payload

    # checksum
    chk = sum(frame[:8]) & 0xFF
    if chk != frame[8]:
        return None

    dist_cm = frame[2] + (frame[3] << 8)
    strength = frame[4] + (frame[5] << 8)
    temp_c = (frame[6] + (frame[7] << 8)) / 8.0 - 256

    return dist_cm, strength, temp_c

def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(0.2)

    print(f"Opened {SERIAL_PORT} @ {BAUD_RATE}")
    print("Sending 'continuous output' command...")
    send_command(ser, CONTINUOUS_MODE_COMMAND)
    print("Reading frames... Move an object between ~30cm and ~200cm. Ctrl+C to stop.\n")

    ok = 0
    bad = 0

    try:
        while True:
            out = read_frame_sync(ser)
            if out:
                ok += 1
                dist_cm, strength, temp_c = out
                print(f"Dist: {dist_cm:4d} cm | Strength: {strength:5d} | Temp: {temp_c:5.1f} C | OK/Bad: {ok}/{bad}")
            else:
                bad += 1
                # Print less often to avoid spam
                if bad % 20 == 0:
                    print(f"(Waiting for valid frames...) OK/Bad: {ok}/{bad}")

    finally:
        ser.close()

if __name__ == "__main__":
    main()
