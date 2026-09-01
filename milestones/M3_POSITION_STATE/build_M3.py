#!/usr/bin/env python3
"""build_M3.py -- Build and verify M3 POSITION_STATE.

Program: IN CRAZY OUT IN CRAZY OUT HALT
  read c1 -> crazy(c1, mem[1]) -> out    (i=0, constant 61)
  read c2 -> crazy(c2, mem[4]) -> out    (i=1, constant 58)

The index i changes between characters: the two CRAZY stages use different
constants (61 vs 58) because they execute at different program positions.
The second output verifiably depends on the changed state (58 != 61).
"""
import hashlib, subprocess, sys, json
from pathlib import Path

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
ORACLE_DIR = str(Path(__file__).parent.parent.parent.parent / "malbolge-oracle")
GOST = str(Path(__file__).parent.parent.parent / "gost.exe")

def enc(inst, pos):
    return chr((XLAT1.index(inst) - pos) % 94 + 33)

def crazy(a, b):
    t = [1, 1, 2, 0, 0, 2, 0, 2, 1]
    r, p = 0, 1
    for _ in range(10):
        r += t[(a % 3) * 3 + (b % 3)] * p
        a //= 3; b //= 3; p *= 3
    return r

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_gost(prog_file, inp):
    r = subprocess.run([GOST, str(prog_file), "1000000"], input=inp.encode(),
                       capture_output=True, timeout=30)
    return r.stdout.decode("ascii", errors="replace").rstrip("\r\n")

def run_oracle(prog, inp):
    code = (f'import sys;sys.path.insert(0,r"{ORACLE_DIR}");from oracle import Oracle;'
            f'm=Oracle();m.load_ascii(list({prog!r}));m.provide_input({inp!r});'
            f'r=m.run(max_steps=1000000);sys.stdout.write(r.output)')
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=30)
    return r.stdout.decode("ascii", errors="replace")

# Build program: IN CRAZY OUT IN CRAZY OUT HALT
insts = ['/', 'p', '<', '/', 'p', '<', 'v']
prog = ''.join(enc(i, p) for p, i in enumerate(insts))
print(f"M3 program: {prog!r} bytes={[ord(c) for c in prog]}")
for p, ch in enumerate(prog):
    print(f"  pos {p}: {ch!r}({ord(ch)}) -> {XLAT1[(ord(ch)-33+p)%94]!r}")
print(f"  mem[1]={ord(prog[1])} (stage 0 constant)")
print(f"  mem[4]={ord(prog[4])} (stage 1 constant)")
print()

md = Path(__file__).parent
md.mkdir(parents=True, exist_ok=True)
(prog_file := md / "program.mal").write_text(prog, encoding="ascii")
baseline_sha = sha(prog_file)
print(f"sha256: {baseline_sha}")

# Stage constants
K0 = ord(prog[1])
K1 = ord(prog[4])

# Test pairs: (input1, input2)
pairs = [("A", "B"), ("X", "Y"), ("1", "2"), ("p", "q"), ("m", "n")]
results = []
all_pass = True
print("\n=== Execution (same .mal, many input pairs) ===")
for c1, c2 in pairs:
    cur_sha = sha(prog_file)
    same = cur_sha == baseline_sha
    inp = c1 + c2
    gout = run_gost(prog_file, inp)
    oout = run_oracle(prog, inp)
    # Independent expected
    exp = chr(crazy(ord(c1), K0) % 256) + chr(crazy(ord(c2), K1) % 256)
    ok = same and gout == exp and gout == oout
    if not ok:
        all_pass = False
    results.append({
        "inputs": inp, "input_hex": inp.encode().hex(),
        "program_sha256": cur_sha, "same_program": same,
        "gost": gout, "oracle": oout, "expected": exp,
        "stage0": {"c": c1, "K": K0}, "stage1": {"c": c2, "K": K1},
        "status": "PASS" if ok else "FAIL"
    })
    print(f"  input={inp!r} sha_same={same} gost={gout!r} expected={exp!r} oracle={oout!r} -> {'PASS' if ok else 'FAIL'}")

evidence = {
    "milestone": "M3_POSITION_STATE",
    "interpreter": "gost.exe",
    "program": str(prog_file), "program_sha256": baseline_sha,
    "structure": "IN CRAZY OUT IN CRAZY OUT HALT",
    "index_state": {
        "description": "i = per-character stage index, encoded in program position",
        "stage0_constant": K0, "stage1_constant": K1,
        "transform_stage0": f"crazy(c1, {K0}) % 256",
        "transform_stage1": f"crazy(c2, {K1}) % 256",
        "second_depends_on_changed_i": K1 != K0
    },
    "compile_once_test_many": all(r["same_program"] for r in results),
    "results": results, "overall": "PASS" if all_pass else "FAIL"
}
(md / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
(md / "SHA256SUMS.txt").write_text(f"{baseline_sha}  program.mal\n", encoding="utf-8")
print(f"\noverall: {evidence['overall']}")
print(f"second_stage_depends_on_changed_i: {K1 != K0}")
sys.exit(0 if all_pass else 1)