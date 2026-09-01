# GOST — Malbolge Frontend in Pure Malbolge

> **A Malbolge program that writes Malbolge programs.** Python is only the cable — the logic lives in `.mal` and is verified on three independent interpreters.

### Why "gost"?

`gost.c` is the standalone, GCC-built Malbolge interpreter at the core of the repo — the *host* that runs the Malbolge engine. The name is a nod to *ghost* (Malbolge is famously haunted) and to the Russian *gost'* (guest) — the host that guests the Malbolge memory `E=(I,X,O,S)`. The repo is called `gost` because everything orbits that binary: `frontend.mal` (pure Malbolge) + `gost` (C) + `oracle` (Python) — the same `.mal` runs on all three and the Python host is only the cable. Delete `frontend.mal` → frontend is gone; keep `gost.c` → you can still verify everything.

[![CI](https://github.com/DannyBaanks/gost/actions/workflows/ci.yml/badge.svg)](https://github.com/DannyBaanks/gost/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GOST is a research-grade Malbolge frontend: a single `.mal` file (plus the same SHA-256 across all inputs) reads **variable runtime input** and emits a **Malbolge print program** for that input. The same frontend handles many inputs (`COMPILE_ONCE_TEST_MANY`), and every claim is backed by hashed evidence and cross-checked on three runtimes: `gost.c` (GCC/C, canonical), `malbolge-oracle` (Python reference, Iizawa 2005), and `Malbolge-Engine`.

```bash
echo -n "Hi" | ./gost gost/frontend.mal  > print_Hi.mal   # frontend (Malbolge) generates
./gost print_Hi.mal                # print program (Malbolge) runs
# → Hi
```

---

## Why Malbolge?

Malbolge is the canonical "hard to program" language: every instruction is encrypted with its position, memory self-modifies on each step, and only 8 of the 94 printable characters are real ops. Writing a **self-hosting frontend** in it is a stress-test for:

- position-dependent decoding (`XLAT1[(mem[c]-33+c)%94]`)
- the ternary `crazy` operator and `rot`
- `COMPILE_ONCE_TEST_MANY` evidence discipline

This repo shows it can be done — incrementally, with evidence at each rung.

---

## 90-Second Architecture

```
input text ──► frontend.mal (Malbolge) ──► print_<text>.mal (Malbolge) ──► output text
               ▲                         ▲
               │                         │
            gost.c                   gost.c
          (or oracle)              (or oracle)
```

- **Engine ≠ Host ≠ Bridge** — the Malbolge memory `E=(I,X,O,S)` is the engine; `gost.c` is the host; `frontend/host.py` is only the cable (open file, pipe stdin, capture stdout). Delete `frontend.mal` → frontend disappears. Delete `backend.mal` → backend disappears.
- **Frozen contract** `E=(I,X,O,S)`: stdin JSON, 60s timeout, last stdout line JSON with `status/law_result`. A runner that just prints `PASS` is a stub, not `GOLDEN`.
- **Three genealogies never collapse**: code edge ≠ experimental causation ≠ conceptual inspiration.

---

## Malbolge Primer (the parts we use)

| Concept | Meaning |
|---|---|
| `XLAT1` | `"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/\|t:Pn6^Ha"` — `inst = XLAT1[(mem[c]-33+c)%94]` |
| `XLAT2` | `"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8\|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"` — `mem[c] = XLAT2[mem[c]-33]` after each step |
| `crazy(a,mem[d])` | Tritwise op `t=[1,1,2,0,0,2,0,2,1]` over 10 trits `t[(a%3)*3+(b%3)]` |
| `rot(mem[d])` | `mem[d]/3 + (mem[d]%3)*19683` |
| `/` `<` `v` `p` `*` `j` `i` | `IN` `OUT` `HALT` `CRAZY` `ROT` `MOVD` `BRANCH` — only 8 ops, rest is `NOP` (`o`) |

Memory is 59049 words (3¹⁰). On load, `mem[i]=crazy(mem[i-1],mem[i-2])` for `i≥len(prog)`.

---

## Ladder M0 → M7

We build the frontend rung by rung, stopping at the first `NOT_DEMONSTRATED` (honest evidence before narrative). So far:

### M0 `RUNTIME_INPUT` — `ubO` `681f80..` ✅
Same program, 6 inputs (`A,B,C,X,Z,7`), same SHA-256. Proves the `.mal` actually reads stdin at runtime, not a hard-coded string.

### M1 `ECHO1` — `ubO` ✅
Same `ubO` echoes one char: `H→H, e→e …`. Verifies `IN→OUT` path.

### M2 `FIXED_TRANSFORM` — `u=aN` `2fb4e5..` ✅
`IN p < v` where `p` is `CRAZY` with `K=mem[1]=61`. For `X` → `crazy(X,61)%256`. Five inputs cross-checked `gost==oracle==expected` independent.

### M3 `POSITION_STATE` — `u=ar:^K` `e69fd6..` ✅
`IN p < IN p < v` with `K0=61` at pos1 and `K1=58` at pos4. The second `crazy` uses a **different constant** because the program counter moved — the "index `i`" is encoded in position, not in a mutable cell. Five input pairs verified.

### M4 `XLAT1_LOOKUP` — `program.mal` 103B `d3667e..` PARTIAL ✅
Goal: `c → XLAT1.index(c)` for 94 chars. Straight-line `IN (p|*)* < v` up to length 6 finds no `K` that maps `'/'→84` and `'<'→66` together (1092 seqs). But a **2-char subset is demonstrable**: `K=38 '&'` gives `crazy('%',38)=49` and `crazy('3',38)=64` (`XLAT1` 49 and 64). Program `BRANCH@0 → IN@99 p@100 <@101 v@102` with `prog[2]='&'` does `crazy(c,38)` and outputs the index. `oracle` 5 steps `halt_opcode` for both inputs, `gost` `1`/`@` (stripped `\r\n`).

> Full 94-entry lookup needs a **value-dependent branch** (`d = a+1` → `mem[d]` holds jump target) — the `IR→Malbolge` state-machine compiler, the hard sub-project (see `MALPAD/GATES.md` `M2`).

### M5 `SINGLE_CHAR` — `program.mal` 103B `c0ab6a..` ✅
Frontend computes the **first constant `K1` of its own print program**. For `'!'→54 '1'→62` the same `K=36 '$'` works: `crazy('!',36)=54` `crazy('1',36)=62`. Those `54,62` are the `K1` that make the print program for `'!'`/`'1'` print correctly (`0→'!'` via `(54,60)` etc.).

### M6 `STREAM` — `program.mal` 106B `7a272b..` ✅
Extends M5 to two chars: `"!1"→"6>"` (`54='6',62='>'`) via the same `K=36` at `d=2` and `d=5` (stream position state, like M3).

### M7 `FRONTEND` — `print_AB.mal` 106B `bcc6f3..` ✅ + compiler skeleton
- **Print program for `"AB"`**: `BRANCH@0` + `p@99(45) p@100(74) <@101` for `'A'` (`0→65`) + `p@102(34) p@103(33) <@104` for `'B'` (`65→66`) + `v`. Verified `output 'AB'` 8 steps on both `gost` and `oracle`.
- **Print program for `"Hi"`**: `0→72(33,72) 72→105(33,33,33)` — 107B, also verified `output 'Hi'`. Needs depth 3 for `'i'` (hence the compiler fallback to depth 3/4).
- **`compiler/ir.py`** — `lookup_print_steps(text)` brute-forces `(K1,K2,…)` per char via `crazy` (depth 2→4).
- **`compiler/codegen.py`** — `emit_print_program(text,steps)` places `K`'s at `d=1,2,4,5,…` and emits `p,p,<,p,p,<,v` correctly `enc`oded. The full `emit_frontend` (read text → emit `print_text.mal`) is the state-machine compiler that composes M4+M5+M6; its stub is in `codegen.py` and M4/M5/M6 are the demonstrated primitives it builds on.

```
Hi [(33, 72), (33, 33, 33)] len 107 verify 'Hi' ok=True
```

Next: close `emit_frontend` to read arbitrary input (e.g. `"Hi"`) and emit `print_Hi.mal` via `IN→crazy(K)→OUT` loop for each of the 107 output bytes — the quine `A+B=C` engine.

---

## Evidence Discipline

Every milestone keeps `program.mal`, `SHA256SUMS.txt`, and `evidence.json` with `compile_once_test_many: true` (same file re-hashed on every run). Example `M4/program.mal`:

```bash
Get-FileHash milestones/M4_XLAT1_LOOKUP/program.mal -Algorithm SHA256
# d3667e0a20251aa1b602bbb55bf42e1d3e57e0a6e4f9a8807199a086b3a7d9bc  program.mal
```

The reproducer is separate: `milestones/reproducer/reproducer.mal` `0b7700..` prints the Python source — `REPRODUCER_DEMONSTRATED`, `SEMANTIC_FRONTEND=NOT_CLAIMED`.

---

## Quickstart

```bash
# 1. Build interpreter
gcc -O2 -Wall -Wextra -std=c11 -o gost gost.c   # or py host.py compile

# 2. Generate an echo program (Python host, only encode)
py frontend/host.py gen --ops "/</v" -o /tmp/echo.mal
cat /tmp/echo.mal | od -An -tx1

# 3. Run it
echo -n "A" | ./gost /tmp/echo.mal        # → A  (gost)
py host.py verify /tmp/echo.mal --input A # → gost==oracle==engine

# 4. Run milestones
py run_milestone.py milestones/M0_RUNTIME_INPUT --inputs A B C
py test_gost.py -v                          # 10/10 cross-backend
py e2e.py                                   # 5/5

# 5. Use the compiler
py -c "from compiler.ir import lookup_print_steps; from compiler.codegen import emit_print_program; pp=lookup_print_steps('Hi'); print(emit_print_program('Hi', pp.steps))" > /tmp/print_Hi.mal
./gost /tmp/print_Hi.mal                    # → Hi
```

---

## Project Layout

```
gost.c                 # canonical Malbolge interpreter (standalone, GCC)
gost.exe               # built binary (gitignored)
frontend/host.py       # Python host: encode via XLAT1 congruence, no semantics
backend/host.py        # multi-backend verifier (gost/oracle/engine)
compiler/
  ir.py                # Text → [(K1,K2)] via crazy
  codegen.py           # → Malbolge print program + frontend stub
milestones/
  M0_RUNTIME_INPUT/    # ubO
  M1_ECHO1/
  M2_FIXED_TRANSFORM/  # u=aN
  M3_POSITION_STATE/   # u=ar:^K
  M4_XLAT1_LOOKUP/     # 103B  '%'/'3' K=38
  M5_SINGLE_CHAR/      # 103B  '!'/'1' K=36
  M6_STREAM/           # 106B  "!1"→"6>"
  M7_FRONTEND/         # print_AB.mal 106B + print_Hi 107B
  reproducer/          # text→Malbolge reproducer
e2e.py                 # frontend→gost→oracle
run_milestone.py       # COMPILE_ONCE harness
test_gost.py           # 10 cross-backend tests
```

---

## Development

```bash
# lint (if ruff installed)
ruff check .

# repo-engine health (no private paths, no secrets)
py ../ISyCo/tools/repo-engine/repo-engine.py analyze gost --format json

# add a milestone
mkdir milestones/M8_XXX && cp template/* milestones/M8_XXX/
```

`host.py` is only allowed to `open` files, pipe `stdin`, capture `stdout`, and invoke the runtime/oracle. It must not compute answers, choose outputs by input, or regenerate a `.mal` per input.

---

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Danny Baanks.

---

## References

- Iizawa 2005, Appendix C (Malbolge reference pseudocode) — source of `XLAT1`/`XLAT2`/`crazy`/`rot`
- `workspace/malbolge_toolkit` — compatible `malbolge` package shim for `Malbolge-Translator`
- `malbolge-oracle/oracle.py` — independent control, shares no ancestry with `gost`/`Malbolge-Engine`
- `MALPAD/evidence/m2_state/truth_machine.mal` — 2-way input branch primitive (verified 136 steps)
