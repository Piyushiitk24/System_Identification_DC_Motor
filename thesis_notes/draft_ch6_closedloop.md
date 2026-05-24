# Chapter 6 — Closed-Loop Validation (Plan and Future Work)

> **Draft status:** first full pass, 2026-05-23. Markdown; converts to LaTeX mechanically. This chapter is **forward-looking**: the closed-loop study (Phase 3) has not been performed. It specifies the hypothesis, the artifacts that must be built, the bench protocol, and the expected outcomes, so that the work can be picked up directly. Material traces to status-doc §6 and the cross-session drift result of Section 5.6.

## 6.1 Objective and status

The open-loop identification of Chapters 2–5 produced a validated cascade model (Model C) and quantified its predictive error within the calibration grid. The natural culmination of the thesis is to show that this model is not merely descriptive but *useful*: that a controller designed against Model C tracks a reference better than one designed against a naive single-LTI model of the same plant. **This closed-loop validation has not yet been carried out.** This chapter therefore states the hypothesis precisely, enumerates the software and firmware artifacts the experiment requires, specifies a bench protocol that respects the session-drift findings of Chapter 5, and predicts the performance the open-loop residuals imply. It is written as an actionable plan rather than a results chapter.

## 6.2 Hypothesis

> A controller informed by the cascade model (direction-specific static block, region- and operating-point-dependent FOPDT dynamics) achieves lower reference-tracking error than a controller informed by a single global LTI model fitted to the same plant, with the largest advantage near the deadzone, at the operating-point extremes, and during direction reversals — the regimes where the single-LTI model is most misspecified.

The hypothesis is falsifiable: if the cascade-aware controller does not beat the global-LTI baseline outside measurement noise, the additional model complexity is not justified for control, and that too is a publishable result.

## 6.3 Required artifacts

Three things must be built before any closed-loop trial can be run.

**(1) A multi-transition / feedback-capable simulator.** The current `simulate_model_C` (notebooks 04–05) handles a *single* command transition and raises `NotImplementedError` for more — sufficient for open-loop step validation, insufficient for a closed loop where the command changes every sample. A v2 simulator must (i) accept an arbitrary command trajectory, (ii) select the accel/decel region and operating-point parameters per transition, (iii) handle re-acceleration mid-decay and direction reversal, and (iv) interpolate parameters between calibrated grid points (the bathtub in accel τ and the target-dependence in decel τ make naive interpolation unsafe near the deadzone). It should be **extracted from the notebooks into a reusable module** under `models/`, which currently holds no code, so that firmware-in-the-loop and pure-simulation runs share one implementation.

**(2) Closed-loop firmware.** The active firmware is the open-loop step sequencer (Section 2.7); a controller variant is required — at minimum a velocity PID on the encoder-derived RPM, with the same 10 ms loop rate and telemetry format so the analysis pipeline is reused unchanged. Anti-windup and an explicit deadzone-feedforward term (using the breakaway/dropout thresholds of Section 3.7) are advisable given the plant's static nonlinearity.

**(3) A baseline model to beat.** The naive comparator — **Model A**, a single global LTI model (one gain, one time constant, no deadzone, no region split) — must be fitted from the same calibration data and used to design a matched baseline controller. Without this baseline the central claim cannot be evaluated.

## 6.4 Bench protocol

The single most important protocol requirement follows directly from Section 5.6: **Phase 2.1 parameters must not be reused as ground truth for a later session.** The cross-session drift — a cold-start warm-up transient, a persistent low-speed decel slowdown, and a persistent reverse high-PWM speed-up — is large enough (especially for deceleration) to invalidate stale calibration. The protocol must therefore be self-contained within one session:

1. **In-session calibration block.** At session start, re-run the open-loop step grid (the original Phase 2.1 conditions, ideally extended with the gap-fill PWMs) and re-fit Model C from *that* session's data. This also yields a fresh global-LTI baseline.
2. **Warm-up margin.** Discard or down-weight the first ≈30 s of operation, where forward accel τ is inflated (Section 5.5).
3. **Closed-loop trials.** With both controllers (cascade-aware and baseline) designed against the same-session calibration, run matched reference profiles: setpoint steps across the operating range, a slow ramp through the deadzone in both directions, direction reversals, and a small load/disturbance if a brake is available.
4. **Logging.** Record ambient temperature throughout (not logged in earlier sessions, status-doc §5) and, if possible, a thermistor on the L298N to correlate driver-side drift.

Predictions for the simulator use the same-session calibration, never the historical tables of Chapters 4–5.

## 6.5 Expected performance and risks

The open-loop residuals bound what closed-loop tracking can achieve. The within-session reproducibility floor of ≈3–5 rpm (Section 5.8) is the best steady-state tracking error a perfect controller could reach on this rig; the cascade-aware controller should approach it across the operating range, while the global-LTI baseline should fall short specifically near the deadzone and at the τ extremes. Two risks are known in advance: cold-start transients will degrade tracking for the first ≈30 s until the motor warms, and reverse stops through the deadzone (the noisy 240→100 condition of Sections 4.4 and 5.5) will show elevated, partly irreducible stochasticity. Both should be reported rather than engineered away, as they are properties of the plant.

## 6.6 Broader future work

Beyond the closed-loop study, the open-loop identification leaves several threads, in rough priority order:

- **Friction-explicit dynamic block ("Model D").** A Coulomb/Stribeck extension is motivated by the structured residuals at PWM = 160 and in coast-to-rest decel (Sections 4.3–4.4); it would replace the effective-FOPDT treatment of those regimes.
- **Higher-order dynamics near full drive.** The PWM = 240 rise departs from first order (Section 4.3); a second-order or back-EMF-aware model would reduce the largest accel residuals.
- **Grid extension.** Step-ups from below breakaway (breakaway dynamics), dynamic steps to PWM = 255 (only a static spot-check exists), and decel from start PWMs other than 240 would close the remaining gaps in the operating envelope.
- **Drift-mechanism study.** The unexplained ≈20 % reverse high-PWM τ deflation (Section 5.6) would require controlled idle-versus-immediate session pairs with thermistor instrumentation to falsify any specific cause (lubricant migration, brush-pattern reset, bearing seating).
- **Instrumentation.** Routine ambient-temperature and driver-temperature logging should be standard for all future sessions, given the driver-side thermal sensitivity established in Chapter 3.

## 6.7 Summary

Closing the loop is the one major deliverable the thesis defers. The path is concrete: build a multi-transition simulator (extracted into `models/`), a PID firmware variant with deadzone feedforward, and a global-LTI baseline; run a self-contained session that calibrates in situ, warms up, and then compares cascade-aware against baseline control on matched reference profiles. The open-loop work predicts a ≈3–5 rpm steady tracking floor and a cascade advantage concentrated at the deadzone, the τ extremes, and reversals — with the test designed so that a *null* result (no advantage) would be an equally valid finding. The remaining open-loop refinements (Model D, higher-order dynamics, grid extension, drift mechanism, instrumentation) are independent of, and not blocking for, this closed-loop study.

---

### Sources for this chapter
status-doc §6 (Phase 3 scope, required artifacts, future work) · Section 5.6 (cross-session drift → in-session calibration requirement) · `notebooks/04_validation.ipynb`, `05_gap_fill.ipynb` (single-transition simulator limitation) · `thesis_notes/log.md` 2026-05-22 (Phase 3 implications, in-session calibration).
