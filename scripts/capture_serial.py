#!/usr/bin/env python3
"""
capture_serial.py — capture step-response firmware output to a log file.

Usage:
    python scripts/capture_serial.py <port> <output_log>

Example:
    python scripts/capture_serial.py /dev/ttyACM0 \\
           data/raw/serial_logs/2026-05-06_phase21_session.log

Behaviour:
    1. Opens serial port at 230400 baud
    2. Drains any pending output
    3. Sends "GO" to start the firmware sequence
    4. Captures every line to stdout AND to the output log
    5. Stops when "SEQUENCE COMPLETE" is seen, OR after 30s of silence

Requires:  pip install pyserial
"""
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    port = sys.argv[1]
    out_path = Path(sys.argv[2])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to {port} at 230400 baud...")
    with serial.Serial(port, 230400, timeout=1) as ser, open(out_path, "w") as f:
        # Allow startup output (~3s)
        time.sleep(3)

        # Drain any pending data
        while ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
            sys.stdout.write(chunk)
            f.write(chunk)
        f.flush()

        # Send GO
        print("\n>>> Sending GO command\n", flush=True)
        ser.write(b"GO\n")

        # Capture loop
        last_data = time.time()
        while True:
            line = ser.readline().decode("utf-8", errors="ignore")
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
                f.write(line)
                f.flush()
                last_data = time.time()
                if "SEQUENCE COMPLETE" in line:
                    print("\n>>> Capture complete.")
                    break
            elif time.time() - last_data > 30:
                print("\n>>> 30 s of silence. Ending capture (partial log saved).")
                break

    print(f"Log saved: {out_path}")


if __name__ == "__main__":
    main()
