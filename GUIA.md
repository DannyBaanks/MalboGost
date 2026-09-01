# GUIA — gost: motor Malbolge minimal

El motor más pequeño que ejecuta Malbolge completo. Compilado desde C,
verificado contra el oracle Python y Malbolge-Engine en 10 tests.

## El comando que viniste a buscar

```powershell
# Compilar (una vez)
gcc -O2 -Wall -Wextra -std=c11 -o gost.exe gost.c

# Ejecutar un programa
echo Hola | py gost.exe examples\echo1.mal 100000

# Verificación cross-backend (gost + oracle + engine)
py gost.py verify examples\echo1.mal --input "A"
```

## Regla de oro

gost.c es un intérprete Malbolge **estándar**. Usa las tablas XLAT1 (descifrado)
y XLAT2 (cifrado) del spec original. Los tres backends (gost, oracle, engine)
producen salida idéntica para el mismo programa.

## Cada comando, uno por uno

### 1. Compilar

```powershell
gcc -O2 -Wall -Wextra -std=c11 -o gost.exe gost.c
```

Salida esperada: ningún warning, `gost.exe` creado.

### 2. Ejecutar un programa

```powershell
echo Hola | py gost.exe examples\echo1.mal 100000
```

Salida:
```
Hola
steps=3 output=4 terminated=yes
```

El `\r\n` al final es un artifact de Windows text mode — el programa solo produce "Hola".

### 3. Verificación cross-backend

```powershell
py gost.py verify examples\echo1.mal --input "A"
```

Salida esperada:
```
Program: examples\echo1.mal
Input:   'A'

  gost       output=b'A\r\n' steps=3 terminated=True
  oracle     output=b'A' steps=? terminated=? 
  engine     output=b'A\r\n' steps=? terminated=?

  ALL BACKENDS AGREE
```

### 4. Generar programas de ejemplo

```powershell
py gen_examples.py
```

Crea `examples/nop.mal`, `echo1.mal`, `echo2.mal`, `echo3.mal`.

## Cómo leer la salida

| Campo | Significado |
|---|---|
| `steps=N` | Número de instrucciones ejecutadas |
| `output=M` | Bytes de salida producidos |
| `terminated=yes` | El programa hizo HALT |
| `terminated=no` | Timeout (pasos agotados) |
| Exit code 0 | Terminó con HALT |
| Exit code 3 | Timeout |

## Trampas

1. **gost.c es binario de Windows** — no funciona en Linux/macOS sin recompilar.
   En esos sistemas: `gcc -O2 -o gost gost.c`

2. **Input con PowerShell** — `echo Hola |` agrega `\r\n` al input.
   Para input limpio: `py -c "import subprocess; subprocess.run([r'gost.exe', ...], input=b'Hola')"`

3. **Oracle requiere >= 2 caracteres** — programas de 1 char (como NOP "Q")
   no se pueden verificar contra el oracle.

4. **Encoding** — Malbolge solo acepta ASCII imprimible (33-126).
   Caracteres fuera de rango son ignorados por el loader.

## Arquitectura

```
gost.c          Intérprete C standalone (~260 líneas)
  ├── crazy5    Tabla precomputada crazy (243×243)
  ├── XLAT1     Tabla de descifrado (index → instrucción)
  ├── XLAT2     Tabla de cifrado (post-ejecución)
  ├── overlay   Mapa para celdas fuente + escrituras
  └── chain     Relleno lazy crazy-chain para celdas no inicializadas

host.py         Orquestador Python (verificación cross-backend)
gen_examples.py Generador de ejemplos usando técnica de congruencias
test_gost.py    Suite de tests (10 tests, cross-backend)
```

## Generar programas Malbolge

La técnica de congruencias (de meowbolge): para programas straight-line,
cada posición i necesita opcode o. La fórmula:

```
mem[i] = (XLAT1.index(o) - i) % 94 + 33
```

Esto resuelve la congruencia `XLAT1[(mem[i] - 33 + i) % 94] = o` directamente,
sin búsqueda. Solo funciona para programas sin saltos.
