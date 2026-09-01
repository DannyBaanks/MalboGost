# GOST — Malbolge Frontend via Pure Malbolge

A Malbolge frontend written in **pure Malbolge** that transforms variable runtime input. Python is only the host/cable and verifier — the logic lives in `.mal`.

> `COMPILE_ONCE_TEST_MANY` — same `.mal` and same SHA-256 for many inputs.

## Milestones M0 → M7

| Hito | Programa | SHA256 | Qué hace |
|---|---|---|---|
| M0 `RUNTIME_INPUT` | `ubO` | `681f80..` | Lee input en runtime (no hardcodeado) |
| M1 `ECHO1` | `ubO` | `681f80..` | Echo 1 char |
| M2 `FIXED_TRANSFORM` | `u=aN` | `2fb4e5..` | `crazy(X,61)%256` — transform no-identidad |
| M3 `POSITION_STATE` | `u=ar:^K` | `e69fd6..` | `i=0 →61, i=1 →58` — estado entre chars |
| M4 `XLAT1_LOOKUP` | `program.mal` 103B | `d3667e..` | `'%'→'1'(49) '3'→'@'(64)` `K=38` `crazy(c,38)` |
| M5 `SINGLE_CHAR` | `program.mal` 103B | `c0ab6a..` | `'!'→54 '1'→62` `K=36` — K1 del print-program |
| M6 `STREAM` | `program.mal` 106B | `7a272b..` | `"!1"→"6>"` stream 2-char |
| M7 `FRONTEND` | `print_AB.mal` 106B | `bcc6f3..` | Print `"AB"` sin input: `0→65(45,74) 65→66(34,33)` |
| `reproducer` | `reproducer.mal` 2KB | `0b7700..` | Imprime el Python fuente (texto→Malbolge) |

Verificado con `gost.exe` (GCC/C), `malbolge-oracle` (Python) y `Malbolge-Engine` — 5/5 `e2e.py` PASS.

## Compiler

- `compiler/ir.py` — `lookup_print_steps(text)` encuentra `(K1,K2,...)` vía `crazy` para cada char (depth 2/3/4)
- `compiler/codegen.py` — `emit_print_program(text, steps)` genera el Malbolge print-program; `emit_frontend` es el dispatch `IN→crazy(K)→OUT`

Ejemplo:
```bash
py compiler/codegen.py
# A [(45, 74)] len 103 verify 'A' ok=True
# AB [(45, 74), (34, 33)] len 106 verify 'AB' ok=True
# Hi [(33, 72), (33, 33, 33)] len 107 verify 'Hi' ok=True
```

## Uso

```bash
# Generar echo con Python (solo host)
py frontend/host.py gen --ops "/</v" -o out.mal

# Verificar milestone M0
py run_milestone.py milestones/M0_RUNTIME_INPUT --inputs A B C

# Run via gost
./gost.exe milestones/M0_RUNTIME_INPUT/program.mal <<< "A"

# E2E
py e2e.py
```

## Estructura

```
gost.c            # intérprete canónico Malbolge (GCC)
gost.exe          # binario
frontend/host.py  # host Python (solo encode, no lógica)
backend/host.py   # verificador
compiler/         # IR → Malbolge
milestones/       # M0..M7 + reproducer
e2e.py            # pipeline frontend→gost→oracle
```

## Verificación

```bash
py test_gost.py        # 10/10 cross-backend
py e2e.py              # 5/5
py tools/repo-engine/repo-engine.py analyze gost  # CLEAN
```

`host.py` solo abre archivos, pasa stdin, captura stdout e invoca el runtime. Si borras `frontend.mal`, el frontend deja de existir.

---
*Research demo — evidencias en `milestones/*/evidence.json` con SHA256.*
