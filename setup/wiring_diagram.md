
---

# Diagram: easy + “looks good” (Mermaid)
If you want a diagram **right inside GitHub**, Mermaid is perfect. Drop this into a `diagram.md` or directly into README.

```md
```mermaid
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
