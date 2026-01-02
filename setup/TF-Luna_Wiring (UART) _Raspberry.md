# TF-Luna Wiring (UART) — Raspberry Pi 3 B+

This project uses a **TF-Luna LiDAR** in **UART mode** to measure forward distance for:
- Guard mode (slowdown + stop)
- Autonomous obstacle avoidance

---

## TF-Luna Pinout (Typical 6-pin)

Most TF-Luna modules expose 6 pins:

- **VCC** (5V)
- **GND**
- **TX** (LiDAR → Pi RX)
- **RX** (Pi TX → LiDAR RX) *(optional, only needed if sending commands)*
- **SDA** *(I2C, unused here)*
- **SCL** *(I2C, unused here)*

We use **UART**, so SDA/SCL are not connected.

---

## Wiring: TF-Luna → Raspberry Pi (UART)

| TF-Luna Pin | Raspberry Pi Pin | Notes |
|------------|-------------------|------|
| VCC | 5V (Pin 2 or 4) | TF-Luna power |
| GND | GND (Pin 6 or any GND) | Must share ground with everything |
| TX | GPIO15 / RXD0 (Pin 10) | **LiDAR TX → Pi RX** |
| RX | GPIO14 / TXD0 (Pin 8) | Only needed if sending commands |

---

## Important: Logic Level Safety

Raspberry Pi GPIO is **3.3V logic**.

Some TF-Luna modules output **5V TTL** on TX. If your setup is stable, great — but for long-term reliability, it’s safest to use:
- a **voltage divider** on TF-Luna TX → Pi RX, or
- a **logic level shifter**

Symptoms of level issues: corrupted frames, flaky/stale readings, random checksum failures.

---

## Enable UART on the Pi

1. Enable serial hardware (UART)
2. Disable serial console login (if enabled)

Common check:
- device should exist: `/dev/serial0`

---

## Confirm Data Stream (Quick Test)

You should see repeating `59 59` headers:

```bash
sudo timeout 2s cat /dev/serial0 | hexdump -C | head -n 30
