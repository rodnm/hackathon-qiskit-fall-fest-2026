# Plan general original (Track A): asignación de puertas de embarque sobre QAP10 — clásico vs Qiskit

> **Documento histórico.** Es la primera versión del plan, antes de dividirlo por persona. Los planes vigentes son
> `00-shared.md` a `04-calendar-and-decisions.md`. Cambios posteriores a esta versión:
>
> - Roles con nombre: Rodrigo = Datos, Diego = Modelos, Felipe = Producto y narrativa.
> - La app de Felipe sigue su propuesta GateFlow Quantum (React + FastAPI + Docker Compose), no Streamlit.
> - El calendario pasó a horas reales (congelamiento de código 14:45, ventana de pitch 15:00–16:40).
> - El EDA (`notebooks/01_data.ipynb`, `docs/eda.md`) separó el **gap** del reto, 100·(C − 340)/340 solo sobre soluciones
>   válidas, del **ahorro frente al azar** (34 %) que usa la narrativa.
> - La fuerza bruta para N=10 toma ~5 s cuando además se mide la memoria con `tracemalloc` (4,0 s sin medirla).

## Contexto

Hackathon NTT DATA × IBM Quantum. Día 1 hoy (10:00–17:00, ventana de pitch 15:00–16:40); día 2 para finalistas
(08:30–13:00). El repositorio y el entorno uv/Qiskit 2.6.1 ya están en `main` (PR #1); `src/`, `tests/` y `notebooks/` están vacíos.
Equipo: **3 personas** (las bases mencionan 4; preguntar a los organizadores si 3 es aceptable).

Reto (`reto-ntt-data/Reto_NTT_DATA.pdf`): MIPLIB `qap10`, 10 elementos → 10 ubicaciones, óptimo de referencia
C* = 340, cada par de flujo se cuenta una sola vez. Se necesita: uso sustantivo de Qiskit, línea base clásica, comparación honesta
y reproducibilidad. Puntuación: modelo/datos/factibilidad 25 · pertinencia de Qiskit 30 · calidad de la asignación vs clásico 20 ·
rigor/tiempo/límites/escalamiento 15 · claridad y sentido operativo 10. La rúbrica común añade: innovación/validación 25,
Qiskit y claridad del pitch 25, rigor técnico/reproducibilidad 15, arquitectura 15; el track de Quantum Hub además pide un entorno
para representar un problema, ejecutar enfoques clásicos vs cuánticos/híbridos, y **visualizar y comparar**.

**Planteamiento Track A (decidido):** 10 vuelos de conexión → 10 puertas. F_ik = pasajeros que hacen transbordo entre los vuelos
i y k; D_jl = distancia a pie entre las puertas j y l; minimizar la distancia total caminada por los pasajeros. Las unidades son
supuestos, no mediciones (el reto exige decirlo).

## Hechos verificados (comprobaciones de solo lectura ya hechas; no volver a derivarlos)

- `data/qap10.mps.gz`: 100 variables `X` de asignación (x_ij = columna `X{10(i-1)+j}`) + 4050 variables `Y` de linealización
  (Adams–Johnson: `Y*A*` = x_ij·x_kl para i<k, j≠l) con coeficiente objetivo = F_ik·D_jl. 1820 filas de igualdad.
  Las columnas ocupan varias líneas del archivo → agregar las entradas por nombre de columna al parsear.
- Decodificar una columna `Y`: sus filas de restricción `C..A{a}` y `C..A{b}` nombran las dos variables X (a<b), con índice
  a−1 = 10·i+j (base 0). Luego `P[i,k,j,l] = coeficiente`.
- **F y D se recuperan de forma exacta:** `D = P[0,1] / mcd` da una D simétrica = distancia Manhattan sobre una **cuadrícula de
  4 columnas con 10 celdas** (puertas 0–3 / 4–7 / 8–9); cada bloque (i,k) es de rango 1 → F entera (flujos de 2 a 20, 29 de 45 pares
  distintos de cero, total 228; el factor de escala 10 queda absorbido en F).
- **La fuerza bruta valida la escala:** N=3 → 24, N=4 → 32, N=10 → **340** en 4,0 s (numpy vectorizado, bloques
  de 200 000 permutaciones; permutación óptima `[2 6 3 0 8 4 5 1 7 9]`).
- Números para la narrativa operativa: costo de la asignación identidad 454; media de una asignación aleatoria ≈ 512 (mín. 372,
  máx. 654); el óptimo 340 implica **≈ 34 % menos caminata que una asignación aleatoria**.
- Prueba rápida de Qiskit (Qiskit 2.6.1, qiskit-algorithms 0.4.0, qiskit-optimization 0.7.0, Aer 0.18):
  - QUBO vía `QuadraticProgramToQubo` → `to_ising`: N=3 → 9 qubits / 45 términos de Pauli; N=4 → 16 qubits / 112 términos.
  - `MinimumEigenOptimizer(QAOA(StatevectorSampler, COBYLA(40), reps=1))` en N=3 **funciona y encuentra 24**,
    pero tarda **87 s** (el `StatevectorSampler/Estimator` de referencia es demasiado lento; con N=4 no terminó).
  - **El `EstimatorV2` de Aer evalúa un circuito QAOA de 16 qubits en ~0,07 s** → usar primitivas de Aer en todo momento.
- Implicación: el solver clásico exacto resuelve N=10 en 4 s. Lo cuántico no ganará en velocidad; el valor del proyecto
  es un modelo correcto, una comparación rigurosa y límites honestos (exactamente lo que premia la rúbrica).

## Roles (3 personas)

| Persona | Rol | Es dueño de |
|---|---|---|
| **Datos** (Rodrigo) | Exploración de datos, carga de la instancia, líneas base clásicas, benchmark | `src/qap/data.py`, `classical.py`, `benchmark.py`, `tests/test_data.py`, `notebooks/01_data.ipynb` |
| **Modelos** (Diego) | QUBO/Ising, QAOA, descomposición híbrida, estudio de λ | `src/qap/model.py`, `quantum.py`, `tests/test_model.py`, `notebooks/02_qiskit.ipynb` |
| **Narrativa** (Felipe) | Narrativa del Track A, app Streamlit, PPT, pitch, video de demo, entrega | `src/app.py`, `docs/`, sección de resultados del README |

Un solo autor por archivo; un PR pequeño por porción de trabajo (rama → commit → PR). La interfaz compartida se acuerda en el
Paso 0 para que todos puedan trabajar en paralelo.

## Paso 0 — Contratos (primeros ~20 min, un PR de la persona de Datos)

Esqueleto en `src/qap/` para que nadie bloquee a nadie:

- Dataclass `Instance`: `name, n, F (n×n, enteros, triangular superior), D (n×n, enteros, simétrica), optimum | None`.
- Dataclass `Result`: `method, perm, cost, feasible, seconds, peak_mem_mb, seed, params (dict), extras (dict)`
  (extras: energía penalizada, fracción factible, historial de iteraciones, indicador de reparación).
- `cost(perm, instance)` = Σ_{i<k} F_ik·D_{p(i)p(k)} — fuente única de verdad para la escala (cada par una sola vez).
- Stubs: `load_instance(n)`, `solve_bruteforce`, `solve_sa`, `solve_qaoa`, `solve_hybrid_lns`, todos devuelven `Result`.
- `tests/` con los valores de control (24, 32, 340) como tests de aceptación.

## Etapa 1 — Datos y modelo (persona de Datos; 25 pts)

1. `data.py`: parser del MPS (gzip + texto, agregando por columna), construir `P[i,k,j,l]`, factorizar en F y D,
   `load_instance(n)` = primeras n filas/columnas. Guardar F y D recuperados en `data/qap10_FD.npz` (+ CSV) para que los demás
   no tengan que parsear.
2. Documentar la recuperación (celda en `notebooks/01_data.ipynb` y README): de dónde salen los coeficientes, la
   verificación de rango 1, la escala por mcd y el control 24/32/340 — es el requisito "explica cómo recuperaste…".
3. Exploración para la narrativa: mapa de calor de flujos, pares con mayor flujo (hubs: los vuelos 3, 7 y 4 tienen flujos de 20),
   mapa de la cuadrícula de puertas con distancias, distribución de costos de asignaciones aleatorias (media 512), comparación
   ingenua vs óptima.

## Etapa 2 — Líneas base clásicas (persona de Datos)

- Exacta: fuerza bruta por bloques (N ≤ 10, ~4 s). También exacta para N=3/4/5 como control.
- Heurísticas para escalar (N ≥ 14): búsqueda local por intercambios/2-opt con reinicios y recocido simulado; opcionalmente
  búsqueda tabú robusta (estado del arte clásico para QAP). Registrar costo, tiempo, memoria pico (`tracemalloc`) y semilla.

## Etapa 3 — Modelos con Qiskit (persona de Modelos; 30 pts)

Regla: primitivas de Aer (`qiskit_aer.primitives.EstimatorV2/SamplerV2`), nunca las `Statevector*` de referencia.
Prueba rápida en los primeros 20 min: comprobar si `qiskit_algorithms.QAOA` acepta primitivas V2 de Aer; si no, usar la alternativa de abajo.

1. **Modelo** (`model.py`): `QuadraticProgram` → `QuadraticProgramToQubo(penalty=λ)` → `SparsePauliOp` de Ising
   (x = (1−Z)/2). Reportar **la energía QUBO penalizada y el costo factible real por separado** (obligatorio).
2. **Estudio de λ:** barrer λ ∈ {0,25; 0,5; 1; 2; 4}·λ0, con λ0 = una cota del costo marginal de cambiar una variable (una cota
   superior holgada es 1600 para la instancia completa; empezar con λ0 ≈ 50–200 y ajustar en N=3/4). Graficar la fracción factible
   y el mejor costo factible vs λ: muy pequeño → óptimo infactible; muy grande → paisaje plano que QAOA no puede optimizar. Esto justifica λ.
3. **QAOA completo en N pequeño** (N=3 → 9 qubits, N=4 → 16 qubits; N=5 → 25 qubits opcional/Aer MPS): `reps` 1–3,
   COBYLA, semillas fijas. Métricas: mejor costo factible, **fracción factible de las mediciones**, brecha respecto de la fuerza bruta, tiempo.
   Alternativa si `qiskit_algorithms` es lento o incompatible: `QAOAAnsatz(op, reps=p)` + `EstimatorV2` de Aer
   + `scipy.optimize.minimize(COBYLA)`, y luego muestrear con `SamplerV2` de Aer (0,07 s por evaluación con 16 qubits).
4. **Descomposición híbrida para N=10 (y N≥14):** búsqueda de vecindario grande. Elegir k vuelos (k=3 → 9 qubits,
   k=4 → 16 qubits), fijar el resto, construir el sub-QUBO de k² variables (términos lineales por las interacciones con los vuelos
   fijos), resolverlo con QAOA en Aer y quedarse con la mejor reasignación **factible** si mejora; repetir. Nunca necesita un estado
   de 100 qubits (el reto lo dice explícitamente). Ablación: los mismos vecindarios resueltos por enumeración clásica exacta
   → muestra si QAOA aporta algo (lo esperable: no, en un subproblema de 24 permutaciones; decirlo).
5. Opcional solo si sobra tiempo: arranque en caliente desde la mejor solución clásica; reparación clásica de muestras infactibles
   (reportar los resultados original y reparado por separado).

## Etapa 4 — Benchmark y escalabilidad (la persona de Datos lo ejecuta, la de Modelos aporta los solvers; 15 pts)

- Tabla (CSV versionado): tamaño de instancia × método → mejor costo factible, **gap % = 100·(C−340)/340 solo sobre soluciones
  válidas**, fracción factible, tiempo de reloj, memoria pico, semilla, parámetros.
- N=3/4 (controles 24/32) → N=10 (340) → N≥14 sobre instancias sintéticas del mismo generador (cuadrícula Manhattan de
  4 columnas, flujos enteros dispersos con valores tipo qap10), o las instancias del día 2 si los organizadores las entregan.
  14! = 8,7×10¹⁰ → la fuerza bruta tardaría ≈ 27 h a la velocidad actual: reportar dónde deja de ser práctica la enumeración exacta y
  dónde el método híbrido es o no competitivo frente a SA. Tabla de memoria del statevector (N=4: 1 MiB … N=14 ≈ 10⁶⁰ B).

## Etapa 5 — Producto y narrativa (persona de Narrativa; claridad 10 + pitch 25)

- **Narrativa:** "Conexiones aeroportuarias — menos minutos caminando para los pasajeros en transbordo." Gancho = 34 % menos
  caminata que una asignación aleatoria de puertas (unidades supuestas, dicho como supuesto). Luego: lo clásico resuelve N=10
  al instante; por qué igual estudiamos lo cuántico/híbrido (escalar a N≥14, banco de pruebas para QAOA) y un veredicto honesto.
- **App Streamlit** (`src/app.py`), lee primero los resultados versionados para que la demo nunca dependa de una ejecución en vivo:
  pestañas *Problema* (mapa de puertas + aristas de flujo según pasajeros) · *Resolver* (elegir N, método, λ, semilla; en vivo para
  N≤4, en caché para N=10) · *Comparar* (tabla + barras de costo / tiempo / fracción factible) · *Escalar* (tiempo y gap vs N).
- **Lista de entregables (antes de las 17:00 del día 1):** nombre del equipo, integrantes, enlace al repositorio de GitHub, enlace
  a la demo o video, descripción breve (problema · solución · funcionalidades), PPT. Verificar que los enlaces abran sin iniciar sesión.
- **Pitch (2:30–3:00 min):** 1) problema y relevancia, 2) formulación + cómo entra Qiskit, 3) demo en vivo (30 s) con
  video de respaldo, 4) resultado + límites honestos, 5) siguientes pasos. Preparar la pregunta "¿por qué cuántico?".
- Créditos e integridad (bases §11–12): citar MIPLIB `qap10`, la documentación de Qiskit, QAOA (Farhi et al.) y las formulaciones de
  Ising de Lucas; cada integrante debe poder explicar el código y las decisiones.

## Calendario (hoy; T = hora de inicio)

- T+0:00–0:20 PR de contratos del Paso 0. La persona de Modelos hace la prueba rápida de Aer/qiskit-algorithms en paralelo.
- T+0:20–1:15 Datos: parser + F/D + tests de control (24/32/340) + fuerza bruta. Modelos: QUBO/Ising + QAOA N=3 → N=4.
  Narrativa: historia, esqueleto de diapositivas, diseño de la app con datos de ejemplo.
- T+1:15–2:30 Datos: SA/búsqueda local + arnés del benchmark. Modelos: barrido de λ, LNS híbrido para N=10.
  Narrativa: mapa de puertas + gráficos de comparación conectados a resultados reales.
- T+2:30–3:15 Integración, README (configuración, reproducción, resultados, límites), congelar resultados, grabar el video de demo.
- Antes de la ventana de pitch de las 15:00: ensayar; enviar los entregables con margen antes de las 17:00.
- Día 2 (finalistas): escalabilidad N≥14, pulir el pitch.

## Riesgos

- Probablemente QAOA no supere a las líneas base clásicas → reportarlo tal cual; la rúbrica premia pertinencia, honestidad y rigor.
- Simulación lenta: nunca usar `StatevectorSampler/Estimator` de referencia más allá de N=3; N=5 (25 qubits) es opcional.
- Equipo de 3 vs 4 en las bases → confirmar con los organizadores; pueden anunciarse restricciones sobre IA generativa o reutilización
  de código → anotar qué se hizo con ayuda de IA y estar listos para explicarlo todo.
- Conflictos de merge → propiedad de archivos como arriba, PRs pequeños, contratos primero.

## Verificación

- `uv run pytest`: la recuperación de la instancia da 24 (N=3), 32 (N=4), 340 (N=10); `cost()` es igual a la energía QUBO en toda
  asignación factible de N=3/4; comprobación de factibilidad del resultado de QAOA.
- `uv run python -m qap.benchmark` → CSV de resultados con gaps calculados solo sobre soluciones factibles.
- `uv run streamlit run src/app.py` → las cuatro pestañas se muestran desde resultados en caché; la ejecución en vivo de N=4 termina.
- Un clon limpio + `uv sync` + las mismas semillas reproduce el CSV.
