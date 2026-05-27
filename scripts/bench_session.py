#!/usr/bin/env python3
"""
bench_session.py — Phase 3 Stage 2 bench orchestrator.

Single end-to-end driver for the closed-loop bench session:

  1. WARMUP — 55 s warm-up motor-on, no trial blocks recorded for analysis.
  2. CALIB  — 30 open-loop trials. Captured to per-trial CSVs.
  3. Refit  — fit fresh Model A + Model C from this session's calibration data.
  4. Freeze — compute IMC PI gains for BASE and CASC and an FF table; upload to
              firmware via GAINS_BASE, GAINS_CASC, FF_FWD, FF_REV. Persist to
              models/calibration_<DATE>.json and models/closed_loop_gains_<DATE>.json.
  5. CL     — 64 closed-loop trials: profiles P1-P4 x 2 controllers x 8 pairs.
              Pair order randomised within profile (seeded); controller order
              within pair randomised. Each trial captured to its own CSV.
  6. DRIFT  — 6 end-of-session drift-check trials.

The whole session captures to data/raw/closed_loop_<DATE>/ and writes a
session-level log under data/raw/serial_logs/<DATE>_phase3_session.log.

If anything looks wrong, Ctrl-C is always available; the script sends STOP and
exits cleanly.
"""

from __future__ import annotations

import argparse
import datetime
import json
import random
import sys
import time
from pathlib import Path

import serial

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from motor_id.calibration import (load_calib_trials, build_session_model_C,
                                  build_session_model_A, save_session_models)
from motor_id.cascade_sim import ModelC, ModelA
from motor_id.model_io import (compute_baseline_gains, compute_cascade_gains,
                                build_ff_table, ff_table_to_firmware_commands)


LAMBDA_MS = 200.0
OP_PWM    = 200
FF_RPMS   = [50, 80, 100, 150, 200]


# ----------------------------------------------------------------------------
# Serial helpers
# ----------------------------------------------------------------------------

class BenchSerial:
    def __init__(self, port: str, log_path: Path):
        self.ser = serial.Serial(port, 230400, timeout=0.05)
        self.log = open(log_path, "w")
        # let the board finish booting after a possible reset on port open
        time.sleep(2.5)
        self.drain(1.0)

    def close(self):
        try:
            self.ser.write(b"STOP\n")
            time.sleep(0.2)
            self.drain(0.3)
        finally:
            self.ser.close()
            self.log.close()

    def _write(self, text: str):
        sys.stdout.write(text); sys.stdout.flush()
        self.log.write(text); self.log.flush()

    def drain(self, seconds: float = 0.5):
        t_end = time.time() + seconds
        while time.time() < t_end:
            n = self.ser.in_waiting
            if n > 0:
                chunk = self.ser.read(n).decode("utf-8", errors="ignore")
                if chunk:
                    self._write(chunk)
            else:
                time.sleep(0.01)

    def send(self, cmd: str, post_delay: float = 0.2):
        self._write(f"\n# >>> SENT: {cmd}\n")
        self.ser.write((cmd + "\n").encode())
        self.ser.flush()
        time.sleep(post_delay)
        self.drain(0.1)

    def capture_until(self, marker: str, timeout_s: float,
                       sink_path: Path | None = None) -> str:
        """Read serial output until `marker` appears in the stream (or timeout).
        Returns the captured text. If sink_path is given, write captured text
        to that file *in addition* to the session log.
        """
        buf = []
        sink = open(sink_path, "w") if sink_path is not None else None
        t_end = time.time() + timeout_s
        try:
            while time.time() < t_end:
                n = self.ser.in_waiting
                if n > 0:
                    chunk = self.ser.read(n).decode("utf-8", errors="ignore")
                    if chunk:
                        self._write(chunk)
                        buf.append(chunk)
                        if sink is not None:
                            sink.write(chunk); sink.flush()
                        if marker in "".join(buf[-8:]):
                            return "".join(buf)
                else:
                    time.sleep(0.01)
            self._write(f"\n# >>> TIMEOUT waiting for: {marker}\n")
            return "".join(buf)
        finally:
            if sink is not None:
                sink.close()


# ----------------------------------------------------------------------------
# Log splitting
# ----------------------------------------------------------------------------

def split_log_into_csvs(log_text: str, out_dir: Path,
                         rename_map: dict | None = None) -> list[str]:
    """Split a captured chunk of serial output into per-trial CSVs.

    Each trial starts with `=== START <name> ===` and ends with `=== END ===`.
    Returns the list of trial names written.

    rename_map (optional): {trial_emitted_name: output_filename_stem}. Lets the
    orchestrator give a closed-loop trial a unique pair-id filename even though
    the firmware emits the same name (e.g., "P1_BASE") for every pair.
    """
    import re
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = r"=== START (\S+) ===\s*\n(.*?)\n=== END ==="
    matches = re.findall(pattern, log_text, re.DOTALL)
    names = []
    for name, body in matches:
        out_name = rename_map[name] if (rename_map and name in rename_map) else name
        body = body.strip() + "\n"
        (out_dir / f"{out_name}.csv").write_text(body)
        names.append(out_name)
    return names


# ----------------------------------------------------------------------------
# Main session
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbmodem101")
    parser.add_argument("--seed", type=int, default=20260527)
    parser.add_argument("--n-pairs", type=int, default=8,
                         help="Pairs per profile per controller (default 8 per pre-reg)")
    parser.add_argument("--date", default=None,
                         help="Override session date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    today = args.date or datetime.date.today().isoformat()
    rng = random.Random(args.seed)

    session_dir = ROOT / "data" / "raw" / f"closed_loop_{today}"
    calib_dir   = session_dir / "calib_trials"
    closed_dir  = session_dir / "closed_loop_trials"
    drift_dir   = session_dir / "drift_trials"
    logs_dir    = ROOT / "data" / "raw" / "serial_logs"
    for d in (session_dir, calib_dir, closed_dir, drift_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)
    session_log_path = logs_dir / f"{today}_phase3_session.log"
    print(f"Session dir: {session_dir}")
    print(f"Log: {session_log_path}")

    bs = BenchSerial(args.port, session_log_path)
    try:
        # =========================================================== WARMUP
        print("\n=== STAGE A: WARMUP (~55 s motor-on) ===")
        bs.send("WARMUP", post_delay=0.3)
        warmup_log_path = session_dir / "warmup.log"
        bs.send("GO")
        warmup_text = bs.capture_until("# === WARMUP SEQUENCE COMPLETE ===",
                                        timeout_s=120, sink_path=warmup_log_path)

        # =========================================================== CALIB
        print("\n=== STAGE B: CALIB (30 open-loop trials, ~7-8 min) ===")
        bs.send("CALIB", post_delay=0.3)
        calib_log_path = session_dir / "calib.log"
        bs.send("GO")
        calib_text = bs.capture_until("# === CALIB SEQUENCE COMPLETE ===",
                                       timeout_s=900, sink_path=calib_log_path)
        names = split_log_into_csvs(calib_text, calib_dir)
        print(f"Wrote {len(names)} calibration CSVs to {calib_dir}")

        # =========================================================== REFIT
        print("\n=== STAGE C: on-laptop refit ===")
        fits = load_calib_trials(calib_dir)
        print(f"  fit_ok accel: {int(fits['accel'].fit_ok.sum())}/{len(fits['accel'])}")
        print(f"  fit_ok decel: {int(fits['decel'].fit_ok.sum())}/{len(fits['decel'])}")
        model_C_dict = build_session_model_C(fits)
        model_A_dict = build_session_model_A(fits)
        # save
        models_dir = ROOT / "models"
        calib_path, _ = save_session_models(models_dir, today, model_C_dict, model_A_dict, fits)
        print(f"  calibration saved: {calib_path}")
        print(f"  Model A: K={model_A_dict['K_A_rpm_per_pwm']:.4f} rpm/PWM, tau={model_A_dict['tau_ms']:.1f} ms, Td={model_A_dict['Td_ms']:.1f} ms")

        # =========================================================== GAINS
        print("\n=== STAGE D: compute and freeze gains ===")
        mc = ModelC(accel_conditions=model_C_dict["accel_conditions"],
                    decel_conditions=model_C_dict["decel_conditions"])
        ma = ModelA(K_A_rpm_per_pwm=model_A_dict["K_A_rpm_per_pwm"],
                    tau_ms=model_A_dict["tau_ms"],
                    Td_ms=model_A_dict["Td_ms"])
        base_gains = compute_baseline_gains(ma, lambda_ms=LAMBDA_MS)
        casc_gains = compute_cascade_gains(mc, lambda_ms=LAMBDA_MS, op_pwm=OP_PWM)
        ff_table = build_ff_table(mc, rpms=FF_RPMS)
        ff_cmds = ff_table_to_firmware_commands(ff_table)
        gains_payload = {
            "date": today, "lambda_ms": LAMBDA_MS, "op_pwm": OP_PWM,
            "BASE": base_gains, "CASC": casc_gains,
            "FF_table": ff_table, "FF_rpms": FF_RPMS,
        }
        gains_path = models_dir / f"closed_loop_gains_{today}.json"
        gains_path.write_text(json.dumps(gains_payload, indent=2, default=float))
        print(f"  frozen gains saved: {gains_path}")

        # upload to firmware
        bs.send(f"GAINS_BASE {base_gains['Kp']:.6f} {base_gains['Ki']:.6f}")
        cg = casc_gains
        gc = " ".join(f"{cg[k]['Kp']:.6f} {cg[k]['Ki']:.6f}"
                       for k in ("accel_fwd", "decel_fwd", "accel_rev", "decel_rev"))
        bs.send(f"GAINS_CASC {gc}")
        for cmd in ff_cmds:
            bs.send(cmd)

        # =========================================================== CL
        print("\n=== STAGE E: closed-loop trials ===")
        profiles = ["P1", "P2", "P3", "P4"]
        cl_log_path = session_dir / "closed_loop.log"
        trial_index = []  # bookkeeping: (profile, pair_id, controller, csv_name)
        with open(cl_log_path, "w") as cl_log:
            for profile in profiles:
                pair_order = list(range(args.n_pairs))
                rng.shuffle(pair_order)
                print(f"\n  Profile {profile}: pair order {pair_order}")
                for pair_id in pair_order:
                    ctrls = ["BASE", "CASC"]
                    if rng.random() < 0.5:
                        ctrls = ["CASC", "BASE"]
                    for ctrl in ctrls:
                        # firmware emits "=== START P3_BASE ===" — give per-pair name
                        out_name = f"{profile}_pair{pair_id:02d}_{ctrl}"
                        print(f"    -> {out_name}")
                        bs.send(ctrl, post_delay=0.15)
                        bs.send(f"LOAD {profile}", post_delay=0.15)
                        # capture only this trial's output
                        tmp_path = closed_dir / f"_tmp_{out_name}.log"
                        bs.send("GO", post_delay=0.05)
                        trial_text = bs.capture_until(
                            "# === CLOSED-LOOP TRIAL COMPLETE ===",
                            timeout_s=120,
                            sink_path=tmp_path,
                        )
                        cl_log.write(trial_text); cl_log.flush()
                        # split this trial's text into a single CSV with the
                        # per-pair filename
                        emit_name = f"{profile}_{ctrl}"
                        written = split_log_into_csvs(
                            trial_text, closed_dir,
                            rename_map={emit_name: out_name},
                        )
                        if written:
                            trial_index.append({
                                "profile": profile, "pair_id": pair_id,
                                "controller": ctrl, "csv": f"{out_name}.csv",
                            })
                        try:
                            tmp_path.unlink()
                        except FileNotFoundError:
                            pass

        # =========================================================== DRIFT
        print("\n=== STAGE F: DRIFT check (6 trials, ~1 min) ===")
        bs.send("DRIFT", post_delay=0.3)
        drift_log_path = session_dir / "drift.log"
        bs.send("GO")
        drift_text = bs.capture_until("# === DRIFT SEQUENCE COMPLETE ===",
                                       timeout_s=300, sink_path=drift_log_path)
        drift_names = split_log_into_csvs(drift_text, drift_dir)
        print(f"  Wrote {len(drift_names)} drift CSVs to {drift_dir}")

        # Trial index written for analysis
        (session_dir / "trial_index.json").write_text(json.dumps({
            "date": today, "seed": args.seed, "n_pairs": args.n_pairs,
            "trials": trial_index,
        }, indent=2))
        print("\nSession complete. trial_index.json written.")

    finally:
        bs.close()


if __name__ == "__main__":
    main()
