# Chapter 1 — Introduction

> **Draft status:** first full pass, 2026-05-23. Markdown; converts to LaTeX mechanically. Written last, as planned. This is **Chapter 1**; the body chapters that follow are Chapters 2–6 and the Conclusion is Chapter 7.

## Background and motivation

Brushed DC gearmotors driven by integrated H-bridge modules are the default actuator of low-cost robotics and motion control: they are inexpensive, easy to wire, and adequate for a wide range of speed- and position-control tasks. Designing a controller for one, however, requires a model, and the model most engineers reach for — the classical linear DC-motor transfer function, a first-order electrical stage cascaded with a first-order mechanical stage, symmetric in direction and linear in command — describes an idealised machine driven by an ideal amplifier. Real low-cost hardware departs from that ideal in ways that matter for control. An L298N bipolar H-bridge drops a significant and direction-dependent voltage across its output transistors, so the motor never sees the supply rail and sees a different fraction of it forwards than backwards. Static friction creates a deadzone with hysteresis: the command needed to start the shaft from rest is well above the command at which it stops. And the transient response is not a single time constant — it varies with operating point and differs between speeding up and slowing down.

A controller tuned against a single global linear model inherits all of these unmodelled effects as tracking error, concentrated exactly where the idealisation is worst: near the deadzone, at the extremes of the operating range, and during direction reversals. The remedy is system identification — extracting, from measurements of the real plant, a model that captures these nonlinearities while remaining compact and physically interpretable enough to inform control design. The central design question is one of *structure*: whether to fit a monolithic black-box model, or to decompose the plant into physically meaningful blocks whose parameters can be identified, interpreted, and trusted separately.

## Problem statement

This thesis addresses the identification of one concrete rig: an Arduino Uno R4 Minima commanding a single channel of an L298N H-bridge, which drives a 12 V, 60:1 geared DC motor instrumented with a 600 PPR quadrature encoder. The goal is a model that captures, in an interpretable form, the five departures from the textbook ideal that this hardware exhibits — driver voltage loss, a hysteretic deadzone with forward/reverse breakaway asymmetry, forward/reverse gain mismatch, operating-point-dependent dynamics, and a small command-to-response delay — and that is validated by cross-validation rather than merely fitted to the calibration data. The structural hypothesis pursued throughout is that the plant is best described not as a single linear system but as a **cascade**: a static block that maps PWM command to delivered motor voltage (carrying the deadzone and the directional asymmetry), followed by a motor block that maps voltage to speed (approximately symmetric, with operating-point-dependent transient dynamics). Establishing whether the data actually support this decomposition — rather than assuming it — is the first substantive result.

## Objectives and scope

The work is scoped to **open-loop** identification and its validation:

1. Characterise the steady-state behaviour of the rig and test the cascade decomposition by separating the driver (PWM→voltage) and motor (voltage→speed) contributions to its asymmetry.
2. Characterise the deadzone and its hysteresis.
3. Identify the transient dynamics as per-operating-point first-order-plus-dead-time (FOPDT) responses, and determine their dependence on operating point, direction, and acceleration/deceleration regime.
4. Validate the resulting model within its calibration grid, quantifying predictive error, and bound its session-to-session reproducibility.

Demonstrating the model's value in **closed loop** — showing that a cascade-aware controller outperforms one designed against a naive global linear model — is the natural culmination. Chapter 6 carries it out on the real rig with a pre-registered comparison and finds a mixed, specific result: the cascade controller wins clearly on stepwise references (including reversals) but loses on a slow ramp through the deadzone, a counter-example that localises the limitation to one identifiable feature of the design (the inverse-static feedforward's discontinuity at the breakaway edge).

## Approach

The methodology is hardware-in-the-loop. Firmware on the Arduino generates the PWM command, decodes the encoder in interrupts, and streams time-stamped telemetry; automated firmware executes pre-programmed step sequences hands-off so that the dynamic data are free of operator timing variability. The telemetry is captured, split into per-trial records, and analysed in Python/Jupyter, with raw measurements held immutable and all derived quantities written separately. Identification proceeds in phases — a static sweep, a dedicated deadzone characterisation, an automated step-response campaign fitted to FOPDT, a leave-one-out validation, and a later gap-fill session that adds operating points and measures drift — each documented as it was run. The cascade structure is not imposed; it is adopted only because the data localise the plant's asymmetry and its instability to one identifiable block.

## Contributions

This thesis makes the following contributions:

- **An empirically justified cascade model (Model C)** of a DC-motor-plus-L298N drive, in which the decomposition is earned from the data: the large directional asymmetry and the only measurable session drift both localise to the driver block, while the motor block is direction-symmetric to within ≈9 % and reproducible to ≈1 %.
- **A region- and operating-point-dependent dynamic characterisation** showing that a single global time constant is misspecified by ≈2×: acceleration time constants follow a broad bathtub in PWM, deceleration is roughly twice as slow and varies non-monotonically with the target through the deadzone, and the forward/reverse asymmetry reverses sign between acceleration and deceleration.
- **A validation methodology** — leave-one-out cross-validation, adopted because no held-out dataset existed — that both quantified predictive error (≈0.1–1 rpm within the grid) and surfaced a cold-start stochasticity effect, which a subsequent warm-motor session then confirmed by a falsifiable prediction.
- **A methodological finding** on session-to-session drift: calibration does not transfer cleanly across sessions (especially for deceleration), so later work must recalibrate in situ — a constraint that directly shapes the proposed closed-loop protocol.
- **A pre-registered closed-loop test** of the cascade structure against the single-LTI baseline — the same model fit from the same in-session data and tuned by the same IMC rule. The result is mixed and informative: cascade wins by 1–5 rpm RMSE on three of four reference profiles (staircase, reversal, small-signal) and loses by ≈1 rpm on a slow bidirectional ramp through the deadzone, a counter-example that localises the limitation to the inverse-static feedforward's discontinuity at the breakaway edge.

## Thesis outline

**Chapter 2 (Hardware Setup)** describes the rig, its wiring and instrumentation, the encoder and velocity-estimation chain, and the commissioning that fixed an inverted encoder sign and established the sign conventions used throughout. **Chapter 3 (Static Characterization)** identifies the steady-state map, separates it into driver and motor blocks, quantifies the deadzone hysteresis, and presents the evidence that justifies the cascade structure. **Chapter 4 (Dynamic Characterization)** fits the FOPDT responses across twenty operating points, establishes the operating-point, direction, and accel/decel dependence of the dynamics, and defines Model C. **Chapter 5 (Validation)** applies leave-one-out cross-validation, reports the predictive error, and develops and confirms the cold-start hypothesis and the cross-session drift result. **Chapter 6 (Closed-Loop Validation)** carries out a pre-registered closed-loop comparison of a cascade-aware controller against a single-LTI baseline tuned from the same in-session calibration, finds a mixed result (cascade wins on three of four reference profiles, loses on the fourth), and traces the failure to a specific feature of the design. The **Conclusion** synthesises the findings, states the limitations, and lays out the remaining work.

---

### Sources for this chapter
`plan.md` (thesis goals and toolchain) · Chapters 2–6 and the Conclusion (contributions, outline) · status-doc §1 (project overview), §4 (final model state). Headline figures previewed here are derived and cited in full in the body chapters.
