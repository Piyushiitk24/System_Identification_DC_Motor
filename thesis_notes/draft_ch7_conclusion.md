# Chapter 7 — Conclusion

> **Draft status:** first full pass, 2026-05-23. Markdown; converts to LaTeX mechanically. Synthesises Chapters 2–6; numbers restated from the chapter tables (status-doc §4–§6). Conventionally placed after the body chapters; the Introduction is written last.

## Summary of work

This thesis identified a compact, physically interpretable model of a DC gearmotor driven by an L298N H-bridge, measured by a quadrature encoder on an Arduino Uno R4 Minima. The model is a **cascade** — `PWM command → static driver-voltage block → motor dynamic block → RPM` (Model C) — and each block was identified through a sequence of bench and analysis phases: a static sweep and deadzone characterisation (Phase 1.1/1.2), an automated step-response campaign (Phase 2.1), a leave-one-out validation of that campaign (Phase 2.2, analysis only), and a gap-fill bench session two weeks later that added operating points and bounded session-to-session drift.

## Principal findings

**The cascade decomposition is empirically justified, not assumed.** The plant's large forward/reverse asymmetry localises almost entirely to the driver: the PWM→voltage map differs by direction by a factor of up to 2.2 near the deadzone edge, while the motor's voltage→speed gain is direction-symmetric to within 9 % (`K_fwd = 26.94`, `K_rev = 24.52` rpm/V). Independently, the only measurable session drift sits on the driver side as well, with the motor block reproducible to ≈1 %. Asymmetry and instability therefore both belong to one identifiable block, which is precisely what makes the cascade the right structure (Chapter 3).

**The dynamics are region-dependent — Model C, not a single LTI system.** Acceleration is well described by FOPDT whose time constant follows a broad bathtub in PWM (≈81 ms at the mid-range minimum, rising to ≈200 ms near breakaway and ≈150 ms near full drive). Deceleration is a separate regime: its time constant is roughly twice the acceleration value and is non-monotone in the target, peaking at ≈321–366 ms for stops that coast through the high-friction deadzone. The forward/reverse asymmetry even reverses sign between acceleration and deceleration — a small but real departure from a perfectly clean cascade. A single global time constant is misspecified by ≈2× and is rejected (Chapter 4).

**The model validates within its grid, and validation surfaced a cold-start effect.** Leave-one-out cross-validation — adopted because no held-out dataset ever existed — gives a predictive excess over the in-sample fit of +1.06 rpm for acceleration and +0.10 rpm for deceleration on the Phase 2.1 grid. The 10× gap traced to cold-start stochasticity: acceleration from rest catches the motor cold, with stochastic friction breakaway, whereas deceleration always begins from a warm, settled state. The gap-fill session confirmed this falsifiable prediction directly — with a warm motor, acceleration excess collapsed to −0.05 rpm (Chapter 5).

**Session discipline is a methodological result in its own right.** Re-running the Phase 2.1 conditions two weeks later revealed structured drift — a cold-start warm-up transient, a persistent low-speed deceleration slowdown, and a persistent ≈20 % reverse high-PWM speed-up. The practical consequence is firm: calibration does not transfer across sessions for deceleration, so any later work must recalibrate in situ rather than reuse stored parameters.

## Limitations

The static map rests on a single sweep (no run02/run03), supported by a two-point spot-check and the implicit cross-validation of the step-response endpoints rather than by full repeat sweeps. The dynamic tables are a two-session composite, honestly labelled, because the bathtub and target-dependence pictures require both sessions. The FOPDT fits are *effective* at the operating-point extremes and for coast-to-rest decel, where the true behaviour is friction-dominated and not first-order, and the fitted dead time is consequently an effective parameter rather than a physical latency. Validation is interpolation within the calibration grid only; it tests neither extrapolation nor — given the documented drift — uncorrected cross-session prediction. One condition, reverse 240→100, is irreducibly noisy through the deadzone.

## Future work

The thesis defers its culminating step — closed-loop validation — for which Chapter 6 gives a concrete plan: a multi-transition simulator extracted into a reusable module, a PID firmware variant with deadzone feedforward, a global-LTI baseline to beat, and a self-contained session that calibrates in situ before comparing cascade-aware against baseline control. Independent open-loop refinements remain available: a friction-explicit "Model D" (Coulomb/Stribeck) for the deadzone and coast regimes, a higher-order dynamic block near full drive, extension of the operating grid (below breakaway, to PWM = 255, and to other deceleration start points), an instrumented study of the unexplained reverse-τ deflation, and routine ambient/driver temperature logging.

## Closing

The open-loop system identification is complete and validated within its calibration grid. The contribution is a cascade model whose structure is earned from the data — asymmetry and drift isolated to the driver, region- and operating-point-dependent dynamics in the motor — together with a validation that not only quantified predictive error but exposed and then confirmed a cold-start mechanism, and a clear methodological lesson about in-session calibration. What remains is to close the loop and show the model earns its complexity in control; the groundwork for that demonstration is now fully in place.

---

### Sources
Chapters 2–6 and their underlying processed CSVs · status-doc §4 (final model state), §5 (limitations), §6 (future work) · `thesis_notes/log.md` (full session narrative).
