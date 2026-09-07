# MalboGost — Frontend Malbolge en Malbolge Puro

> **Un programa Malbolge que escribe programas Malbolge.** Python solo es el cable — la logica vive en `.mal` y se verifica en tres interpretes independientes.

### Por que "MalboGost"?

**MalboGost es el proyecto. `gost` es su runtime canonico de Malbolge.**

```
MalboGost/
├── gost.c          ← runtime (construido con GCC, standalone)
├── frontend.mal    ← frontend Malbolge
├── compiler/
├── milestones/
└── evidence/
```

`gost.c` es el interprete standalone de Malbolge en el nucleo — el *host* que corre el motor. El nombre es un guiño a *ghost* (Malbolge es famosamente embrujado) y al ruso *gost'* (huesped) — el host que hospeda la memoria de Malbolge `E=(I,X,O,S)`. El proyecto se llama **MalboGost** porque todo orbita ese binario: `frontend.mal` (Malbolge puro) + `gost` (C) + `oracle` (Python) — el mismo `.mal` corre en los tres y el host Python solo es el cable. Borra `frontend.mal` → el frontend desaparece; conserva `gost.c` → todavia puedes verificar todo.

[![CI](https://github.com/DannyBaanks/MalboGost/actions/workflows/ci.yml/badge.svg)](https://github.com/DannyBaanks/MalboGost/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MalboGost es un frontend de nivel investigacion: un solo archivo `.mal` (mas el mismo SHA-256 en todos los inputs) lee **input de runtime variable** y emite un **programa de impresion Malbolge** para ese input. El mismo frontend maneja muchos inputs (`COMPILE_ONCE_TEST_MANY`), y cada claim esta respaldado por evidencia hasheada y verificada en tres runtimes: `gost.c` (GCC/C, canonico), `malbolge-oracle` (referencia Python, Iizawa 2005), y `Malbolge-Engine`.

```bash
echo -n "Hi" | ./gost gost/frontend.mal  > print_Hi.mal   # frontend (Malbolge) genera
./gost print_Hi.mal                # programa de impresion (Malbolge) corre
# → Hi
```

---

## Por que Malbolge?

Malbolge es el lenguaje canonico "dificil de programar": cada instruccion esta cifrada con su posicion, la memoria se auto-modifica en cada paso, y solo 8 de los 94 caracteres imprimibles son ops reales. Escribir un **frontend self-hosting** en el es un stress-test para:

- decodificacion dependiente de posicion (`XLAT1[(mem[c]-33+c)%94]`)
- el operador ternario `crazy` y `rot`
- disciplina de evidencia `COMPILE_ONCE_TEST_MANY`

Este repo demuestra que se puede hacer — incrementalmente, con evidencia en cada peldaño.

---

## Arquitectura en 90 Segundos

```
texto input ──► frontend.mal (Malbolge) ──► print_<texto>.mal (Malbolge) ──► texto output
               ▲                         ▲
               │                         │
            gost.c                   gost.c
          (o oracle)              (o oracle)
```

- **Motor ≠ Host ≠ Puente** — la memoria de Malbolge `E=(I,X,O,S)` es el motor; `gost.c` es el host; `frontend/host.py` solo es el cable (abre archivo, pipe stdin, captura stdout). Borra `frontend.mal` → el frontend desaparece. Borra `backend.mal` → el backend desaparece.
- **Contrato congelado** `E=(I,X,O,S)`: stdin JSON, timeout 60s, ultima linea stdout JSON con `status/law_result`. Un runner que solo imprime `PASS` es un stub, no `GOLDEN`.
- **Tres genealogias nunca colapsan**: borde de codigo ≠ causacion experimental ≠ inspiracion conceptual.

---

## Manual Malbolge (las partes que usamos)

| Concepto | Significado |
|---|---|
| `XLAT1` | `"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/\|t:Pn6^Ha"` — `inst = XLAT1[(mem[c]-33+c)%94]` |
| `XLAT2` | `"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8\|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"` — `mem[c] = XLAT2[mem[c]-33]` despues de cada paso |
| `crazy(a,mem[d])` | Op por trit `t=[1,1,2,0,0,2,0,2,1]` sobre 10 trits `t[(a%3)*3+(b%3)]` |
| `rot(mem[d])` | `mem[d]/3 + (mem[d]%3)*19683` |
| `/` `<` `v` `p` `*` `j` `i` | `IN` `OUT` `HALT` `CRAZY` `ROT` `MOVD` `BRANCH` — solo 8 ops, lo demas es `NOP` (`o`) |

La memoria es de 59049 palabras (3^10). Al cargar, `mem[i]=crazy(mem[i-1],mem[i-2])` para `i>=len(prog)`.

---

## Escalera M0 → M7

Construimos el frontend peldaño por peldaño, parando en el primer `NOT_DEMONSTRATED` (evidencia honesta antes de narrativa). Hasta ahora:

### M0 `RUNTIME_INPUT` — `ubO` `681f80..` ✅
Mismo programa, 6 inputs (`A,B,C,X,Z,7`), mismo SHA-256. Demuestra que el `.mal` realmente lee stdin en runtime, no un string hardcodeado.

### M1 `ECHO1` — `ubO` ✅
Mismo `ubO` hace echo de un char: `H→H, e→e …`. Verifica la ruta `IN→OUT`.

### M2 `FIXED_TRANSFORM` — `u=aN` `2fb4e5..` ✅
`IN p < v` donde `p` es `CRAZY` con `K=mem[1]=61`. Para `X` → `crazy(X,61)%256`. Cinco inputs verificados `gost==oracle==expected` independientes.

### M3 `POSITION_STATE` — `u=ar:^K` `e69fd6..` ✅
`IN p < IN p < v` con `K0=61` en pos1 y `K1=58` en pos4. El segundo `crazy` usa una **constante diferente** porque el program counter se movio — el "indice `i`" esta codificado en posicion, no en una celda mutable. Cinco pares de inputs verificados.

### M4 `XLAT1_LOOKUP` — `program.mal` 103B `d3667e..` PARCIAL ✅
Objetivo: `c → XLAT1.index(c)` para 94 chars. Linea recta `IN (p|*)* < v` hasta longitud 6 no encuentra `K` que mapee `'/'→84` y `'<'→66` juntos (1092 seqs). Pero un **subconjunto de 2 chars es demostrable**: `K=38 '&'` da `crazy('%',38)=49` y `crazy('3',38)=64` (`XLAT1` 49 y 64). El programa `BRANCH@0 → IN@99 p@100 <@101 v@102` con `prog[2]='&'` hace `crazy(c,38)` y muestra el indice. `oracle` 5 pasos `halt_opcode` para ambos inputs, `gost` `1`/`@` (sin `\r\n`).

> La busqueda completa de 94 entradas necesita una **ramificacion dependiente de valor** (`d = a+1` → `mem[d]` contiene el target del salto) — el compilador de maquina de estados `IR→Malbolge`, el sub-proyecto dificil (ver `MALPAD/GATES.md` `M2`).

### M5 `SINGLE_CHAR` — `program.mal` 103B `c0ab6a..` ✅
El frontend calcula la **primera constante `K1` de su propio programa de impresion**. Para `'!'→54 '1'→62` el mismo `K=36 '$'` funciona: `crazy('!',36)=54` `crazy('1',36)=62`. Esos `54,62` son el `K1` que hace que el programa de impresion para `'!'`/`'1'` imprima correctamente (`0→'!'` via `(54,60)` etc.).

### M6 `STREAM` — `program.mal` 106B `7a272b..` ✅
Extiende M5 a dos chars: `"!1"→"6>"` (`54='6',62='>'`) via el mismo `K=36` en `d=2` y `d=5` (estado de posicion de stream, como M3).

### M7 `FRONTEND` — `print_AB.mal` 106B `bcc6f3..` ✅ + esqueleto del compilador
- **Programa de impresion para `"AB"`**: `BRANCH@0` + `p@99(45) p@100(74) <@101` para `'A'` (`0→65`) + `p@102(34) p@103(33) <@104` para `'B'` (`65→66`) + `v`. Verificado `output 'AB'` 8 pasos en `gost` y `oracle`.
- **Programa de impresion para `"Hi"`**: `0→72(33,72) 72→105(33,33,33)` — 107B, tambien verificado `output 'Hi'`. Necesita profundidad 3 para `'i'` (de ahi el fallback del compilador a profundidad 3/4).
- **`compiler/ir.py`** — `lookup_print_steps(text)` fuerza bruta `(K1,K2,…)` por caracter via `crazy` (profundidad 2→4).
- **`compiler/codegen.py`** — `emit_print_program(text,steps)` coloca los `K`'s en `d=1,2,4,5,…` y emite `p,p,<,p,p,<,v` correctamente codificado. El `emit_frontend` completo (lee texto → emite `print_text.mal`) es el compilador de maquina de estados que compone M4+M5+M6; su stub esta en `codegen.py` y M4/M5/M6 son las primitivas demostradas en las que se construye.

```
Hi [(33, 72), (33, 33, 33)] len 107 verify 'Hi' ok=True
```

Siguiente: cerrar `emit_frontend` para leer input arbitrario (ej. `"Hi"`) y emitir `print_Hi.mal` via el loop `IN→crazy(K)→OUT` para cada uno de los 107 bytes de salida — el motor quine `A+B=C`.

---

## Disciplina de Evidencia

Cada hito conserva `program.mal`, `SHA256SUMS.txt`, y `evidence.json` con `compile_once_test_many: true` (mismo archivo re-hasheado en cada corrida). Ejemplo `M4/program.mal`:

```bash
Get-FileHash milestones/M4_XLAT1_LOOKUP/program.mal -Algorithm SHA256
# d3667e0a20251aa1b602bbb55bf42e1d3e57e0a6e4f9a8807199a086b3a7d9bc  program.mal
```

El reproductor esta por separado: `milestones/reproducer/reproducer.mal` `0b7700..` imprime el fuente Python — `REPRODUCER_DEMONSTRATED`, `SEMANTIC_FRONTEND=NOT_CLAIMED`.

---

## Inicio Rapido

```bash
# 1. Construir interprete
gcc -O2 -Wall -Wextra -std=c11 -o gost gost.c   # o py host.py compile

# 2. Generar un programa echo (host Python, solo codifica)
py frontend/host.py gen --ops "/</v" -o /tmp/echo.mal
cat /tmp/echo.mal | od -An -tx1

# 3. Correrlo
echo -n "A" | ./gost /tmp/echo.mal        # → A  (gost)
py host.py verify /tmp/echo.mal --input A # → gost==oracle==engine

# 4. Correr hitos
py run_milestone.py milestones/M0_RUNTIME_INPUT --inputs A B C
py test_gost.py -v                          # 10/10 cross-backend
py e2e.py                                   # 5/5

# 5. Usar el compilador
py -c "from compiler.ir import lookup_print_steps; from compiler.codegen import emit_print_program; pp=lookup_print_steps('Hi'); print(emit_print_program('Hi', pp.steps))" > /tmp/print_Hi.mal
./gost /tmp/print_Hi.mal                    # → Hi
```

---

## Layout del Proyecto

```
gost.c                 # interprete canonico de Malbolge (standalone, GCC)
gost.exe               # binario construido (gitignored)
frontend/host.py       # host Python: codifica via congruencia XLAT1, sin semanticas
backend/host.py        # verificador multi-backend (gost/oracle/engine)
compiler/
  ir.py                # Texto → [(K1,K2)] via crazy
  codegen.py           # → programa de impresion Malbolge + stub del frontend
milestones/
  M0_RUNTIME_INPUT/    # ubO
  M1_ECHO1/
  M2_FIXED_TRANSFORM/  # u=aN
  M3_POSITION_STATE/   # u=ar:^K
  M4_XLAT1_LOOKUP/     # 103B  '%'/'3' K=38
  M5_SINGLE_CHAR/      # 103B  '!'/'1' K=36
  M6_STREAM/           # 106B  "!1"→"6>"
  M7_FRONTEND/         # print_AB.mal 106B + print_Hi 107B
  reproducer/          # texto→Malbolge reproductor
e2e.py                 # frontend→gost→oracle
run_milestone.py       # harness COMPILE_ONCE
test_gost.py           # 10 pruebas cross-backend
```

---

## Desarrollo

```bash
# lint (si ruff esta instalado)
ruff check .

# repo-engine health (sin rutas privadas, sin secretos)
py ../ISyCo/tools/repo-engine/repo-engine.py analyze gost --format json

# agregar un hito
mkdir milestones/M8_XXX && cp template/* milestones/M8_XXX/
```

A `host.py` solo se le permite `open` archivos, pipe `stdin`, capturar `stdout`, e invocar el runtime/oraculo. No debe calcular respuestas, elegir outputs por input, ni regenerar un `.mal` por input.

---

## Licencia

MIT — ver [LICENSE](LICENSE). Copyright (c) 2026 Danny Baanks.

---

## Referencias

- Iizawa 2005, Appendix C (pseudocodigo de referencia de Malbolge) — fuente de `XLAT1`/`XLAT2`/`crazy`/`rot`
- `workspace/malbolge_toolkit` — shim de paquete `malbolge` compatible para `Malbolge-Translator`
- `malbolge-oracle/oracle.py` — control independiente, no comparte ascendencia con `gost`/`Malbolge-Engine`
- `MALPAD/evidence/m2_state/truth_machine.mal` — primitiva de ramificacion de input de 2 vias (verificada 136 pasos)
