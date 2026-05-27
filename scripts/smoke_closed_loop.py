#!/usr/bin/env python3
"""
smoke_closed_loop.py — Stage 1 smoke test for the closed-loop firmware.

Drives the firmware through a fixed command sequence that:
  1. Loads placeholder gains and FF table (from Stage 0 simulation; not
     calibrated to the real motor — only used to confirm stability).
  2. Runs P3 (reversal profile, +100 -> -100 rpm over 10 s) with BASE.
  3. Runs P3 with CASC.
  4. Streams everything to stdout + a log file under data/raw/serial_logs/.

After completion, run `scripts/split_log.py` on the log to confirm the trial
blocks parse. STOP is always available by pressing Ctrl-C.

Usage:
    python scripts/smoke_closed_loop.py <port> [log_path]
"""
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


COMMAND_SCRIPT = [
    # (delay_before_s, command, label)
    (0.0,  "?",                                                                "banner"),
    (0.3,  "GAINS_BASE 1.2033 5.7996",                                         "base gains"),
    (0.3,  "GAINS_CASC 0.2355 2.4762 0.6525 2.3704 0.2066 2.5427 0.7631 2.4905","cascade gains"),
    (0.3,  "FF_FWD 5 50 154 80 176 100 187 150 212 200 235",                   "ff fwd table"),
    (0.3,  "FF_REV 5 50 144 80 167 100 180 150 208 200 230",                   "ff rev table"),
    (0.3,  "BASE",                                                             "select BASE"),
    (0.3,  "LOAD P3",                                                          "load P3"),
    (0.3,  "GO",                                                               "GO base/P3"),
    # Trial duration ~10 s; wait then continue.
    (14.0, "CASC",                                                             "select CASC"),
    (0.3,  "LOAD P3",                                                          "load P3"),
    (0.3,  "GO",                                                               "GO casc/P3"),
    (14.0, "?",                                                                "final banner"),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    port = sys.argv[1]
    if len(sys.argv) >= 3:
        log_path = Path(sys.argv[2])
    else:
        from datetime import date
        log_path = Path("data/raw/serial_logs") / f"{date.today().isoformat()}_phase3_smoke.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening {port} at 230400 baud; logging to {log_path}")
    with serial.Serial(port, 230400, timeout=0.1) as ser, open(log_path, "w") as f:
        # let the board finish booting
        time.sleep(2.5)
        # drain pending banner
        t0 = time.time()
        while ser.in_waiting > 0 or time.time() - t0 < 1.0:
            chunk = ser.read(max(ser.in_waiting, 1)).decode("utf-8", errors="ignore")
            if chunk:
                sys.stdout.write(chunk); sys.stdout.flush()
                f.write(chunk); f.flush()
            time.sleep(0.05)

        try:
            for delay, cmd, label in COMMAND_SCRIPT:
                # wait `delay` seconds, streaming output the whole time
                t_end = time.time() + delay
                while time.time() < t_end:
                    chunk = ser.read(max(ser.in_waiting, 1)).decode("utf-8", errors="ignore")
                    if chunk:
                        sys.stdout.write(chunk); sys.stdout.flush()
                        f.write(chunk); f.flush()
                    else:
                        time.sleep(0.02)

                marker = f"\n# >>> [{label}] sending: {cmd}\n"
                sys.stdout.write(marker); sys.stdout.flush()
                f.write(marker); f.flush()
                ser.write((cmd + "\n").encode())
                ser.flush()
        except KeyboardInterrupt:
            print("\n# >>> KeyboardInterrupt: sending STOP")
            ser.write(b"STOP\n")
            time.sleep(0.5)
            f.write("\n# >>> KeyboardInterrupt: STOP sent\n")

        # final drain
        t_end = time.time() + 2.0
        while time.time() < t_end:
            chunk = ser.read(max(ser.in_waiting, 1)).decode("utf-8", errors="ignore")
            if chunk:
                sys.stdout.write(chunk); sys.stdout.flush()
                f.write(chunk); f.flush()
            else:
                time.sleep(0.05)

    print(f"\nLog saved: {log_path}")


if __name__ == "__main__":
    main()
