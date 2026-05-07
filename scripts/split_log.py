#!/usr/bin/env python3
"""
split_log.py — split a step-response serial log into per-trial CSV files.

Usage:
    python scripts/split_log.py <log_file> <output_dir>

Example:
    python scripts/split_log.py \\
           data/raw/serial_logs/2026-05-06_phase21_session.log \\
           data/raw/step_responses/

Behaviour:
    1. Reads the log file
    2. Finds every block bounded by:
           === START <name> ===
           ...
           === END ===
    3. Writes each block (excluding the START/END markers) as
       <output_dir>/<name>.csv
    4. Reports trial count and per-file row counts
"""
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    log_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    if not log_path.exists():
        print(f"ERROR: log file not found: {log_path}")
        sys.exit(1)

    content = log_path.read_text()
    pattern = r"=== START (\S+) ===\s*\n(.*?)\n=== END ==="
    trials = re.findall(pattern, content, re.DOTALL)

    if not trials:
        print("ERROR: no trials found. Check the log file format.")
        sys.exit(1)

    print(f"Found {len(trials)} trial(s). Writing to {out_dir}/")
    print()

    for name, body in trials:
        body = body.strip() + "\n"
        out_path = out_dir / f"{name}.csv"
        out_path.write_text(body)
        n_lines = body.count("\n") - 1  # exclude header
        print(f"  {out_path.name:42s}  {n_lines:4d} data rows")

    print()
    print(f"Done. {len(trials)} CSV files written.")


if __name__ == "__main__":
    main()
