# RC / Autonomous Car (Raspberry Pi)

> A Raspberry Pi–based RC car that supports **manual driving**, **collision-guarded driving**, and **basic autonomous navigation**, built as a learning and experimentation platform for embedded systems and robotics.

This project started as a simple RC car and evolved into a **multi-mode robotic system** with real sensor integration, safety logic, and clean software structure.

The goal is not perfection — the goal is **understanding, iteration, and reuse**.

---

## What This Project Does (At a Glance)

- Manual RC driving using an Xbox controller (Bluetooth)
- Collision-guarded driving using TF-Luna LiDAR
- Autonomous “Roomba-style” obstacle avoidance
- Clean separation between:
  - motor control
  - sensor input
  - control logic
- Designed so future versions can be built smaller or expanded without rethinking everything

---

## Current Modes

### 1. Manual Mode
- Pure tank drive
- Left stick → left motors
- Right stick → right motors
- No sensor interference

### 2. Guard Mode
- Manual driving **with safety**
- TF-Luna monitors forward distance
- Behavior:
  - Far away → full speed
  - Getting close → gradual slowdown
  - Too close → forward motion blocked
- Reverse and steering away always allowed

### 3. Autonomous Mode
- No joystick driving required
- Behavior loop:
  - Drive forward
  - Detect obstacle
  - Reverse briefly
  - Turn randomly
  - Continue forward
- Simple, reliable, and expandable

---

## Controller Controls (Xbox)

| Button | Action |
|------|-------|
| **A** | Arm / Disarm motors |
| **B** | Emergency stop (instant disarm) |
| **X** | Cycle modes (Manual → Guard → Auto) |
| **LB** | Decrease stop distance |
| **RB** | Increase stop distance |
| **Y** | Currently unused (reserved for future features) |

---

## Hardware Overview

- **Controller:** Raspberry Pi 3 B+
- **Motors:** 4× DC motors (tank drive)
- **Motor Driver:** SN754410 H-Bridge
- **Sensor:** TF-Luna LiDAR (UART)
- **Control:** Xbox controller over Bluetooth
- **Power:** External battery for motors, Pi powered separately

---

## Why the Architecture Matters

This project intentionally separates responsibilities:

- **Motor layer:**  
  Handles GPIO, PWM, and direction logic only

- **Sensor layer:**  
  TF-Luna runs in its own thread and continuously streams distance data  
  (prevents stale readings and blocking behavior)

- **Control layer:**  
  Decides *what the car should do* based on:
  - mode
  - joystick input
  - sensor data

This structure is what made the system:
- stable
- responsive
- easy to extend

---

## Key Lessons Learned

- Sensors should **never block** the main control loop  
- LiDAR must be read continuously (threaded) to avoid stale data
- Static motor friction requires higher initial PWM (“kick”)
- Guard logic must fail **safe**, not optimistic
- Button mappings vary — always confirm them programmatically
- Good architecture matters more than fancy algorithms

---

## Project Status

This project is **functionally complete** for its current goals.

Things that work reliably:
- Manual driving
- Collision guard
- Autonomous navigation
- Mode switching
- Emergency stop
- Live parameter tuning

---

## Future Ideas (Optional)

These are *nice-to-have*, not requirements:

- Save tuning parameters to a config file
- On-screen telemetry (HUD)
- Camera-based perception
- Multiple LiDARs or sensor fusion
- Smaller chassis using the same control logic
- Cleaner module separation (`motor.py`, `lidar.py`, etc.)

---

## Why This Project Exists

This project exists to:
- learn embedded systems by **building**, not just reading
- create something reusable for future robotics projects
- understand how software architecture affects real hardware
- have a reference system that “just works” when starting something new
- 

---


---

# Wiring Diagram:
```md
flowchart LR
  Pi[Raspberry Pi 3 B+]

  subgraph MotorDriver[SN754410 H-Bridge]
    ENA[1,2EN (PWM)]
    IN1[1A]
    IN2[2A]
    ENB[3,4EN (PWM)]
    IN3[3A]
    IN4[4A]
  end

  subgraph Motors[DC Motors]
    L[Left motor pair (parallel)]
    R[Right motor pair (parallel)]
  end

  subgraph LiDAR[TF-Luna (UART)]
    TX[TX -> Pi RX]
    RX[RX <- Pi TX]
    VCC[5V]
    GND[GND]
  end

  Pi -- GPIO18 --> ENA
  Pi -- GPIO23 --> IN1
  Pi -- GPIO24 --> IN2
  Pi -- GPIO19 --> ENB
  Pi -- GPIO25 --> IN3
  Pi -- GPIO26 --> IN4

  MotorDriver --> L
  MotorDriver --> R

  Pi <-- UART --> LiDAR

  Power[(Battery / Power)]
  Power --- MotorDriver
  Power --- Pi
  Power --- LiDAR

  note1[[All grounds tied together]]
  Power --- note1

