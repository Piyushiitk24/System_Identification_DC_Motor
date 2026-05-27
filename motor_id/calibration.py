"""On-session laptop refit: FOPDT fits for calibration trials, then build
ModelA and ModelC from this session's data.

Trial name conventions (firmware-emitted):
  step_up_<dir>_<pwm>_run<NN>            — accel
  step_down_<dir>_240to<target>_run<NN>  — decel
  warmup_*                               — skipped
  drift_step_up_<dir>_<pwm>_run<NN>      — drift check (used separately)

The fitting logic mirrors notebooks/03_step_responses.ipynb and 05_gap_fill.ipynb
(heuristic init then scipy.optimize.curve_fit under physical bounds).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


DIR_SIGN = {"F": 1, "R": -1, "N": 0}

ACCEL_RE = re.compile(r"^step_up_(fwd|rev)_(\d+)_run(\d+)$")
DECEL_RE = re.compile(r"^step_down_(fwd|rev)_240to(\d+)_run(\d+)$")
DRIFT_RE = re.compile(r"^drift_step_up_(fwd|rev)_(\d+)_run(\d+)$")


# ---------- FOPDT model functions ----------

def _fopdt_rise(t_ms, t_step_ms, K_ss, Td, tau):
    elapsed = (t_ms - t_step_ms) - Td
    inside = elapsed >= 0
    y = np.zeros_like(t_ms, dtype=float)
    y[inside] = K_ss * (1.0 - np.exp(-elapsed[inside] / tau))
    return y


def _fopdt_decay(t_ms, t_step_ms, y_init, y_final, Td, tau):
    elapsed = (t_ms - t_step_ms) - Td
    inside = elapsed >= 0
    y = np.full_like(t_ms, y_init, dtype=float)
    y[inside] = y_final + (y_init - y_final) * np.exp(-elapsed[inside] / tau)
    return y


# ---------- Fit one trial ----------

def fit_accel_trial(df: pd.DataFrame, direction: str, pwm: int) -> dict:
    """Fit accel FOPDT to a single trial. df must have t_ms and rpm columns."""
    t = df["t_ms"].to_numpy(dtype=float)
    rpm = df["rpm"].to_numpy(dtype=float)
    # step occurs at pre_step_ms=500 (firmware Trial.pre_step_ms for accel)
    t_step_ms = 500.0
    sign = 1.0 if direction == "fwd" else -1.0
    # heuristic: K_ss ~= mean of last 500 ms
    mask_end = t >= (t[-1] - 500.0)
    K0 = float(np.mean(rpm[mask_end]))
    # tau heuristic: 63.2% rise time
    target = 0.632 * K0
    rise_mask = t >= t_step_ms
    t_rise = t[rise_mask]; y_rise = rpm[rise_mask]
    above = (y_rise / K0 if K0 != 0 else y_rise) >= 0.632 if sign > 0 else \
            (y_rise / K0 if K0 != 0 else y_rise) >= 0.632
    if np.any(above):
        tau0 = float(t_rise[np.argmax(above)] - t_step_ms)
    else:
        tau0 = 100.0
    if tau0 <= 0: tau0 = 100.0
    Td0 = 10.0
    # bounds
    if sign > 0:
        K_lo, K_hi = 0.0, 2.0 * max(abs(K0), 1.0)
    else:
        K_lo, K_hi = -2.0 * max(abs(K0), 1.0), 0.0
    p0 = [K0, Td0, max(tau0, 20.0)]
    bounds = ([K_lo, 0.0, 10.0], [K_hi, 200.0, 1000.0])

    def model(t_arr, K_ss, Td, tau):
        return _fopdt_rise(t_arr, t_step_ms, K_ss, Td, tau)

    try:
        popt, _ = curve_fit(model, t, rpm, p0=p0, bounds=bounds, maxfev=5000)
        K_ss, Td, tau = popt
        fit_ok = True
    except Exception:
        K_ss, Td, tau = K0, Td0, max(tau0, 20.0)
        fit_ok = False
    # residuals
    pred = model(t, K_ss, Td, tau)
    t_rise_end = t_step_ms + 5 * tau
    mask_rise = (t >= t_step_ms) & (t < t_rise_end)
    mask_total = t >= t_step_ms
    rms_rise = float(np.sqrt(np.mean((rpm[mask_rise] - pred[mask_rise]) ** 2))) if mask_rise.any() else float("nan")
    rms_total = float(np.sqrt(np.mean((rpm[mask_total] - pred[mask_total]) ** 2))) if mask_total.any() else float("nan")
    return dict(K_ss=float(K_ss), Td_ms=float(Td), tau_ms=float(tau),
                rms_rise=rms_rise, rms_total=rms_total, fit_ok=fit_ok)


def fit_decel_trial(df: pd.DataFrame, direction: str, target_pwm: int) -> dict:
    """Fit decel FOPDT to a single trial."""
    t = df["t_ms"].to_numpy(dtype=float)
    rpm = df["rpm"].to_numpy(dtype=float)
    t_step_ms = 3000.0  # firmware decel pre_step_ms
    # y_init: mean rpm during pre-step (200..2900 ms)
    mask_pre = (t >= 200) & (t < 2900)
    y_init0 = float(np.mean(rpm[mask_pre])) if mask_pre.any() else float(rpm[0])
    # y_final: mean rpm of last 500 ms
    mask_end = t >= (t[-1] - 500.0)
    y_final0 = float(np.mean(rpm[mask_end])) if mask_end.any() else 0.0
    tau0 = 200.0
    Td0 = 20.0
    sign = 1.0 if direction == "fwd" else -1.0
    if sign > 0:
        yi_lo, yi_hi = 0.0, 400.0
        yf_lo, yf_hi = -50.0, 400.0
    else:
        yi_lo, yi_hi = -400.0, 0.0
        yf_lo, yf_hi = -400.0, 50.0
    p0 = [y_init0, y_final0, Td0, tau0]
    bounds = ([yi_lo, yf_lo, 0.0, 10.0],
              [yi_hi, yf_hi, 200.0, 1000.0])

    def model(t_arr, y_init, y_final, Td, tau):
        return _fopdt_decay(t_arr, t_step_ms, y_init, y_final, Td, tau)

    try:
        popt, _ = curve_fit(model, t, rpm, p0=p0, bounds=bounds, maxfev=5000)
        y_init, y_final, Td, tau = popt
        fit_ok = True
    except Exception:
        y_init, y_final, Td, tau = y_init0, y_final0, Td0, tau0
        fit_ok = False
    pred = model(t, y_init, y_final, Td, tau)
    mask_fit = t >= (t_step_ms + 2000)
    rms_decel = float(np.sqrt(np.mean((rpm[mask_fit] - pred[mask_fit]) ** 2))) if mask_fit.any() else float("nan")
    mask_total = t >= t_step_ms
    rms_total = float(np.sqrt(np.mean((rpm[mask_total] - pred[mask_total]) ** 2))) if mask_total.any() else float("nan")
    return dict(y_init=float(y_init), y_final=float(y_final),
                Td_ms=float(Td), tau_ms=float(tau),
                rms_decel=rms_decel, rms_total=rms_total, fit_ok=fit_ok)


# ---------- Fit all trials in a directory of CSVs ----------

def load_calib_trials(csv_dir: Path) -> dict:
    """Load every CSV in csv_dir. Returns {'accel': df, 'decel': df, 'drift': df}.

    Each row is one trial: trial_name, direction, pwm or target_pwm, run, plus
    the fitted parameters. Trials are signed in the same convention as raw
    files (`dir` column: F/R/N -> {+1, -1, 0}); we apply DIR_SIGN before fitting.
    """
    accel_rows, decel_rows, drift_rows = [], [], []
    for csv_path in sorted(csv_dir.glob("*.csv")):
        name = csv_path.stem
        if name.startswith("warmup_"):
            continue
        df = pd.read_csv(csv_path)
        # signed rpm: csv 'rpm' carries finite-difference sign already
        # apply DIR_SIGN to pwm_cmd for consistency
        if "dir" in df.columns:
            df["dir_sign"] = df["dir"].map(DIR_SIGN).fillna(0).astype(int)
        m = ACCEL_RE.match(name)
        if m:
            direction, pwm, run = m.group(1), int(m.group(2)), int(m.group(3))
            fit = fit_accel_trial(df, direction, pwm)
            accel_rows.append({"trial": name, "direction": direction, "pwm": pwm,
                               "run": run, **fit})
            continue
        m = DRIFT_RE.match(name)
        if m:
            direction, pwm, run = m.group(1), int(m.group(2)), int(m.group(3))
            fit = fit_accel_trial(df, direction, pwm)
            drift_rows.append({"trial": name, "direction": direction, "pwm": pwm,
                               "run": run, **fit})
            continue
        m = DECEL_RE.match(name)
        if m:
            direction, target, run = m.group(1), int(m.group(2)), int(m.group(3))
            fit = fit_decel_trial(df, direction, target)
            decel_rows.append({"trial": name, "direction": direction,
                               "start_pwm": 240, "target_pwm": target,
                               "run": run, **fit})
            continue
        # other trial names (unknown) ignored
    return {
        "accel": pd.DataFrame(accel_rows),
        "decel": pd.DataFrame(decel_rows),
        "drift": pd.DataFrame(drift_rows),
    }


# ---------- Build session ModelA and ModelC from fits ----------

def build_session_model_C(fits: dict) -> dict:
    """Aggregate per-condition means and return a Model C JSON dict matching
    models/model_C.json's shape (accel_conditions + decel_conditions).
    """
    accel = fits["accel"][fits["accel"].fit_ok]
    decel = fits["decel"][fits["decel"].fit_ok]
    accel_conditions = []
    for (d, p), grp in accel.groupby(["direction", "pwm"]):
        accel_conditions.append({
            "direction": d,
            "pwm": int(p),
            "K_ss": float(grp.K_ss.mean()),
            "tau_ms": float(grp.tau_ms.mean()),
            "Td_ms": float(grp.Td_ms.mean()),
            "n_runs": int(len(grp)),
        })
    decel_conditions = []
    for (d, sp, tp), grp in decel.groupby(["direction", "start_pwm", "target_pwm"]):
        decel_conditions.append({
            "direction": d,
            "start_pwm": int(sp),
            "target_pwm": int(tp),
            "y_init": float(grp.y_init.mean()),
            "y_final": float(grp.y_final.mean()),
            "tau_ms": float(grp.tau_ms.mean()),
            "Td_ms": float(grp.Td_ms.mean()),
            "n_runs": int(len(grp)),
        })
    return {
        "name": "C_session",
        "description": "Session-fresh Model C (cascade), fitted from on-bench calibration",
        "accel_conditions": accel_conditions,
        "decel_conditions": decel_conditions,
    }


def build_session_model_A(fits: dict) -> dict:
    """Fit a global linear A model to the same trials Model C used.

    K_A: slope of K_ss vs PWM (signed), pooled across direction (single global gain
         is the whole point of A).
    tau, Td: trial-weighted means across all accel trials.
    """
    accel = fits["accel"][fits["accel"].fit_ok].copy()
    # signed K_ss already; pwm signed via direction
    accel["pwm_signed"] = accel["pwm"] * accel["direction"].map({"fwd": 1, "rev": -1})
    accel["K_ss_signed"] = accel["K_ss"]
    pwm_arr = accel["pwm_signed"].to_numpy(dtype=float)
    Kss_arr = accel["K_ss_signed"].to_numpy(dtype=float)
    # least-squares through origin: K_A = sum(pwm*K_ss) / sum(pwm^2)
    K_A = float(np.sum(pwm_arr * Kss_arr) / np.sum(pwm_arr ** 2))
    tau = float(accel["tau_ms"].mean())
    Td = float(accel["Td_ms"].mean())
    return {
        "name": "A_session",
        "description": "Session-fresh Model A (single global LTI), no static block",
        "K_A_rpm_per_pwm": K_A,
        "tau_ms": tau,
        "Td_ms": Td,
        "n_trials": int(len(accel)),
    }


def save_session_models(out_dir: Path, today: str,
                        model_C_dict: dict, model_A_dict: dict,
                        fits: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    calib_path = out_dir / f"calibration_{today}.json"
    calib_payload = {
        "date": today,
        "model_C": model_C_dict,
        "model_A": model_A_dict,
        "n_accel_trials_used": int(fits["accel"].fit_ok.sum()),
        "n_decel_trials_used": int(fits["decel"].fit_ok.sum()),
    }
    calib_path.write_text(json.dumps(calib_payload, indent=2))
    return calib_path, calib_path  # second return reserved for future split
