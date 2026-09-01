#!/usr/bin/env python3
"""backend/host.py -- Execute .mal programs via gost.c.

Usage:
    python host.py run <file.mal> [--input DATA] [--steps N]
    python host.py verify <file.mal> [--input DATA]
"""

import argparse
import subprocess
import sys
import tempfile
import os
from pathlib import Path

GOST_C = Path(__file__).parent.parent / "gost.c"
GOST_EXE = Path(__file__).parent.parent / "gost.exe"
ENGINE = Path(__file__).parent.parent.parent / "Malbolge-Engine" / "malbolge.exe"
ORACLE_DIR = Path(__file__).parent.parent.parent / "malbolge-oracle"


def compile_gost():
    if GOST_EXE.exists():
        return True
    r = subprocess.run(
        ["gcc", "-O2", "-Wall", "-Wextra", "-std=c11",
         "-o", str(GOST_EXE), str(GOST_C)],
        capture_output=True, text=True, timeout=30
    )
    return r.returncode == 0


def run_gost(program: Path, input_data: bytes = b"", steps: int = 100_000_000):
    if not GOST_EXE.exists():
        compile_gost()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mal", delete=False) as f:
        f.write(program.read_text(encoding="ascii", errors="replace"))
        path = f.name
    try:
        r = subprocess.run(
            [str(GOST_EXE), path, str(steps)],
            input=input_data, capture_output=True, timeout=30
        )
        output = r.stdout.rstrip(b"\r\n")
        terminated = r.returncode == 0
        stats = {}
        for line in r.stderr.decode(errors="replace").splitlines():
            if line.startswith("steps="):
                for p in line.split():
                    if p.startswith("steps="):
                        stats["steps"] = int(p.split("=")[1])
                    elif p.startswith("terminated="):
                        stats["terminated"] = p.split("=")[1] == "yes"
        return {"output": output, "rc": r.returncode, **stats}
    finally:
        os.unlink(path)


def run_oracle(source: str, input_data: bytes = b"", steps: int = 100_000_000):
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
    return {"output": r.stdout, "rc": r.returncode}


def run_engine(program: Path, input_data: bytes = b"", steps: int = 100_000_000):
    if not ENGINE.exists():
        return {"output": b"", "rc": -1, "error": "engine not found"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mal", delete=False) as f:
        f.write(program.read_text(encoding="ascii", errors="replace"))
        path = f.name
    try:
        r = subprocess.run(
            [str(ENGINE), path, str(steps)],
            input=input_data, capture_output=True, timeout=30
        )
        return {"output": r.stdout.rstrip(b"\r\n"), "rc": r.returncode}
    finally:
        os.unlink(path)


def cmd_run(args):
    program = Path(args.program)
    input_data = args.input.encode() if args.input else b""
    result = run_gost(program, input_data, args.steps)
    sys.stdout.buffer.write(result["output"])
    if not result["output"].endswith(b"\n"):
        print()
    print(f"[steps={result.get('steps','?')} terminated={result.get('terminated','?')}]", file=sys.stderr)


def cmd_verify(args):
    program = Path(args.program)
    source = program.read_text(encoding="ascii", errors="replace")
    source = "".join(c for c in source if 33 <= ord(c) <= 126)
    input_data = args.input.encode() if args.input else b""

    g = run_gost(program, input_data, args.steps)
    o = run_oracle(source, input_data, args.steps)
    e = run_engine(program, input_data, args.steps)

    results = {"gost": g, "oracle": o, "engine": e}
    print(f"Program: {program.name}")
    for name, r in results.items():
        out = r.get("output", b"").rstrip(b"\r\n")
        print(f"  {name:10s} {out!r}")

    outputs = {n: r.get("output", b"").rstrip(b"\r\n") for n, r in results.items()}
    if len(set(outputs.values())) == 1:
        print("  ALL AGREE")
    else:
        print("  MISMATCH")


def main():
    parser = argparse.ArgumentParser(description="Malbolge backend")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("run")
    p.add_argument("program")
    p.add_argument("--input", "-i", default="")
    p.add_argument("--steps", "-s", type=int, default=100_000_000)

    p = sub.add_parser("verify")
    p.add_argument("program")
    p.add_argument("--input", "-i", default="")
    p.add_argument("--steps", "-s", type=int, default=100_000_000)

    args = parser.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "verify":
        cmd_verify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
