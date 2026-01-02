# Motor Driver Wiring – SN754410 H-Bridge

This project uses **one SN754410 H-bridge IC** to drive a 4-wheel RC car using **tank-style differential drive**.  
Each side (left/right) is controlled independently using PWM for speed and GPIO for direction.

---

## Overview

- **Motor driver:** SN754410 (quad half-H bridge)
- **Controller:** Raspberry Pi 3 B+
- **Drive style:** Tank controls (left motors + right motors)
- **Motors:** 4 DC motors (2 per side, wired in parallel)

---

## Raspberry Pi to  SN754410 Control Wiring

### Left Motor Channel (Motor A)

| Raspberry Pi GPIO | SN754410 Pin | Function |
|------------------|-------------|----------|
| GPIO18 | 1,2EN | Enable / PWM (speed control) |
| GPIO23 | 1A | Direction input |
| GPIO24 | 2A | Direction input |

### Right Motor Channel (Motor B)

| Raspberry Pi GPIO | SN754410 Pin | Function |
|------------------|-------------|----------|
| GPIO19 | 3,4EN | Enable / PWM (speed control) |
| GPIO25 | 3A | Direction input |
| GPIO26 | 4A | Direction input |

---

## SN754410 Outputs to  Motors

| SN754410 Pins | Connected To |
|--------------|--------------|
| 1Y & 2Y | Left motor pair (wired in parallel) |
| 3Y & 4Y | Right motor pair (wired in parallel) |

Each side’s two motors are electrically parallel and behave as a single motor group.

---

## Power Wiring (Critical)

️**All grounds must be common** or the system will not work.

### Logic Power
- **VCC1 (SN754410 logic supply)** → Raspberry Pi **5V**
  - (Some setups may work at 3.3V, but 5V is more reliable)

### Motor Power
- **VCC2 (motor supply)** → External battery voltage  
  - Examples: 6V, 7.4V (2S Li-ion), etc.

### Ground
- **Battery GND**
- **SN754410 GND**
- **Raspberry Pi GND**

️ All tied together.

---

## Direction Logic (How Motion Works)

- **ENA / ENB (Enable pins)** control motor speed via PWM
- **Direction pins (A inputs)** determine rotation direction:

| IN1 | IN2 | Motor State |
|----|----|-------------|
| HIGH | LOW | Forward |
| LOW | HIGH | Reverse |
| LOW | LOW | Brake / Stop |

(Same logic applies for right motor using IN3 / IN4)

---

## Notes & Lessons Learned

- PWM is applied **only** to the enable pins (1,2EN and 3,4EN)
- Direction pins are **digital only**
- Motors will behave erratically if grounds are not shared
- SN754410 can handle moderate current, but motors should not stall for long periods

---

## Why One H-Bridge Works for 4 Wheels

Because the car uses **tank drive**, both left motors always move together, and both right motors always move together.  
This allows one H-bridge chip to control all four wheels efficiently.

---

