# PARTE 0 — Contexto compartido

## 0.1 El reto en un párrafo
Hackathon NTT DATA × IBM Quantum. Instancia MIPLIB `qap10`: asignar 10 elementos a 10 ubicaciones minimizando
C(x) = Σ_{i<k} Σ_{j≠l} F_ik·D_jl·x_ij·x_kl (cada par una sola vez), con x una matriz de permutación. Óptimo de referencia **C* = 340**.
Debemos usar **Qiskit de forma sustantiva**, comparar contra una **línea base clásica**, reportar costo, factibilidad y tiempo
con honestidad (incluso cuando lo cuántico no ayuda) y hacer los resultados **reproducibles**. Día 1 (hoy, 10:00–17:00,
ventana de pitch 15:00–16:40): etapa 1 (N=3/4, opcionalmente N=10). Día 2 (finalistas): escalabilidad N ≥ 14.

Puntuación (NTT): modelo/datos/factibilidad 25 · relevancia y justificación de Qiskit 30 · calidad de la asignación vs clásico 20 ·
rigor (tiempo, límites, escalamiento) 15 · claridad y significado operativo 10. Rúbrica del evento adicional: innovación/validación 25,
Qiskit + claridad del pitch 25, rigor técnico/reproducibilidad 15, arquitectura 15. Track Quantum Hub: un entorno para
**representar, ejecutar, visualizar y comparar** soluciones clásicas vs cuánticas/híbridas.

## 0.2 Nuestro planteamiento (Track A)
10 **vuelos** de conexión → 10 **puertas**. F_ik = pasajeros que hacen transbordo entre los vuelos i y k.
D_jl = distancia a pie entre las puertas j y l. Objetivo: minimizar la distancia total caminada por los pasajeros.
**Las unidades son supuestos, no mediciones** (el reto exige decirlo explícitamente).

## 0.3 Hechos ya verificados (no volver a derivarlos)
- `data/qap10.mps.gz` tiene 100 variables de asignación `X001..X100` (x_ij = `X{10·(i−1)+j}`) y 4050 variables de
  linealización `Y…A…` cuyo coeficiente objetivo es F_ik·D_jl. Las entradas de una columna ocupan varias líneas del archivo.
- **F y D se recuperan de forma exacta.** D = distancia Manhattan sobre una **cuadrícula de 4 columnas con 10 celdas** (puertas 0–3 / 4–7 / 8–9),
  simétrica; cada bloque (i,k) de coeficientes es de rango 1 → F entera (valores 2…20, 29 de 45 pares distintos de cero,
  flujo total 228).
- **La fuerza bruta sobre 10! = 3 628 800 permutaciones toma 4.0 s** y devuelve **340**; permutación óptima
  `[2 6 3 0 8 4 5 1 7 9]` (vuelo i → puerta perm[i]). Óptimos de control: N=3 → **24**, N=4 → **32**.
- Líneas base ingenuas para la narrativa: asignación identidad = 454; asignación aleatoria con media ≈ 512 (mín. 372, máx. 654).
  El óptimo (340) implica **≈ 34 % menos caminata que una asignación aleatoria**.
- El stack de Qiskit funciona (Qiskit 2.6.1, qiskit-optimization 0.7.0, qiskit-algorithms 0.4.0, Aer 0.18):
  `QuadraticProgram` → `QuadraticProgramToQubo` → `to_ising` da N=3 → 9 qubits / 45 términos de Pauli,
  N=4 → 16 qubits / 112 términos. `MinimumEigenOptimizer(QAOA(...))` encontró 24 con N=3.
  **Trampa de velocidad:** el `StatevectorSampler/Estimator` de referencia tardó **87 s** con N=3 y nunca terminó con N=4.
  **El `EstimatorV2` de Aer evalúa un circuito QAOA de 16 qubits en ~0.07 s → usar siempre las primitivas de Aer.**
- Consecuencia (decirla en el pitch): el solver clásico exacto resuelve N=10 en 4 s, así que lo cuántico no ganará en velocidad.
  Nuestro valor es un modelo correcto, una comparación rigurosa, límites honestos y un producto claro.

## 0.4 Reglas del repositorio (todos)
- `main` está protegida por convención: **rama → commit → push de la rama → PR**. Nunca hagas push a `main`.
  Nombres de rama: `feat/data-…`, `feat/models-…`, `feat/story-…`. Un PR pequeño por porción de trabajo, revisado por un compañero
  (tiempo de revisión objetivo: < 10 min).
- **Un solo autor por archivo** (propiedad más abajo). Si necesitas un cambio en un archivo ajeno → avísale / abre un PR diminuto hacia esa persona.
- Mensajes de commit: oración en imperativo que describa el *porqué* (ver `git log`). Sin líneas de atribución de IA en commits/PR.
- Configuración: `uv sync`; ejecuta con `uv run …`. Nueva dependencia: `uv add <pkg>` y haz commit de `pyproject.toml` + `uv.lock`.
- Integridad (bases §11–12): cita las fuentes (MIPLIB, documentación de Qiskit, artículo de QAOA), anota qué se hizo con ayuda de IA y **cada
  integrante debe poder explicar cada parte de la solución** en el pitch.

## 0.5 Paso 0 — Contratos compartidos (primeros ~20 min; Rodrigo lo escribe, todos lo revisan)
Todo lo siguiente vive en `src/qap/` y queda **congelado tras el merge** (los cambios deben anunciarse al equipo).

```python
# src/qap/types.py
@dataclass(frozen=True)
class Instance:
    name: str; n: int
    F: np.ndarray      # (n,n) int, upper-triangular: F[i,k], i<k (flows); zeros elsewhere
    D: np.ndarray      # (n,n) int, symmetric, zero diagonal (distances)
    optimum: int | None
    @property
    def F_sym(self): return self.F + self.F.T

@dataclass
class Result:
    method: str                      # "bruteforce" | "sa" | "qaoa" | "hybrid_lns" | ...
    perm: tuple[int, ...] | None     # perm[i] = gate of flight i; None if no feasible solution found
    cost: int | None                 # TRUE cost of perm (never the penalized energy)
    feasible: bool
    seconds: float; peak_mem_mb: float; seed: int | None
    params: dict                     # everything needed to reproduce (reps, lambda, maxiter, shots, k, ...)
    extras: dict                     # penalized_energy, feasible_fraction, history, repaired, ...
```
- `cost(perm, inst)` = Σ_{i<k} F[i,k]·D[perm[i], perm[k]] — **la única fuente de verdad para la escala** (cada par una sola vez).
  Una versión vectorizada `costs(perms_2d, inst)` para muchas permutaciones.
- Firma del solver para cada método: `solve_xxx(inst: Instance, *, seed: int, **params) -> Result`.
- Convención de orden de variables para QUBO: `x_{i}_{j}` con nombre `f"x_{i}_{j}"`, índice aplanado `i*n + j`.
- Esquema del CSV de benchmark (`results/benchmark.csv`, lo genera `uv run python -m qap.benchmark`):
  `instance,n,method,config,seed,cost,feasible,optimal,gap_pct,gap_vs_control_pct,seconds,peak_mem_mb,shots,feasible_samples,optimal_samples,feasible_fraction,penalized_energy,params_json,source`.
  - `gap_pct = 100·(cost−340)/340` es **la brecha del reto: solo n=10 y solo filas válidas**.
  - `gap_vs_control_pct = 100·(cost−óptimo de control)/óptimo de control` es para n<10 (24, 32, …): **extensión nuestra**, no la
    brecha del reto.
  - `cost` (costo real) y `penalized_energy` (energía del QUBO) son columnas distintas.
  - El agregado por N × método × configuración está en `results/comparison.csv`.
- Stubs que lancen `NotImplementedError` para cada solver + `tests/` con los valores de control (24 / 32 / 340) marcados como las
  pruebas de aceptación que cada responsable debe poner en verde.
