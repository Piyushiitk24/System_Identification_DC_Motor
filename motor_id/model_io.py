"""Model loading, IMC tuning, FF-table construction, sim safety checks.

The IMC tuning rule is the same callable for Model A (one gain set) and
Model C (four per-region gain sets at the canonical PWM=200 operating
point), so neither model gets hand-tuned and the A-vs-C comparison is fair
by construction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np

from .cascade_sim import ModelA, ModelC


# ----------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------

def load_model_C(path: str | Path) -> ModelC:
    data = json.loads(Path(path).read_text())
    return ModelC(
        accel_conditions=data["accel_conditions"],
        decel_conditions=data["decel_conditions"],
    )


def load_model_A(path: str | Path) -> ModelA:
    data = json.loads(Path(path).read_text())
    return ModelA(
        K_A_rpm_per_pwm=data["K_A_rpm_per_pwm"],
        tau_ms=data["tau_ms"],
        Td_ms=data["Td_ms"],
    )


# ----------------------------------------------------------------------------
# IMC tuning
# ----------------------------------------------------------------------------

def compute_imc_gains(K: float, tau_ms: float, Td_ms: float,
                      lambda_ms: float) -> tuple[float, float]:
    """IMC PI tuning for a FOPDT plant y = K/(tau s + 1) e^(-Td s).

    Standard PI: Kp = tau / (K * (lambda + Td)), Ti = tau -> Ki = Kp / tau.
    Units: K in rpm/PWM, tau and lambda in ms, Td in ms. Returned Kp has units
    PWM/rpm; Ki has units PWM/(rpm·s).
    """
    if K == 0:
        raise ValueError("IMC: K must be non-zero")
    tau_s = tau_ms * 1e-3
    lam_s = lambda_ms * 1e-3
    Td_s = Td_ms * 1e-3
    # IMC with closed-loop time-constant lambda:
    Kp = tau_s / (K * (lam_s + Td_s))
    Ki = Kp / tau_s
    return float(Kp), float(Ki)


def compute_baseline_gains(model_A: ModelA, lambda_ms: float) -> dict:
    Kp, Ki = compute_imc_gains(model_A.K_A_rpm_per_pwm, model_A.tau_ms,
                               model_A.Td_ms, lambda_ms)
    return {"Kp": Kp, "Ki": Ki, "lambda_ms": lambda_ms}


def compute_cascade_gains(model_C: ModelC, lambda_ms: float,
                          op_pwm: int = 200) -> dict:
    """Four PI gain sets (fwd-accel, fwd-decel, rev-accel, rev-decel).

    Computed at the canonical PWM=200 operating point per Ch4 §4.3 — the
    clean FOPDT point. K is the *local incremental* gain near op_pwm
    (drpm/dpwm) inferred from the calibrated grid.
    """
    out = {"lambda_ms": lambda_ms, "op_pwm": op_pwm}

    for direction in ("fwd", "rev"):
        # Accel: incremental gain from accel K_ss curve at op_pwm
        pwm_grid, Kss_grid, tau_grid, Td_grid = model_C._accel_grid(direction)
        if op_pwm < pwm_grid[0] or op_pwm > pwm_grid[-1]:
            raise ValueError(f"op_pwm {op_pwm} outside accel grid for {direction}")
        # local slope dK_ss/dpwm via two-point centered difference at op_pwm
        i = int(np.searchsorted(pwm_grid, op_pwm))
        if pwm_grid[i] == op_pwm:
            i_lo = max(i - 1, 0); i_hi = min(i + 1, len(pwm_grid) - 1)
        else:
            i_lo, i_hi = max(i - 1, 0), min(i, len(pwm_grid) - 1)
        dKss = (Kss_grid[i_hi] - Kss_grid[i_lo]) / (pwm_grid[i_hi] - pwm_grid[i_lo])
        # use magnitude of the incremental gain so PI sign is normalised by ref-sign
        K_local = abs(dKss)
        tau_at_op = float(np.interp(op_pwm, pwm_grid, tau_grid))
        Td_at_op = float(np.interp(op_pwm, pwm_grid, Td_grid))
        Kp_a, Ki_a = compute_imc_gains(K_local, tau_at_op, Td_at_op, lambda_ms)
        out[f"accel_{direction}"] = {"Kp": Kp_a, "Ki": Ki_a,
                                     "K_local_rpm_per_pwm": K_local,
                                     "tau_ms": tau_at_op, "Td_ms": Td_at_op}

        # Decel: use the closest decel target around op_pwm for tau/Td;
        # incremental gain reuses the accel slope (the static block is shared).
        target_grid, tau_dec, Td_dec = model_C._decel_grid(direction)
        # representative decel: 240 -> 160 (target_pwm = 160, closest to op_pwm = 200)
        # use linear interp at op_pwm clamped to the decel target grid.
        tau_dec_at_op = float(np.interp(np.clip(op_pwm, target_grid[0], target_grid[-1]),
                                        target_grid, tau_dec))
        Td_dec_at_op = float(np.interp(np.clip(op_pwm, target_grid[0], target_grid[-1]),
                                       target_grid, Td_dec))
        Kp_d, Ki_d = compute_imc_gains(K_local, tau_dec_at_op, Td_dec_at_op, lambda_ms)
        out[f"decel_{direction}"] = {"Kp": Kp_d, "Ki": Ki_d,
                                     "K_local_rpm_per_pwm": K_local,
                                     "tau_ms": tau_dec_at_op, "Td_ms": Td_dec_at_op}
    return out


# ----------------------------------------------------------------------------
# Feedforward table for firmware
# ----------------------------------------------------------------------------

def build_ff_table(model_C: ModelC,
                   rpms: Sequence[float] = (50, 80, 100, 150, 200)) -> dict:
    """Build a (rpm, pwm) lookup table per direction from the inverse static map.

    Five points per direction (default) chosen to span the deadzone edge (50/80)
    and the linear region (100/150/200). Below 50 the motor cannot sustain
    steady motion from rest, so FF saturates at breakaway PWM there — this is
    embedded in `ModelC.inverse_static_pwm`.
    """
    table = {"fwd": [], "rev": []}
    for rpm in rpms:
        rpm = float(rpm)
        pwm_fwd = model_C.inverse_static_pwm(+rpm)
        pwm_rev = model_C.inverse_static_pwm(-rpm)
        table["fwd"].append((rpm, pwm_fwd))
        table["rev"].append((rpm, abs(pwm_rev)))  # magnitude for firmware
    return table


def ff_table_to_firmware_commands(table: dict) -> list[str]:
    """Render an FF table as the serial commands the closed-loop firmware will accept.

    Format per the protocol:
      FF_FWD <n> <rpm0> <pwm0> <rpm1> <pwm1> ...
      FF_REV <n> <rpm0> <pwm0> <rpm1> <pwm1> ...
    PWM values are emitted as integers (PWM counts 0-255).
    """
    cmds = []
    for direction in ("FWD", "REV"):
        key = direction.lower()
        pairs = table[key]
        parts = [f"FF_{direction}", str(len(pairs))]
        for rpm, pwm in pairs:
            parts.append(f"{int(round(rpm))}")
            parts.append(f"{int(round(pwm))}")
        cmds.append(" ".join(parts))
    return cmds


def ff_lookup_from_table(table: dict):
    """Return a callable ff_lookup(rpm_target) -> signed PWM using piecewise-linear
    interpolation on the table (matches firmware logic).
    """
    fwd_rpms = np.array([r for r, _ in table["fwd"]], dtype=float)
    fwd_pwms = np.array([p for _, p in table["fwd"]], dtype=float)
    rev_rpms = np.array([r for r, _ in table["rev"]], dtype=float)
    # store rev pwms as magnitudes; we apply sign below.
    rev_pwms = np.array([abs(p) for _, p in table["rev"]], dtype=float)

    def lookup(rpm_target: float) -> float:
        if rpm_target == 0:
            return 0.0
        if rpm_target > 0:
            mag = rpm_target
            # saturate to endpoints of the table
            if mag <= fwd_rpms[0]:
                pwm = fwd_pwms[0]
            elif mag >= fwd_rpms[-1]:
                pwm = fwd_pwms[-1]
            else:
                pwm = float(np.interp(mag, fwd_rpms, fwd_pwms))
            return pwm
        else:
            mag = -rpm_target
            if mag <= rev_rpms[0]:
                pwm = rev_pwms[0]
            elif mag >= rev_rpms[-1]:
                pwm = rev_pwms[-1]
            else:
                pwm = float(np.interp(mag, rev_rpms, rev_pwms))
            return -pwm

    return lookup


# ----------------------------------------------------------------------------
# Safety checks on simulated closed-loop trials
# ----------------------------------------------------------------------------

def safety_check_sim(result: dict,
                     pwm_clip: float = 255.0,
                     max_saturation_frac: float = 0.20,
                     oscillation_zero_crossings_per_s: float = 8.0,
                     dt_ms: float = 10.0) -> dict:
    """Inspect a simulated closed-loop trial for the gain rejection rules:

      - time_saturated > max_saturation_frac of total
      - sustained oscillation: error zero-crossings per second exceeds threshold
        over the steady-state portion (last 30% of trial)

    Returns a dict of flags. The notebook decides whether to reject.
    """
    pwm = np.asarray(result["pwm_cmd"], dtype=float)
    rpm = np.asarray(result["rpm"], dtype=float)
    ref = np.asarray(result["ref_rpm"], dtype=float)

    n = len(pwm)
    saturated_frac = float(np.mean(np.abs(pwm) >= pwm_clip - 1e-6))

    ss_start = int(0.7 * n)
    err = ref[ss_start:] - rpm[ss_start:]
    zc = int(np.sum(np.diff(np.sign(err)) != 0))
    duration_s = (n - ss_start) * dt_ms * 1e-3
    zc_per_s = zc / max(duration_s, 1e-9)

    return {
        "saturated_frac": saturated_frac,
        "saturated_violates_20pct": saturated_frac > max_saturation_frac,
        "ss_zero_crossings_per_s": zc_per_s,
        "oscillating": zc_per_s > oscillation_zero_crossings_per_s,
    }
