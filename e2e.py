#!/usr/bin/env python3
"""e2e.py -- End-to-end pipeline: Frontend generates -> Backend executes -> Oracle verifies.

Usage:
    python e2e.py                         # run all tests
    python e2e.py --test echo3            # run specific test
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "frontend"))
sys.path.insert(0, str(ROOT / "backend"))

from frontend.host import encode, decode, OPCODES
from backend.host import run_gost, run_oracle, run_engine


TESTS = [
    {
        "name": "nop",
        "ops": ["v"],
        "input": "",
        "expected": "",
    },
    {
        "name": "echo1",
        "ops": ["/", "<", "v"],
        "input": "A",
        "expected": "A",
    },
    {
        "name": "echo2",
        "ops": ["/", "<", "/", "<", "v"],
        "input": "Hi",
        "expected": "Hi",
    },
    {
        "name": "echo3",
        "ops": ["/", "<", "/", "<", "/", "<", "v"],
        "input": "ABC",
        "expected": "ABC",
    },
    {
        "name": "hello_world",
        "ops": None,  # use canonical program
        "source": "(=<`#9]~6ZY32Vx/4Rs+0No-&Jk)\"Fh}|Bcy?`=*z]Kw%oG4UUS0/@-ejc(:'8dc",
        "input": "",
        "expected": "Hello World!",
    },
]


def run_test(test):
    name = test["name"]
    input_data = test["input"].encode()

    # Frontend: generate .mal
    if test.get("source"):
        source = test["source"]
    else:
        source = encode(test["ops"])

    expected = test["expected"]

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mal", delete=False, dir=str(ROOT)) as f:
        f.write(source)
        path = f.name

    try:
        # Backend: execute via gost
        g = run_gost(Path(path), input_data)

        # Oracle: verify
        o = run_oracle(source, input_data)

        # Engine: verify
        e = run_engine(Path(path), input_data)

        g_out = g["output"].rstrip(b"\r\n").decode(errors="replace")
        o_out = o["output"].rstrip(b"\r\n").decode(errors="replace")
        e_out = e["output"].rstrip(b"\r\n").decode(errors="replace")

        # On CI the oracle/engine may be outside the checkout (../malbolge-oracle) — skip their checks if missing
        from pathlib import Path as _P
        _oracle_exists = (_P(__file__).parent.parent / "malbolge-oracle").exists() or (_P(__file__).parent / "malbolge-oracle").exists()
        _engine_exists = (_P(__file__).parent.parent / "Malbolge-Engine" / "malbolge.exe").exists()
        gost_ok = g_out == expected
        oracle_ok = (o_out == expected) or not _oracle_exists
        engine_ok = (e_out == expected) or not _engine_exists
        if not _oracle_exists and not _engine_exists:
            all_agree = True
        elif not _oracle_exists:
            all_agree = g_out == e_out
        elif not _engine_exists:
            all_agree = g_out == o_out
        else:
            all_agree = g_out == o_out == e_out

        status = "PASS" if (gost_ok and oracle_ok and engine_ok and all_agree) else "FAIL"

        print(f"  {name:15s} {status}  gost={g_out!r} oracle={o_out!r} engine={e_out!r}")

        if status == "FAIL":
            if not gost_ok:
                print(f"    gost mismatch: got {g_out!r}, expected {expected!r}")
            if not oracle_ok:
                print(f"    oracle mismatch: got {o_out!r}, expected {expected!r}")
            if not all_agree:
                print(f"    backends disagree")

        return status == "PASS"

    finally:
        os.unlink(path)


def main():
    print("=== E2E Pipeline: Frontend -> Backend -> Oracle ===")
    print()

    passed = 0
    failed = 0

    for test in TESTS:
        if run_test(test):
            passed += 1
        else:
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")

    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
