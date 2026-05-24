# Chapter 5 — Validation

> **Draft status:** first full pass, 2026-05-21. Markdown; converts to LaTeX mechanically. All values trace to `data/processed/phase21_loocv_summary.csv` and `phase2gapfill_loocv_summary_combined.csv` (and the per-trial LOOCV CSVs), status-doc §4.4–§5, figures `12`–`15`, `19`. Covers Phase 2.2 (LOOCV on the Phase 2.1 grid) and the gap-fill within-condition LOOCV.

## 5.1 Objective

Chapter 4 fitted Model C condition by condition. This chapter asks whether those parameters **predict** rather than merely describe: given the calibrated FOPDT for an operating point, how accurately does the model reproduce a trial it was not fitted to? Three questions are separated — how well the model generalises between repeats of the same condition (within-grid), whether that generalisation depends on the acceleration/deceleration regime, and how far the parameters transfer to a *different bench session*. The answers quantify the model's predictive error and, importantly, expose a cold-start effect that reframes one of the Phase 2.1 conclusions.

## 5.2 Method

The validation plan originally called for a held-out dataset under `data/raw/_sealed/`. An inventory probe established that **this directory never existed** — it was an aspiration in an early handover, not a real artifact — so validation pivoted to **leave-one-out cross-validation (LOOCV)**, which needs no separate hold-out and uses the existing trials honestly.

For each trial, the model is rebuilt from the *other* runs at the same condition and used to predict the held-out trial: the FOPDT parameters are taken as the mean of the remaining runs (two others in Phase 2.1, four in the gap-fill accel set), injected into the single-transition Model C simulator, and scored against the measured trace. Scoring is window-matched to the original fits so the comparison is like-for-like: the rise window for acceleration, the post-2000 ms fit window for deceleration. The headline metric is the **excess**,

$$\text{excess} = \overline{\text{RMSE}}_\text{LOOCV} - \text{in-sample fit floor},$$

i.e. how much worse the model predicts a held-out trial than it fit the trials it was trained on. An excess near zero means the parameters generalise; a large positive excess means run-to-run variability the per-condition mean cannot capture. The simulator was verified to reproduce the in-sample fit bit-for-bit when given a condition's own parameters, so any excess is genuine generalisation error, not a simulator artefact.

## 5.3 Within-grid validation (Phase 2.2)

Applying LOOCV across the thirty Phase 2.1 trials gives:

| Region | Mean excess (rpm) | std | n conditions | Range |
|---|---:|---:|---:|---|
| Acceleration | **+1.06** | 0.80 | 6 | −0.29 (rev 200) … +1.97 (fwd 160) |
| Deceleration | **+0.10** | 0.10 | 4 | +0.01 … +0.23 |

*Table 5.1 — Phase 2.2 LOOCV excess by regime (figure `12`; 30-panel overlay in figure `13`).*

Two results stand out. The model generalises well in absolute terms — even the worst accel condition predicts held-out trials to within ≈2 rpm of its own fit floor, against an RPM signal whose quantisation alone is 2.5 rpm (Section 2.5). And **deceleration is roughly ten times more reproducible than acceleration** (+0.10 vs +1.06 rpm excess). The worst single condition is acceleration at PWM = 160 forward (+1.97 rpm), the friction-corrupted operating point just above breakaway; the best is reverse PWM = 200, which actually predicts marginally *better* than its own noisy fit — a sign of LOOCV robustness rather than a model gain.

## 5.4 The acceleration/deceleration reproducibility asymmetry

The 10× gap in Table 5.1 is not predicted by the FOPDT structure and demands a physical explanation. The hypothesis is **cold-start stochasticity**. An acceleration trial starts the motor from rest, catching it cold: static-friction breakaway is stochastic (Section 3.7) and the rotor pole alignment at the instant of release is uncontrolled, so the early rise varies run to run in ways a mean parameter set cannot track. A deceleration trial, by contrast, begins only after the motor has held PWM = 240 for three seconds — by then it is thermally settled, its friction is stable, and pole position has been randomised over many revolutions. Decel therefore always sees a "warm, settled" machine and transfers cleanly between runs; accel from rest does not. This was invisible in the Phase 2.1 per-condition fits, which average over runs, and is exposed only by the leave-one-out procedure.

## 5.5 Warm-motor confirmation (gap-fill)

The cold-start hypothesis makes a falsifiable prediction: with a **warm** motor, acceleration reproducibility should collapse to the deceleration level. The gap-fill session tests exactly this — its new accel conditions were run five times each on an already-warm machine. The within-condition LOOCV gives:

| Phase / region | Mean excess (rpm) | n cond | Notable |
|---|---:|---:|---|
| Phase 2.2 accel (cold, from rest) | +1.06 | 6 | worst fwd 160 +1.97 |
| Gap-fill accel (warm, n=5) | **−0.05** | 4 | range −0.37 … +0.28 |
| Phase 2.2 decel | +0.10 | 4 | — |
| Gap-fill decel | +0.45 | 6 | worst rev 240→100 +1.06 |

*Table 5.2 — Combined LOOCV across both sessions (figure `19`; full 20-condition table in status-doc §4.4).*

The prediction holds: warm-motor acceleration excess collapses from +1.06 to **−0.05 rpm**, statistically indistinguishable from the deceleration floor. The Phase 2.2 accel penalty was therefore **cold-start stochasticity, not a steady-state property of acceleration** — a refinement, not a contradiction, of the Phase 2.1 conclusion. Deceleration excess stays low in both sessions (+0.10, +0.45); the slightly higher gap-fill figure is driven almost entirely by one condition, reverse 240→100 (+1.06 rpm), where short PWM-on pulses during freewheel through the deadzone interact stochastically with the brush contact pattern — the noisiest condition in the entire study (Section 4.4; status-doc §5).

## 5.6 Cross-session generalization

The eight piggyback trials — Phase 2.1 conditions re-run during the gap-fill session, two weeks later — test the hardest case: do the calibrated parameters transfer across sessions? They do not transfer cleanly, and the failure is **structured**, not random (figures `14`, `15`):

- **Cold-start transient.** The first forward accel trials of the session show τ inflated 30–40 % (e.g. fwd 200 run 1: τ = 131 ms vs the Phase 2.1 mean of 95 ms), recovering within the first ≈30 s as the motor warms — the same thermal effect as Section 5.4, now visible at session scale.
- **Persistent low-speed decel slowdown.** Decel through the deadzone (240→100, 240→180) runs ≈2× slower than Phase 2.1 interpolation would predict, a persistent shift attributed to lubricant settling over the idle period.
- **Persistent reverse high-PWM speed-up.** Reverse τ at PWM = 240 sits ≈20 % below its Phase 2.1 value across all gap-fill reverse high-PWM trials — stable, not a warm-up transient, and mechanistically unexplained.

The operative conclusion is that **Phase 2.1 parameters must not be treated as ground truth for a later session**: the decel drift in particular is larger than the within-session predictive error. Within-session validation passes comfortably; cross-session validation does not, for deceleration. This directly shapes any future closed-loop protocol, which must begin with a fresh in-session calibration block rather than reuse these tables.

## 5.7 Limitations of the validation

Three boundaries should be stated plainly. (i) LOOCV tests **interpolation within the calibration grid** only — PWM ∈ {160…240}, decel targets ∈ {0, 100, 160, 180, 220}; it does not test extrapolation beyond it. (ii) There is **no truly held-out dataset**; the `_sealed/` set never existed, and LOOCV reuses calibration trials by construction. (iii) Cross-session generalisation is characterised (Section 5.6) but not *validated* — the drift is measured, not corrected, so the model is not claimed to predict a future cold session without recalibration. None of these undermine the within-session result; they bound its scope.

## 5.8 Summary

Model C predicts held-out trials within its calibration grid to ≈0.1–1 rpm of its own fit floor, on an RPM signal whose quantisation is 2.5 rpm — a strong within-session result. The leave-one-out procedure surfaced a cold-start effect: acceleration from rest is ≈10× less reproducible than deceleration, a gap that collapses to zero once the motor is warm, confirming the effect is start-state stochasticity rather than a property of acceleration itself. Cross-session transfer is structured but imperfect — a warm-up transient, a persistent low-speed decel slowdown, and a persistent reverse high-PWM speed-up — large enough that later-session work must recalibrate in situ. If closed-loop control were undertaken on this rig, these residuals imply a steady-operation tracking floor of ≈3–5 rpm. With the static block (Chapter 3), the dynamic block (Chapter 4), and this within-grid validation, the open-loop identification is complete; closing the loop is the remaining work, deferred to future work and laid out as a concrete plan in Chapter 6.

---

### Sources for this chapter
`data/processed/phase21_loocv_summary.csv`, `phase2gapfill_loocv_summary_combined.csv`, `phase21_loocv_accel.csv` / `_decel.csv`, `phase2gapfill_loocv_accel.csv` / `_decel.csv` · `notebooks/04_validation.ipynb`, `05_gap_fill.ipynb` (LOOCV, simulator, figures 12–15, 19) · status-doc §4.4, §5 · `thesis_notes/log.md` 2026-05-07 / 2026-05-22 (LOOCV results, cold-start hypothesis, session drift).
