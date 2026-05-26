"""Cascade-model simulator: plant classes and open/closed-loop drivers.

Model C is implemented operationally in PWM -> RPM form, indexed by direction x
region x operating point. The physical PWM -> V_motor -> RPM decomposition is
retained as an interpretive result (Ch3); the simulator does not evaluate it.

Two plant classes:
  ModelC — direction-specific FOPDT family, region (accel/decel) selected per
           sample from sign((rpm_ss(pwm) - rpm) * sign(rpm_ss(pwm))), with tau
           interpolated linearly over the calibrated PWM grid (accel) or
           selected piecewise over decel target levels.
  ModelA — single global linear gain (K_A * pwm), single tau, single Td.

Two open-loop drivers:
  simulate_open_loop_single_transition — bit-compatible replica of the notebook
       simulator (regression target for Stage 0).
  simulate_open_loop — multi-transition, sample-by-sample, via plant.step().

One closed-loop driver:
  simulate_closed_loop — runs a controller against a plant at fixed dt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np


# ----------------------------------------------------------------------------
# ModelC: cascade plant
# ----------------------------------------------------------------------------

@dataclass
class ModelC:
    """Cascade plant, operationally PWM->RPM.

    accel_conditions: list of dicts {direction, pwm, K_ss, tau_ms, Td_ms}
    decel_conditions: list of dicts {direction, start_pwm, target_pwm, y_init,
                                     y_final, tau_ms, Td_ms}
    deadzone: dict per direction {breakaway_pwm, dropout_pwm} (optional; defaults
              fall back to constants from Ch3 §3.7).
    """

    accel_conditions: list[dict]
    decel_conditions: list[dict]
    deadzone: dict = field(default_factory=lambda: {
        "fwd": {"breakaway_pwm": 154, "dropout_pwm": 114},
        "rev": {"breakaway_pwm": 144, "dropout_pwm": 112},
    })

    # ---- static block (PWM -> steady-state RPM) ----

    def _accel_grid(self, direction: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        rows = [c for c in self.accel_conditions if c["direction"] == direction]
        rows = sorted(rows, key=lambda c: c["pwm"])
        pwm = np.array([c["pwm"] for c in rows], dtype=float)
        Kss = np.array([c["K_ss"] for c in rows], dtype=float)
        tau = np.array([c["tau_ms"] for c in rows], dtype=float)
        Td = np.array([c["Td_ms"] for c in rows], dtype=float)
        return pwm, Kss, tau, Td

    def static_rpm(self, pwm_signed: float) -> float:
        """Steady-state RPM at the given signed PWM; 0 inside the deadzone."""
        if pwm_signed == 0:
            return 0.0
        direction = "fwd" if pwm_signed > 0 else "rev"
        breakaway = self.deadzone[direction]["breakaway_pwm"]
        mag = abs(pwm_signed)
        if mag < breakaway:
            # below breakaway, the motor does not sustain motion from rest;
            # for steady-state map we return 0 (dropout edge handling lives in
            # the controller's FF lookup, not here).
            return 0.0
        pwm_grid, Kss_grid, _, _ = self._accel_grid(direction)
        # K_ss is signed in the grid; magnitude grows with PWM.
        return float(np.interp(mag, pwm_grid, Kss_grid))

    def inverse_static_pwm(self, rpm_target: float) -> float:
        """PWM (signed) needed to achieve rpm_target at steady state."""
        if rpm_target == 0:
            return 0.0
        direction = "fwd" if rpm_target > 0 else "rev"
        breakaway = self.deadzone[direction]["breakaway_pwm"]
        pwm_grid, Kss_grid, _, _ = self._accel_grid(direction)
        # K_ss is monotone with PWM within direction.
        mag_target = abs(rpm_target)
        Kss_mag = np.abs(Kss_grid)
        # find PWM by inverse interpolation on |K_ss|
        if mag_target <= Kss_mag[0]:
            # below the lowest calibrated steady speed -> use breakaway PWM
            # (cannot sustain lower steady speeds; this is the FF "saturate at
            # breakaway" rule).
            pwm_mag = float(breakaway)
        elif mag_target >= Kss_mag[-1]:
            pwm_mag = float(pwm_grid[-1])
        else:
            pwm_mag = float(np.interp(mag_target, Kss_mag, pwm_grid))
        return pwm_mag if rpm_target > 0 else -pwm_mag

    # ---- dynamic block (tau, Td) ----

    def tau_accel(self, direction: str, pwm_mag: float) -> float:
        pwm_grid, _, tau_grid, _ = self._accel_grid(direction)
        return float(np.interp(np.clip(pwm_mag, pwm_grid[0], pwm_grid[-1]),
                               pwm_grid, tau_grid))

    def Td_accel(self, direction: str, pwm_mag: float) -> float:
        pwm_grid, _, _, Td_grid = self._accel_grid(direction)
        return float(np.interp(np.clip(pwm_mag, pwm_grid[0], pwm_grid[-1]),
                               pwm_grid, Td_grid))

    def _decel_grid(self, direction: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rows = [c for c in self.decel_conditions if c["direction"] == direction]
        rows = sorted(rows, key=lambda c: abs(c["target_pwm"]))
        target = np.array([abs(c["target_pwm"]) for c in rows], dtype=float)
        tau = np.array([c["tau_ms"] for c in rows], dtype=float)
        Td = np.array([c["Td_ms"] for c in rows], dtype=float)
        return target, tau, Td

    def tau_decel(self, direction: str, target_pwm_mag: float) -> float:
        target_grid, tau_grid, _ = self._decel_grid(direction)
        return float(np.interp(np.clip(target_pwm_mag, target_grid[0], target_grid[-1]),
                               target_grid, tau_grid))

    def Td_decel(self, direction: str, target_pwm_mag: float) -> float:
        target_grid, _, Td_grid = self._decel_grid(direction)
        return float(np.interp(np.clip(target_pwm_mag, target_grid[0], target_grid[-1]),
                               target_grid, Td_grid))

    # ---- one-sample plant step (for multi-transition + closed loop) ----

    def step(self, rpm: float, pwm_cmd: float, dt_ms: float) -> float:
        """Advance the plant one sample.

        Region selection: accel if |rpm_ss(pwm)| > |rpm| and same sign;
        decel otherwise. Tau looked up from the appropriate grid.
        Dead time is handled at the simulator driver layer (input shift
        register), not here — this step assumes the dead-time-delayed input.
        """
        rpm_ss = self.static_rpm(pwm_cmd)
        direction = "fwd" if (rpm_ss + rpm) >= 0 else "rev"  # use composite sign
        if pwm_cmd == 0 and rpm == 0:
            return 0.0
        # region: accel when moving the speed *away from zero* toward rpm_ss
        # with the same sign; decel otherwise (includes coast to zero and
        # cross-zero situations).
        same_sign = (rpm_ss > 0 and rpm >= 0) or (rpm_ss < 0 and rpm <= 0) or rpm == 0
        accel = same_sign and abs(rpm_ss) > abs(rpm)
        if accel:
            direction = "fwd" if rpm_ss > 0 else "rev"
            tau = self.tau_accel(direction, abs(pwm_cmd))
        else:
            # decel toward rpm_ss; use direction of the *current* rotation
            # (which is what physically determines friction sign), falling
            # back to direction of rpm_ss when rpm==0.
            direction = "fwd" if (rpm > 0 or (rpm == 0 and rpm_ss > 0)) else "rev"
            tau = self.tau_decel(direction, abs(pwm_cmd))
        # exact one-step solution of first-order: y[k+1] = y_ss + (y[k]-y_ss)*exp(-dt/tau)
        if tau <= 0:
            return rpm_ss
        alpha = np.exp(-dt_ms / tau)
        return rpm_ss + (rpm - rpm_ss) * alpha


# ----------------------------------------------------------------------------
# ModelA: naive global LTI baseline
# ----------------------------------------------------------------------------

@dataclass
class ModelA:
    K_A_rpm_per_pwm: float
    tau_ms: float
    Td_ms: float

    def static_rpm(self, pwm_signed: float) -> float:
        return self.K_A_rpm_per_pwm * pwm_signed

    def inverse_static_pwm(self, rpm_target: float) -> float:
        if self.K_A_rpm_per_pwm == 0:
            return 0.0
        return rpm_target / self.K_A_rpm_per_pwm

    def step(self, rpm: float, pwm_cmd: float, dt_ms: float) -> float:
        rpm_ss = self.static_rpm(pwm_cmd)
        if self.tau_ms <= 0:
            return rpm_ss
        alpha = np.exp(-dt_ms / self.tau_ms)
        return rpm_ss + (rpm - rpm_ss) * alpha


# ----------------------------------------------------------------------------
# Open-loop single-transition simulator: bit-compatible regression target
# ----------------------------------------------------------------------------

def simulate_open_loop_single_transition(
    pwm_cmd: Sequence[float],
    dt_ms: float = 10.0,
    return_meta: bool = False,
    override_params: Optional[dict] = None,
):
    """Exact replica of the notebook simulator (notebooks/04 cell 6b,
    notebooks/05 cell 7). Single transition only; takes either accel
    (K_ss, Td, tau) or decel (y_init, y_final, Td, tau) override_params.

    This function is the regression target for the Stage 0 gate.
    """
    assert override_params is not None, "Override params required (matches notebook)."
    pwm_cmd = np.asarray(pwm_cmd, dtype=float)
    n = len(pwm_cmd)
    transitions = np.where(np.abs(np.diff(np.abs(pwm_cmd))) > 0.5)[0]
    if len(transitions) == 0:
        return (np.zeros(n), {"regime": "flat"}) if return_meta else np.zeros(n)
    if len(transitions) > 1:
        raise NotImplementedError(f"single-transition only; got {len(transitions)}")
    t_step = int(transitions[0] + 1)
    pwm_before, pwm_after = pwm_cmd[t_step - 1], pwm_cmd[t_step]
    abs_before, abs_after = int(round(abs(pwm_before))), int(round(abs(pwm_after)))
    if abs_after > abs_before:
        regime = "accel"
        direction = "fwd" if pwm_after > 0 else "rev"
        p = {k: float(override_params[k]) for k in ("K_ss", "Td", "tau")}
        y_init, y_final = 0.0, p["K_ss"]
    else:
        regime = "decel"
        direction = "fwd" if pwm_before > 0 else "rev"
        p = {k: float(override_params[k]) for k in ("y_init", "y_final", "Td", "tau")}
        y_init, y_final = p["y_init"], p["y_final"]
    Td, tau = p["Td"], p["tau"]
    rpm = np.empty(n)
    rpm[:t_step] = 0.0 if regime == "accel" else y_init
    for k in range(t_step, n):
        elapsed_ms = (k - t_step) * dt_ms - Td
        rpm[k] = (y_init if regime == "decel" else 0.0) if elapsed_ms < 0 else \
                 y_final + (y_init - y_final) * np.exp(-elapsed_ms / tau)
    meta = dict(regime=regime, direction=direction, pwm_before=abs_before,
                pwm_after=abs_after, K_ss=y_final, y_init=y_init, Td=Td, tau=tau,
                t_step=t_step)
    return (rpm, meta) if return_meta else rpm


# ----------------------------------------------------------------------------
# Multi-transition open-loop simulator (uses plant.step())
# ----------------------------------------------------------------------------

def simulate_open_loop(
    pwm_cmd: Sequence[float],
    plant,
    dt_ms: float = 10.0,
    init_rpm: float = 0.0,
    deadtime_ms: float = 0.0,
) -> dict:
    """Sample-by-sample open-loop simulation.

    deadtime_ms applies a uniform input delay (shift register). For closed-loop
    work the controller picks its own region; here we let the plant decide.
    """
    pwm_cmd = np.asarray(pwm_cmd, dtype=float)
    n = len(pwm_cmd)
    delay_samples = int(round(deadtime_ms / dt_ms))
    rpm = np.empty(n)
    pwm_eff = np.empty(n)
    rpm_k = init_rpm
    buf = [0.0] * max(delay_samples, 0)
    for k in range(n):
        if delay_samples > 0:
            buf.append(pwm_cmd[k])
            u_k = buf.pop(0)
        else:
            u_k = pwm_cmd[k]
        pwm_eff[k] = u_k
        rpm_k = plant.step(rpm_k, u_k, dt_ms)
        rpm[k] = rpm_k
    return {"rpm": rpm, "pwm_effective": pwm_eff}


# ----------------------------------------------------------------------------
# Closed-loop simulator
# ----------------------------------------------------------------------------

def simulate_closed_loop(
    t_ms: Sequence[float],
    ref_rpm: Sequence[float],
    controller,
    plant,
    dt_ms: float = 10.0,
    init_rpm: float = 0.0,
    deadtime_ms: float = 0.0,
    rpm_quantum: float = 0.0,
    pwm_clip: float = 255.0,
) -> dict:
    """Run a closed-loop simulation.

    rpm_quantum > 0 simulates the encoder/finite-difference RPM quantisation
    (≈ 2.5 rpm at 10 ms, 600 PPR, 4x decode — see thesis §2.5). Set to 0 for
    noise-free runs.
    """
    t_ms = np.asarray(t_ms, dtype=float)
    ref_rpm = np.asarray(ref_rpm, dtype=float)
    n = len(t_ms)
    assert len(ref_rpm) == n, "ref length mismatch"

    delay_samples = int(round(deadtime_ms / dt_ms))
    pwm_buf = [0.0] * max(delay_samples, 0)

    rpm = np.empty(n)
    pwm_cmd = np.empty(n)
    pwm_eff = np.empty(n)
    meas = np.empty(n)
    controller.reset()
    rpm_k = init_rpm

    for k in range(n):
        # measurement (with optional quantisation)
        if rpm_quantum > 0:
            meas_k = rpm_quantum * np.round(rpm_k / rpm_quantum)
        else:
            meas_k = rpm_k
        meas[k] = meas_k

        # controller computes PWM command
        u_cmd = controller(t_ms[k], ref_rpm[k], meas_k)
        u_cmd = float(np.clip(u_cmd, -pwm_clip, pwm_clip))
        pwm_cmd[k] = u_cmd

        # apply input dead time
        if delay_samples > 0:
            pwm_buf.append(u_cmd)
            u_eff = pwm_buf.pop(0)
        else:
            u_eff = u_cmd
        pwm_eff[k] = u_eff

        # advance plant
        rpm_k = plant.step(rpm_k, u_eff, dt_ms)
        rpm[k] = rpm_k

    return {
        "t_ms": t_ms,
        "ref_rpm": ref_rpm,
        "rpm": rpm,
        "rpm_measured": meas,
        "pwm_cmd": pwm_cmd,
        "pwm_effective": pwm_eff,
    }
