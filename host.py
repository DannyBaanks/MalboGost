#!/usr/bin/env python3
"""host.py -- Python orchestrator for the Malbolge engine.

Runs .mal programs via gost.c, verifies against oracle, provides CLI.

Usage:
    python host.py run examples/echo.mal --input "A"
    python host.py verify examples/echo.mal --input "A"
    python host.py compile   # build gost.c if needed
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

GOST_C = Path(__file__).parent / "gost.c"
GOST_EXE = Path(__file__).parent / "gost.exe"
ORACLE = Path(__file__).parent.parent / "malbolge-oracle" / "oracle.py"
ENGINE = Path(__file__).parent.parent / "Malbolge-Engine" / "malbolge.exe"


def find_gost() -> Path:
    """Find gost executable, compile if needed."""
    if GOST_EXE.exists():
        return GOST_EXE
    compile_gost()
    if GOST_EXE.exists():
        return GOST_EXE
    raise FileNotFoundError("gost.exe not found and compilation failed")


def compile_gost():
    """Compile gost.c with gcc or cl."""
    print("Compiling gost.c...")
    try:
        r = subprocess.run(
            ["gcc", "-O2", "-Wall", "-Wextra", "-std=c11",
             "-o", str(GOST_EXE), str(GOST_C)],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            print(f"  Built: {GOST_EXE}")
            return
        print(f"  gcc failed:\n{r.stderr}")
    except FileNotFoundError:
        pass

    # Try MSVC
    try:
        r = subprocess.run(
            ["cl", "/O2", "/W4", str(GOST_C)],
            capture_output=True, text=True, timeout=30,
            cwd=str(GOST_EXE.parent)
        )
        if r.returncode == 0:
            print(f"  Built: {GOST_EXE}")
            return
        print(f"  cl failed:\n{r.stderr}")
    except FileNotFoundError:
        pass

    print("  ERROR: no compiler found (gcc or cl required)")


def run_gost(program: Path, input_data: bytes = b"",
             max_steps: int = 100_000_000) -> tuple[bytes, dict]:
    """Run a .mal program via gost. Returns (output, stats)."""
    gost = find_gost()
    cmd = [str(gost), str(program), str(max_steps)]
    r = subprocess.run(
        cmd, input=input_data, capture_output=True, timeout=30
    )
    output = r.stdout
    # Parse stats from stderr
    stats = {"steps": 0, "output_len": 0, "terminated": False}
    for line in r.stderr.decode(errors="replace").splitlines():
        if line.startswith("steps="):
            parts = line.split()
            for p in parts:
                if p.startswith("steps="):
                    stats["steps"] = int(p.split("=")[1])
                elif p.startswith("output="):
                    stats["output_len"] = int(p.split("=")[1])
                elif p.startswith("terminated="):
                    stats["terminated"] = p.split("=")[1] == "yes"
    return output, stats


def run_oracle(program: Path, input_data: bytes = b"") -> bytes:
    """Run via Python oracle for verification."""
    if not ORACLE.exists():
        raise FileNotFoundError(f"Oracle not found: {ORACLE}")

    # Run oracle as subprocess (avoids import path issues)
    source = program.read_text(encoding="ascii", errors="replace")
    source = ''.join(ch for ch in source if 33 <= ord(ch) <= 126)

    code = f"""
import sys
sys.path.insert(0, r"{ORACLE.parent}")
from oracle import Oracle
m = Oracle()
m.load_ascii(list({source!r}))
if {input_data!r}:
    m.provide_input({input_data.decode('ascii', errors='replace')!r})
r = m.run(max_steps=100_000_000)
sys.stdout.buffer.write(r.output.encode('ascii', errors='replace'))
"""
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f"Oracle failed: {r.stderr.decode()}")
    return r.stdout


def run_engine(program: Path, input_data: bytes = b"",
               max_steps: int = 100_000_000) -> bytes:
    """Run via Malbolge-Engine C implementation."""
    if not ENGINE.exists():
        raise FileNotFoundError(f"Engine not found: {ENGINE}")
    cmd = [str(ENGINE), str(program), str(max_steps)]
    r = subprocess.run(
        cmd, input=input_data, capture_output=True, timeout=30
    )
    return r.stdout


def cmd_compile(args):
    compile_gost()


def cmd_run(args):
    program = Path(args.program)
    input_data = args.input.encode() if args.input else b""
    output, stats = run_gost(program, input_data, args.steps)
    sys.stdout.buffer.write(output)
    if not output.endswith(b"\n"):
        print()
    print(f"[steps={stats['steps']} terminated={stats['terminated']}]", file=sys.stderr)


def cmd_verify(args):
    """Cross-backend verification: gost vs oracle vs engine."""
    program = Path(args.program)
    input_data = args.input.encode() if args.input else b""

    results = {}

    # gost
    try:
        out, stats = run_gost(program, input_data, args.steps)
        results["gost"] = {"output": out, "steps": stats["steps"],
                           "terminated": stats["terminated"]}
    except Exception as e:
        results["gost"] = {"error": str(e)}

    # oracle
    try:
        out = run_oracle(program, input_data)
        results["oracle"] = {"output": out}
    except Exception as e:
        results["oracle"] = {"error": str(e)}

    # engine
    try:
        out = run_engine(program, input_data, args.steps)
        results["engine"] = {"output": out}
    except Exception as e:
        results["engine"] = {"error": str(e)}

    # Compare
    print(f"Program: {program}")
    print(f"Input:   {args.input!r}")
    print()
    for name, r in results.items():
        if "error" in r:
            print(f"  {name:10s} ERROR: {r['error']}")
        else:
            out = r["output"]
            steps = r.get("steps", "?")
            term = r.get("terminated", "?")
            print(f"  {name:10s} output={out!r} steps={steps} terminated={term}")

    # Check agreement (normalize trailing \r\n from Windows text mode)
    outputs = {n: r.get("output", b"").rstrip(b"\r\n") for n, r in results.items() if "output" in r}
    if len(set(outputs.values())) == 1:
        print("\n  ALL BACKENDS AGREE")
    elif len(outputs) > 1:
        print("\n  MISMATCH between backends!")
        for n, o in outputs.items():
            print(f"    {n}: {o!r}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Malbolge engine host")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("compile", help="Compile gost.c")

    p_run = sub.add_parser("run", help="Run a .mal program")
    p_run.add_argument("program", help="Path to .mal file")
    p_run.add_argument("--input", "-i", default="", help="Input data")
    p_run.add_argument("--steps", "-s", type=int, default=100_000_000)

    p_verify = sub.add_parser("verify", help="Cross-backend verify")
    p_verify.add_argument("program", help="Path to .mal file")
    p_verify.add_argument("--input", "-i", default="", help="Input data")
    p_verify.add_argument("--steps", "-s", type=int, default=100_000_000)

    args = parser.parse_args()
    if args.cmd == "compile":
        cmd_compile(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "verify":
        cmd_verify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
