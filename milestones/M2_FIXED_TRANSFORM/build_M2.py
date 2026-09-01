#!/usr/bin/env python3
"""build_M2.py -- Build and verify M2 FIXED_TRANSFORM program.

Program: IN, CRAZY, OUT, HALT
After IN: a = input X
CRAZY: a = crazy(X, mem[1])   (mem[1] = the CRAZY instruction char at pos 1)
OUT: emit a % 256
HALT

The transform crazy(X, mem[1]) is non-identity and depends on the input.
"""
import hashlib, subprocess, sys, json
from pathlib import Path

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
ORACLE_DIR = str(Path(__file__).parent.parent.parent.parent / "malbolge-oracle")
GOST = str(Path(__file__).parent.parent.parent / "gost.exe")

def enc(inst, pos):
    return chr((XLAT1.index(inst) - pos) % 94 + 33)

def crazy_trit(a, b):
    table = [1, 1, 2, 0, 0, 2, 0, 2, 1]
    return table[(a % 3) * 3 + (b % 3)]

def crazy(a, b):
    r, p = 0, 1
    for _ in range(10):
        r += crazy_trit(a, b) * p
        a //= 3; b //= 3; p *= 3
    return r

# Build program: IN('/') CRAZY('p') OUT('<') HALT('v')
prog = ''.join(enc(i, p) for p, i in enumerate(['/', 'p', '<', 'v']))
print(f"M2 program: {prog!r} bytes={[ord(c) for c in prog]}")

# Decode verify
for p, ch in enumerate(prog):
    inst = XLAT1[(ord(ch) - 33 + p) % 94]
    print(f"  pos {p}: {ch!r} (value {ord(ch)}) -> {inst!r}")

# mem[1] value = ord(prog[1])
mem1 = ord(prog[1])
print(f"  mem[1] = {prog[1]!r} = {mem1}  -> CRAZY constant")
print()

# Write program
md = Path(__file__).parent
md.mkdir(parents=True, exist_ok=True)
(program := md / "program.mal").write_text(prog, encoding="ascii")
sha = hashlib.sha256(prog.encode()).hexdigest()
print(f"program.mal sha256: {sha}")

# Expected transform per input
print("\nExpected transform (crazy(X, mem[1]) % 256), computed INDEPENDENTLY:")
tests = {}
for inp in "ABXZ7":
    x = ord(inp)
    expected = crazy(x, mem1) % 256
    tests[inp] = chr(expected)
    print(f"  input {inp!r} (={x:3d}) -> crazy(X,{mem1})%256 = {expected} = {chr(expected)!r}")