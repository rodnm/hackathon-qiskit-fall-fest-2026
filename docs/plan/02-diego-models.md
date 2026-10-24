# PARTE 2 — Diego: MODELOS (QUBO/Ising, QAOA, descomposición híbrida)

**Eres responsable de:** `src/qap/model.py`, `quantum.py`, `tests/test_model.py`, `tests/test_quantum.py`, `notebooks/02_qiskit.ipynb`,
`docs/figures/lambda_*.png`, `docs/figures/qaoa_*.png`.
**Dependes de:** los contratos del Paso 0 + `load_instance` (T+0:45). Hasta entonces, escribe directamente en el código los primeros 4×4 de F y D desde el
README/notebook para comenzar el spike.
**Entregas:** veredicto del spike (T+0:30), `model.py` (T+1:00), QAOA N=3/4 (T+1:45), híbrido para N=10 (T+2:30).

### M1. Spike: ¿qué camino de QAOA? (0:00–0:30)
Pregunta: ¿`qiskit_algorithms.QAOA(sampler=<Aer SamplerV2>, …)` corre en pocos segundos para N=3 y N=4?
- Si sí → usa `MinimumEigenOptimizer(QAOA(...))` (menos código, lo más "Qiskit estándar").
- Si no → **alternativa (se sabe que funciona)**: `QAOAAnsatz(cost_operator=op, reps=p)` + `qiskit_aer.primitives.EstimatorV2`
  para la energía + `scipy.optimize.minimize(method="COBYLA")` sobre `(β, γ)`; luego muestrea el circuito final con Aer
  `SamplerV2` (requiere `measure_all`) y decodifica las cadenas de bits. Medido: 0.07 s por evaluación de energía con 16 qubits.
Nunca uses el `StatevectorSampler/Estimator` de referencia para N ≥ 4 (87 s para N=3).

### M2. Modelo — `model.py` (0:30–1:00)
- `build_qp(inst) -> QuadraticProgram`: variables binarias `x_{i}_{j}`; coeficientes cuadráticos del objetivo
  `F[i,k]·D[j,l]` para `i<k`, `j≠l`; restricciones de igualdad (cada suma de fila = 1, cada suma de columna = 1).
- `to_qubo(qp, lam) -> QuadraticProgram` mediante `QuadraticProgramToQubo(penalty=lam)`; `to_ising(qubo) -> (SparsePauliOp, offset)`.
  Relación (x = (1−Z)/2): `⟨op⟩ + offset` = energía QUBO penalizada.
- Funciones auxiliares: `decode(bitstring, n) -> perm | None` (None si no es una matriz de permutación), `is_feasible`,
  `true_cost(perm, inst)` (reutiliza `cost()`), `penalized_energy(x, qubo)`.
- **Trampa del orden de bits en Qiskit:** una cadena de bits medida es little-endian (el carácter más a la derecha = qubit 0). Inviértela antes de mapearla
  a `x_{i}_{j}` (índice `i*n+j`). Prueba esto de forma explícita.
- Reporta la **energía penalizada y el costo factible real como campos distintos** (`Result.extras`, lo exige el reto).

### M3. Pruebas del modelo — `tests/test_model.py`
- Para N=3 y N=4: enumera con numpy todas las cadenas de bits de 2^(N²) (512 / 65 536). Verifica con assert: (a) para cada permutación la energía
  QUBO es igual a `cost(perm)` (el término de penalización es cero en los puntos factibles); (b) para λ por encima del umbral, el argmin de
  la energía QUBO es una permutación óptima factible (costo 24 / 32).

### M4. Estudio de λ (1:00–1:30) — la justificación de la penalización
Umbral exacto, barato para N=3/4 (y N=5 por bloques): `λ* = max sobre x infactible de (C_opt − C(x)) / P(x)` donde
`P(x) = Σ_i(Σ_j x_ij − 1)² + Σ_j(Σ_i x_ij − 1)²`. Para λ > λ*, el estado fundamental del QUBO es factible y óptimo.
Elige `λ = 1.5–2 × λ*`; extrapola el orden de magnitud a N=10 (se esperan decenas). Grafica (`docs/figures/lambda_*.png`):
(1) λ* vs N, (2) para QAOA con N=3/4: fracción factible y mejor costo factible vs λ ∈ {0.5, 1, 2, 4}×λ*.
Mensaje: demasiado pequeño → el óptimo es infactible; demasiado grande → paisaje plano en el que QAOA tiene dificultades. Esto es lo que pregunta el jurado
("justifica su valor y comprueba la factibilidad").

### M5. QAOA completo en N pequeño — `quantum.py: solve_qaoa` (1:00–1:45)
- N=3 (9 qubits) y N=4 (16 qubits). N=5 (25 qubits) solo si hay tiempo y solo con una verificación de memoria en Aer MPS/statevector.
- Parámetros a registrar: `reps` ∈ {1, 2, 3}, optimizador COBYLA con `maxiter` ≈ 100–200, `shots` = 4096, `(β, γ)` iniciales pequeños
  y fijos por semilla, semillas 0–4.
- Métricas (ponlas en `Result.extras`): mejor costo **factible** entre las muestras, **fracción factible** de los shots,
  probabilidad de muestrear la permutación óptima, energía penalizada final, historial de iteraciones, tiempo.
  Compara con la fuerza bruta (24 / 32). Un QAOA que encuentra el óptimo con una fracción factible minúscula igualmente vale la pena reportarlo con honestidad.
- Datos del circuito para las diapositivas: qubits, profundidad, cantidad de compuertas de 2 qubits tras `transpile` (opcionalmente hacia un backend simulado).

### M6. Descomposición híbrida para N=10 (y N ≥ 14) — `quantum.py: solve_hybrid_lns` (1:45–2:30)
Búsqueda de vecindarios grandes (LNS) con un subsolver QAOA (es la propia sugerencia del reto: "subinstancias, fijar decisiones,
optimizar vecindarios, reconstruir una asignación completa").
```
start: p = best of a quick classical heuristic or a random permutation  (record which one; seed it)
repeat T times (T ≈ 30):
    S = k flights  (k=3 → 9 qubits, k=4 → 16 qubits); choose randomly, or a flight + its heaviest-flow partners
    G = {p[i] for i in S}                      # the gates those flights currently use
    sub-problem variables y[i,g], i∈S, g∈G, one-hot rows/cols (k×k)
    cost(y) = Σ_{i<m in S} F[i,m]·D[g,g']·y[i,g]·y[m,g']                      # interactions inside S
            + Σ_{i∈S, m∉S} F_sym[i,m]·D[g, p[m]]·y[i,g]                      # linear: interaction with fixed flights
    build QUBO with λ_sub, run QAOA (Aer), take best FEASIBLE sample → new p'
    accept if cost(p') < cost(p)             # always evaluate with the global cost()
```
- Ablación (importante para el jurado): resuelve los **mismos** subproblemas mediante enumeración exacta (k! ≤ 24 opciones). Se espera:
  QAOA, en el mejor caso, iguala ese resultado; el subproblema es demasiado pequeño para que lo cuántico aporte algo. Repórtalo tal cual.
- Registra por ejecución: costo final, brecha vs 340, número de vecindarios mejorados, fracción factible por subproblema, tiempo total.
- N ≥ 14: el mismo código sobre instancias sintéticas (de `make_synthetic` de Rodrigo), con k sin cambios.

### M7. Opcional (solo si todo lo anterior está en verde)
QAOA con arranque en caliente desde la mejor solución clásica; reparación clásica de muestras infactibles (**reporta por separado los resultados
originales y los reparados**); simulación con ruido mediante un modelo de ruido de Aer.

**Errores comunes:** no confundas la energía penalizada con el costo real; reevalúa siempre los candidatos con `cost()`; fija las semillas
(inicialización del optimizador, semilla del sampler, elección de vecindarios); mantén `reps` pequeño (la profundidad del circuito crece con el número de términos de Pauli).

**Tu criterio de terminado:** pruebas del modelo en verde; `solve_qaoa` N=3/4 reproduce 24/32 (o documenta por qué no); figuras de
λ con commit; resultados de `solve_hybrid_lns` N=10 en `results/benchmark.csv` con la ablación.
