#!/usr/bin/env python3
"""Generate and verify Malbolge programs using XLAT1-based encoding."""
from pathlib import Path

XLAT1 = (
    "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z'"
    ";FNQuY]szf$!BS/|t:Pn6^Ha"
)

# Instruction characters and their XLAT1 indices
INST = {
    'IN':    '/',
    'OUT':   '<',
    'HALT':  'v',
    'CRAZY': 'p',
    'ROT':   '*',
    'MOVD':  'j',
    'BRANCH':'i',
}

def encode(inst_chars):
    """Encode instruction characters to printable Malbolge source.
    
    Decode: XLAT1[(mem[i] - 33 + i) % 94] = inst_chars[i]
    Encode: mem[i] = (find(inst_chars[i]) - i) % 94 + 33
    """
    result = []
    for i, ch in enumerate(inst_chars):
        idx = XLAT1.index(ch)
        raw = (idx - i) % 94 + 33
        result.append(chr(raw))
    return ''.join(result)

def decode(source):
    """Decode source to instruction characters."""
    result = []
    for i, ch in enumerate(source):
        v = (ord(ch) - 33 + i) % 94
        result.append(XLAT1[v])
    return ''.join(result)

# --- Generate programs ---
programs = {
    'nop':   ['v'],
    'echo1': ['/', '<', 'v'],
    'echo2': ['/', '<', '/', '<', 'v'],
    'echo3': ['/', '<', '/', '<', '/', '<', 'v'],
}

base = str(Path(__file__).parent / "examples")
for name, ops in programs.items():
    src = encode(ops)
    dec = decode(src)
    match = dec == ''.join(ops)
    print(f"{name}: {src!r} len={len(src)} decode={dec!r} match={match}")
    path = f'{base}/{name}.mal'
    with open(path, 'wb') as f:
        f.write(src.encode('ascii'))
    print(f"  -> {path}")

# Echo3 trace
print("\n--- echo3 trace ---")
src = encode(['/', '<', '/', '<', '/', '<', 'v'])
for i, ch in enumerate(src):
    v = (ord(ch) - 33 + i) % 94
    ix = XLAT1[v]
    print(f"  pos {i}: mem={ord(ch)}, idx={v}, xlat1={ix!r}")
