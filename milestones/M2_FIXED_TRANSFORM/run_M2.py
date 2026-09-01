#!/usr/bin/env python3
"""run_M2.py -- Execute M2 FIXED_TRANSFORM with same .mal, many inputs.

Verifies: gost output == oracle output == independently-computed crazy(X, mem1)%256
The expected transform is computed HERE (in the verifier) from first principles,
NOT injected into the program. The program 'u=aN' is fixed (same SHA-256).
"""
import subprocess, hashlib, sys, json
from pathlib import Path

ORACLE_DIR = str(Path(__file__).parent.parent.parent.parent / "malbolge-oracle")
GOST = str(Path(__file__).parent.parent.parent / "gost.exe")
MD = Path(__file__).parent
PROGRAM = MD / "program.mal"

def crazy(a, b):
    t = [1, 1, 2, 0, 0, 2, 0, 2, 1]  # (a%3)*3+(b%3): rows a-trit, cols b-trit
    r, p = 0, 1
    for _ in range(10):
        r += t[(a % 3) * 3 + (b % 3)] * p
        a //= 3; b //= 3; p *= 3
    return r

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_gost(inp):
    r = subprocess.run([GOST, str(PROGRAM), "1000000"], input=inp.encode(),
                       capture_output=True, timeout=30)
    return r.stdout.decode("ascii", errors="replace").rstrip("\r\n")

def run_oracle(prog, inp):
    code = (f'import sys;sys.path.insert(0,r"{ORACLE_DIR}");from oracle import Oracle;'
            f'm=Oracle();m.load_ascii(list({prog!r}));m.provide_input({inp!r});'
            f'r=m.run(max_steps=1000000);sys.stdout.write(r.output)')
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=30)
    return r.stdout.decode("ascii", errors="replace")

prog = PROGRAM.read_text(encoding="ascii")
prog = "".join(c for c in prog if 33 <= ord(c) <= 126)
baseline_sha = sha(PROGRAM)
mem1 = ord(prog[1])

print(f"=== M2 FIXED_TRANSFORM ===")
print(f"program: {prog!r}")
print(f"sha256: {baseline_sha}")
print(f"transform: a = crazy(input, mem[1]={mem1}) % 256   (computed in verifier)")
print()

results = []
all_pass = True
for inp in "ABXZ7":
    cur_sha = sha(PROGRAM)
    same = cur_sha == baseline_sha
    gout = run_gost(inp)
    oout = run_oracle(prog, inp)
    expected = chr(crazy(ord(inp), mem1) % 256)  # independent computation
    ok = (same and gout == expected and gout == oout)
    if not ok:
        all_pass = False
    results.append({
        "input": inp, "input_hex": inp.encode().hex(),
        "program_sha256": cur_sha, "same_program": same,
        "gost": gout, "oracle": oout, "expected_crazy": expected, "status": "PASS" if ok else "FAIL"
    })
    print(f"  input={inp!r} sha_same={same} gost={gout!r} crazy_expected={expected!r} oracle={oout!r} -> {'PASS' if ok else 'FAIL'}")

evidence = {
    "milestone": "M2_FIXED_TRANSFORM",
    "interpreter": "gost.exe",
    "program": str(PROGRAM), "program_sha256": baseline_sha,
    "transform": f"a = crazy(input, mem[1]={mem1}) % 256",
    "compile_once_test_many": all(r["same_program"] for r in results),
    "results": results, "overall": "PASS" if all_pass else "FAIL"
}
(MD / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
(MD / "SHA256SUMS.txt").write_text(f"{baseline_sha}  program.mal\n", encoding="utf-8")
print(f"\noverall: {evidence['overall']}  compile_once_test_many: {evidence['compile_once_test_many']}")
print(f"evidence: {MD/'evidence.json'}")
sys.exit(0 if all_pass else 1)