#!/usr/bin/env python3
"""run_milestone.py -- Run a milestone .mal against many inputs (COMPILE_ONCE_TEST_MANY).

Applies the rule: the SAME .mal file (verified SHA-256 unchanged across all runs)
must handle different runtime inputs. Expected outputs are computed by the oracle
AFTER/independently of execution.

Usage:
    python run_milestone.py <milestone_dir> --inputs A B C --interpreter gost
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path

GOST = str(Path(__file__).parent / "gost.exe")
ORACLE_DIR = str(Path(__file__).parent.parent / "malbolge-oracle")

# inputs are single chars (M0/M1 contract: read 1 char)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_gost(program, input_data, steps=1000000):
    r = subprocess.run([GOST, str(program), str(steps)],
                       input=input_data, capture_output=True, timeout=30)
    # gost: output may have \r\n from Windows text mode; strip line endings
    return r.stdout.decode("ascii", errors="replace").rstrip("\r\n"), r.returncode


def run_oracle(source, input_data, steps=1000000):
    input_str = input_data.decode("ascii", errors="replace") if input_data else ""
    code = (
        f'import sys; sys.path.insert(0, r"{ORACLE_DIR}")\n'
        f'from oracle import Oracle\n'
        f'm = Oracle(); m.load_ascii(list({source!r}))\n'
        f'if {input_str!r}: m.provide_input({input_str!r})\n'
        f'r = m.run(max_steps={steps})\n'
        f'sys.stdout.buffer.write(r.output.encode("ascii"))\n'
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=30)
    return r.stdout.decode("ascii", errors="replace"), r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("milestone_dir")
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--interpreter", default="gost", choices=["gost"])
    ap.add_argument("--verify-oracle", action="store_true",
                    help="Cross-check each output against the oracle")
    args = ap.parse_args()

    md = Path(args.milestone_dir)
    program = md / "program.mal"
    if not program.exists():
        print(f"ERROR: {program} not found", file=sys.stderr)
        sys.exit(1)

    source = program.read_text(encoding="ascii", errors="replace")
    source = "".join(c for c in source if 33 <= ord(c) <= 126)

    # Baseline SHA-256 (the ONE program that must survive all inputs)
    baseline_sha = sha256_file(program)

    results = []
    all_pass = True

    print(f"=== Milestone: {md.name} ===")
    print(f"program: {program}")
    print(f"baseline SHA-256: {baseline_sha}")
    print()

    for inp in args.inputs:
        in_bytes = inp.encode("ascii")

        # Re-hash EVERY run to prove same program
        cur_sha = sha256_file(program)
        same_program = cur_sha == baseline_sha

        out, rc = run_gost(program, in_bytes)

        # Expected computed by oracle (independent of gost execution)
        oracle_out, oracle_rc = run_oracle(source, in_bytes)

        # For M0/M1: expected = the single input char (echo semantics)
        expected = inp if len(inp) == 1 else inp

        match = (out == oracle_out) and (out == expected)
        if not (same_program and match):
            all_pass = False

        status = "PASS" if (same_program and match) else "FAIL"
        results.append({
            "input": inp,
            "input_hex": in_bytes.hex(),
            "program_sha256": cur_sha,
            "same_program_as_baseline": same_program,
            "output": out,
            "expected": expected,
            "oracle_output": oracle_out,
            "gost_exit": rc,
            "status": status,
        })

        print(f"  input={inp!r:6} sha_same={same_program} "
              f"gost={out!r:8} expected={expected!r:8} "
              f"oracle={oracle_out!r:8} -> {status}")

    evidence = {
        "milestone": md.name,
        "interpreter": args.interpreter,
        "command": f"py run_milestone.py {md} --inputs {' '.join(args.inputs)}",
        "program_path": str(program),
        "program_sha256": baseline_sha,
        "compile_once_test_many": all(r["same_program_as_baseline"] for r in results),
        "results": results,
        "overall": "PASS" if all_pass else "FAIL",
    }

    ev_path = md / "evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (md / "SHA256SUMS.txt").write_text(f"{baseline_sha}  program.mal\n", encoding="utf-8")

    print()
    print(f"overall: {evidence['overall']}")
    print(f"compile_once_test_many: {evidence['compile_once_test_many']}")
    print(f"evidence: {ev_path}")

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()