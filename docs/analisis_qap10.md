# Análisis de la instancia `qap10.mps`

Fecha: 2026-10-24  
Fichero analizado: `data/qap10.mps/qap10.mps`  
Script reproducible: `uv run python src/analyze_qap10.py --solve`

> **Aviso de ruta:** `data/qap10.mps` es un **directorio**, no un fichero. El MPS real está en
> `data/qap10.mps/qap10.mps`. La copia `data/qap10.mps.gz` se descomprime byte a byte al mismo
> contenido (SHA-256 `a317ab99d08ad4d4b5cb8286a8a1c4c4f77ad801ff3f8b50d565390219485789`).

## 1. Resumen ejecutivo

- Es un **QAP (Quadratic Assignment Problem)** de 10 instalaciones × 10 localizaciones,
  formulado como **MILP linealizado**, no como QUBO.
- Contiene **4.150 variables enteras**: 100 variables de asignación `X` y 4.050 variables
  producto `Y`.
- Contiene **1.820 restricciones de igualdad** (20 de asignación + 1.800 de linealización)
  más 1 fila objetivo. Matriz muy dispersa: 22.250 no ceros (0,294 %).
- La formulación se reduce al QAP clásico
  `min Σ_{i<k} F[i,k] · D[π(i),π(k)]`, con matrices `F` y `D` reconstruidas exactamente
  (error de factorización 0).
- **Óptimo verificado: 340**, con **asignación óptima única**
  `π = (3, 7, 4, 1, 9, 5, 6, 2, 8, 10)` (instalación 1→localización 3, etc.).
- El paisaje de las 10! = 3.628.800 asignaciones es muy selectivo: media 511,73,
  desviación 39,18, máximo 666; solo **19 permutaciones** tienen coste ≤ 360 y solo
  **5.392** (0,15 %) tienen coste ≤ 400.
- Para una implementación cuántica conviene usar **solo las 100 variables X**; las 4.050 `Y`
  son un artefacto de la linealización clásica.

## 2. Formato y estructura del MPS

| Elemento | Valor |
|---|---:|
| Tamaño | 675.639 bytes |
| Líneas | 24.098 |
| Filas totales | 1.821 (1 `N` + 1.820 `E`) |
| Columnas | 4.150 (100 `X` + 4.050 `Y`) |
| No ceros | 22.250 |
| Densidad | 0,2944 % |
| RHS | todos 1,0 |
| Secciones | `NAME`, `ROWS`, `COLUMNS`, `RHS`, `ENDATA` |
| `BOUNDS` / `RANGES` | ausentes |
| Marcador entero | `INTORG` / `INTEND` (todas las variables) |
| Sentido | minimización (por defecto; no hay `OBJSENSE`) |

No hay sección `BOUNDS`: las variables son enteras con cota inferior 0 y sin cota superior
explícita. En soluciones factibles, las restricciones de asignación y las igualdades de
linealización fuerzan `X ∈ {0,1}` e `Y ∈ {0,1}`. Si se carga el MPS en un solver genérico,
conviene añadir explícitamente cotas `[0,1]` y tipo binario.

### 2.1 Filas

| Bloque | Nº | Significado |
|---|---:|---|
| `NOBJ` | 1 | Fila objetivo (solo coeficientes de `Y`) |
| `NX01`–`NX10` | 10 | Cada instalación se asigna a exactamente una localización |
| `NX11`–`NX20` | 10 | Cada localización recibe exactamente una instalación |
| `C01A001`–`C18A100` | 1.800 | 18 igualdades de linealización por cada `X_t` (t = 1..100) |

Las 20 primeras restricciones son:

```text
Σ_j X[i,j] = 1     para i = 1..10    (NX01..NX10)
Σ_i X[i,j] = 1     para j = 1..10    (NX11..NX20)
```

Cada fila `C**A t` tiene exactamente 10 no ceros: `-1 · X_t` y `+1 · Y` para 9 variables `Y`.
Es decir, son igualdades del tipo `Σ_{9 Y} Y = X_t`.

### 2.2 Columnas y variables

- **`X001`…`X100`**: 100 variables de asignación. Codificación
  `t = 10·(i-1) + j` → `X_t = x_{i,j}` (instalación `i`, localización `j`, ambas 1-based).
  Cada `X` aparece en 20 filas: 2 de asignación (`NX`) y 18 `C`.
- **`Y001A001`…`Y081A090`**: 4.050 variables producto. Cada una aparece en 5 filas:
  4 filas `C` y la fila objetivo. No hay variables `Y` con la misma instalación o la misma
  localización.
- Cada `Y` está asociada a **exactamente dos variables `X`** distintas, con instalaciones y
  localizaciones diferentes. El número total es:

```text
C(10,2) pares de instalaciones × 10·9 pares ordenados de localizaciones
= 45 × 90 = 4.050
```

- De las 4.050 `Y`, **2.610 tienen coeficiente objetivo no nulo** y **1.440 tienen coeficiente 0**.
  Las 100 `X` no aparecen en el objetivo.

## 3. Reconstrucción del QAP subyacente

Para cada `Y` se identifican sus dos `X` asociadas a partir de las filas `C`. Eso permite
reconstruir la matriz de coeficientes cuadráticos `Q[i,k,j,l]`, que resulta factorizar
exactamente como:

```text
Q[i,k,j,l] = F[i,k] · D[j,l]
```

con error máximo 0. `F` es la matriz de flujos (simétrica, sin diagonal) y `D` la matriz de
distancias (simétrica, sin diagonal). El objetivo es:

```text
min  Σ_{i<k} F[i,k] · D[π(i), π(k)]
```

donde `π(i)` es la localización asignada a la instalación `i`.

### 3.1 Matriz de flujos `F`

```text
      1   2   3   4   5   6   7   8   9  10
1     0  10   4   8   2   0   0  12   4   2
2    10   0   6   0   4   4   4   0   8  10
3     4   6   0   0   0   0   0  10  10   4
4     8   0   0   0  10   4   4  20   0   0
5     2   4   0  10   0  20   0   0   0  10
6     0   4   0   4  20   0  10   2   2  10
7     0   4   0   4   0  10   0  20  10   4
8    12   0  10  20   0   2  20   0   0   0
9     4   8  10   0   0   2  10   0   0   0
10    2  10   4   0  10  10   4   0   0   0
```

- 29 de los 45 pares posibles tienen flujo no nulo (64,4 %).
- Valores: `{2, 4, 6, 8, 10, 12, 20}`; flujo máximo 20.
- Flujo total (pares no ordenados): 228.
- Grados de flujo por instalación: `[42, 46, 34, 46, 46, 52, 52, 64, 34, 40]`.
  La instalación 8 es la más conectada y la 3 y la 9 las menos conectadas.

### 3.2 Matriz de distancias `D`

```text
      1  2  3  4  5  6  7  8  9 10
1     0  1  2  3  1  2  3  4  2  3
2     1  0  1  2  2  1  2  3  3  2
3     2  1  0  1  3  2  1  2  4  3
4     3  2  1  0  4  3  2  1  5  4
5     1  2  3  4  0  1  2  3  1  2
6     2  1  2  3  1  0  1  2  2  1
7     3  2  1  2  2  1  0  1  3  2
8     4  3  2  1  3  2  1  0  4  3
9     2  3  4  5  1  2  3  4  0  1
10    3  2  3  4  2  1  2  3  1  0
```

`D` es una **distancia Manhattan** sobre una rejilla de 4 columnas × 3 filas, de la que solo
se usan 10 celdas:

```text
localización : (columna, fila)
1  (0,0)   2  (1,0)   3  (2,0)   4  (3,0)
5  (0,1)   6  (1,1)   7  (2,1)   8  (3,1)
9  (0,2)  10  (1,2)
```

Las celdas `(2,2)` y `(3,2)` de la rejilla 4×3 no se usan. Las distancias toman valores
`{1,2,3,4,5}`; la máxima es 5 (localizaciones 4 y 9).

## 4. Solución óptima y paisaje de búsqueda

Enumerando exhaustivamente las 3.628.800 permutaciones:

| Métrica | Valor |
|---|---:|
| Óptimo | **340** |
| Nº de óptimos | **1** (único) |
| Asignación óptima | `π = (3, 7, 4, 1, 9, 5, 6, 2, 8, 10)` |
| Coste máximo | 666 |
| Media | 511,73 |
| Mediana | 512 |
| Desviación típica | 39,18 |

La asignación inversa (localización → instalación) es
`(4, 8, 1, 3, 6, 7, 2, 9, 5, 10)`.

Las 10 variables `X` activas en el óptimo son:

```text
X(1,3) X(2,7) X(3,4) X(4,1) X(5,9) X(6,5) X(7,6) X(8,2) X(9,8) X(10,10)
```

Al sustituir en el MPS, las 45 `Y` correspondientes se activan y la suma directa de sus
coeficientes objetivo da exactamente **340**, lo que confirma que la reconstrucción y el
valor de referencia del reto coinciden.

### 4.1 Distribución del objetivo

| Rango | Nº permutaciones | Porcentaje |
|---|---:|---:|
| [340, 360) | 12 | 0,0003 % |
| [360, 380) | 361 | 0,010 % |
| [380, 400) | 4.077 | 0,112 % |
| [400, 420) | 24.353 | 0,671 % |
| [420, 440) | 87.188 | 2,402 % |
| [440, 460) | 217.864 | 6,003 % |
| [460, 480) | 414.292 | 11,414 % |
| [480, 500) | 613.181 | 16,895 % |
| [500, 520) | 713.398 | 19,656 % |
| [520, 540) | 654.804 | 18,044 % |
| [540, 560) | 475.748 | 13,109 % |
| [560, 580) | 268.618 | 7,402 % |
| [580, 600) | 114.287 | 3,149 % |
| [600, 620) | 33.966 | 0,936 % |
| [620, 640) | 6.107 | 0,168 % |
| [640, 660) | 525 | 0,014 % |
| [660, 666] | 19 | 0,0005 % |

Percentiles: 1 % = 422, 5 % = 446, 25 % = 484, 50 % = 512, 75 % = 538, 95 % = 576,
99 % = 600.

### 4.2 Rugosidad / dificultad

- Solo **19** permutaciones tienen coste ≤ 360 y **5.392** (0,149 %) ≤ 400. El óptimo está
  muy aislado en la cola izquierda de la distribución.
- No existe ninguna permutación a distancia Hamming 1 del óptimo (obviamente, una sola
  posición cambiada no es una permutación). Las mejores vecinas están a distancia 2
  (coste mínimo 346).
- La correlación entre el coste y la distancia Hamming al óptimo es muy baja
  (**0,066**): el objetivo no actúa como una guía suave hacia el óptimo. Es un paisaje
  rugoso, con muchos óptimos locales.
- En una muestra aleatoria de 30.000 permutaciones, solo 4 (≈0,013 %) eran mínimos locales
  bajo intercambio de dos posiciones; el mejor de ellos tenía coste 376. Es una estimación
  indicativa, pero coherente con un paisaje con pocos valles y separados del óptimo.

## 5. Implicaciones para la parte cuántica

1. **No linealizar el QAP en 4.150 variables para el circuito.** La formulación MPS es útil
   para un solver MILP clásico, pero para Qiskit conviene usar directamente las 100 variables
   binarias `x[i,j]` y el objetivo cuadrático `F[i,k]·D[j,l]`.
2. **Restricciones one-hot.** Hay que imponer `Σ_j x[i,j] = 1` y `Σ_i x[i,j] = 1`. En un
   QUBO se añaden como penalizaciones. Una cota segura y sencilla es una penalización
   `M > 666` (rango máximo del objetivo), por ejemplo `M = 1000`, para que ninguna solución
   no factible compita con el óptimo factible 340.
3. **Tamaño cuántico.** 100 qubits codifican el problema, frente a 10! ≈ 3,63 M soluciones
   factibles. Un QAOA directo a 100 qubits es ambicioso; para el hackathon es razonable
   combinarlo con reparación/refinamiento clásico, descomposición o un muestreo de baja
   profundidad.
4. **Baseline clásico exacto.** La enumeración de 10! tarda segundos en Python/NumPy y da el
   óptimo 340. Por tanto, el baseline clásico puede ser **exacto**, no una heurística; la
   comparación cuántica debería reportar gap respecto a 340, no solo frente a una solución
   aleatoria (cuya media es ≈512).
5. **Estructura aprovechable.** `F` solo tiene 29/45 pares no nulos y `D` es Manhattan entera
   pequeña. El QUBO resultante tiene interacciones únicamente entre asignaciones de
   instalaciones distintas y localizaciones distintas; no hay términos `x[i,j]·x[i,l]` ni
   `x[i,j]·x[k,j]` (esos pares ya los controlan las restricciones one-hot).

Ejemplo de formulación con Qiskit Optimization:

```python
from qiskit_optimization import QuadraticProgram

qp = QuadraticProgram("qap10")
x = {(i, j): qp.binary_var(f"x_{i}_{j}") for i in range(10) for j in range(10)}

for i in range(10):
    qp.linear_constraint({x[i, j]: 1 for j in range(10)}, "==", 1, f"fac_{i}")
for j in range(10):
    qp.linear_constraint({x[i, j]: 1 for i in range(10)}, "==", 1, f"loc_{j}")

quadratic = {}
for i in range(10):
    for k in range(i + 1, 10):
        for j in range(10):
            for l in range(10):
                if j != l and F[i, k]:
                    quadratic[(f"x_{i}_{j}", f"x_{k}_{l}")] = F[i, k] * D[j, l]

qp.minimize(quadratic=quadratic)
qubo = qp.to_qubo(penalty=1000.0)
```

## 6. Comprobaciones de integridad realizadas

- Todas las filas `E` tienen exactamente 10 no ceros; la fila `NOBJ` tiene 4.050.
- Las 100 columnas `X` tienen 20 no ceros; las 4.050 columnas `Y` tienen 5.
- Todos los RHS valen 1.
- Cada `Y` enlaza exactamente 2 variables `X` distintas y el conjunto de 4.050 pares
  coincide exactamente con todas las combinaciones de instalaciones distintas y
  localizaciones distintas.
- `Q = F·D` con error máximo 0; `F` y `D` son simétricas.
- El MPS original y el `.gz` descomprimido son idénticos (mismo SHA-256).
- La suma directa del objetivo MPS en la asignación óptima da 340, igual que el valor de
  referencia del reto y de MIPLIB.
