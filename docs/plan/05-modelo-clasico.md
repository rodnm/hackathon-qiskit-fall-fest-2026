# PARTE 5 — Modelo clásico (Rodrigo) para que Diego se concentre en lo cuántico

**Estado:** Fase A (comparación del día 1) y Fase B (heurísticas clásicas) en ejecución por Rodrigo. **Fase C en stand by**
hasta acordarla con Diego.

## Contexto

Diego (Modelos) tiene el modelo QUBO/Ising, QAOA (`solve_qaoa`), el estudio de λ y el híbrido LNS, y escribe sus corridas en
`results/lambda_qaoa.csv`, `results/qaoa_m5.csv` y `results/hybrid_lns.csv`. Del lado clásico existía solo la **fuerza bruta
exacta** (`solve_bruteforce`): óptimo probado para N ≤ 10 (N=10: 340 en ~5 s). Rodrigo toma toda la parte clásica y la
comparación. Diego no toca nada clásico y nosotros **no volvemos a correr QAOA**: leemos sus CSV.

## Precisiones del reto (verificadas en `reto-ntt-data/Reto_NTT_DATA.pdf`; Track A)

| Regla | Consecuencia para el modelo clásico |
|---|---|
| "Comparando un método clásico con otro que utilice Qiskit" | El clásico es la referencia obligatoria de toda comparación |
| Etapa 1: N=3 o N=4 (primeras N filas/columnas), óptimos de control 24 y 32; comparar **costo, factibilidad y tiempo** | Tabla del día 1 en N=3/4; N=10 es opcional hoy ("se acepta un trabajo sólido en N=4 o N=5") |
| "Para la instancia completa, calcula la brecha … solo sobre soluciones válidas: gap(%) = 100·(C − 340)/340" | `gap_pct` **solo para N=10 y solo si la asignación es válida**. Para N<10: `gap_vs_control_pct` (distancia al óptimo de control), rotulada como extensión nuestra |
| "Puedes usar el óptimo conocido para evaluar la solución, pero **no como punto de partida**" | Las heurísticas nunca arrancan desde la permutación óptima, no leen `inst.optimum` y no se detienen al llegar a 340 (presupuesto fijo) |
| "Si aplicas reparación clásica, informa tanto el resultado original como el corregido" | Si alguna vez se repara una muestra de QAOA, se guardan ambos resultados en columnas distintas |
| "La energía penalizada del QUBO no es lo mismo que el costo … si reportas ambas, identifícalas" | Columnas separadas `cost` y `penalized_energy` |
| Sección 6, comparación: mejor costo factible, fracción factible de las muestras, tiempo total y límites del método; reproducibilidad: código, versiones, semillas, parámetros | Columnas y agregados de la tabla de comparación |
| Etapa 3 (día 2): N ≥ 14, comparar con N=10 en tiempo, memoria, calidad y factibilidad | Heurísticas escalables + medición de memoria + instancias ampliadas |

## Fase A — comparación del día 1

1. **`src/qap/classical.py`:** `solve_bruteforce` ya no apaga la medición de memoria de quien lo llama (antes hacía
   `tracemalloc.start()/stop()` siempre).
2. **`src/qap/stats.py`:** `random_floor`, `wilson_interval`, `binomial_vs_floor`, `shots_for_power`, `gap_pct` (solo N=10),
   `gap_vs_control_pct` (N<10).
3. **`src/qap/benchmark.py`** (`uv run python -m qap.benchmark`): corre los métodos clásicos e **ingiere sin volver a correr**
   los CSV de Diego (deduplicando corridas repetidas entre archivos). Escribe `results/benchmark.csv` (una fila por corrida) y
   `results/comparison.csv` (agregado por N × método × configuración: mejor costo, tasa de llegada al óptimo con IC de Wilson,
   gap, tiempo, memoria y, para QAOA, fracción factible combinada con IC, múltiplo y p-valor frente al piso del azar y disparos
   necesarios para detectar 2× el piso).
4. **`notebooks/07_comparacion.ipynb`** (el número 05 ya lo usa Diego): tabla del día 1, figuras
   `docs/figures/qaoa_vs_random_floor.png` y `docs/figures/classical_vs_qaoa.png`, y conclusiones.
5. **Tests:** `tests/test_stats.py`, `tests/test_benchmark.py` y un test nuevo en `tests/test_classical.py`.

## Fase B — heurísticas clásicas

Firma del contrato `solve_xxx(inst, *, seed, **params) -> Result`, arranque aleatorio por semilla, presupuesto fijo y **sin usar
el óptimo conocido**.

1. `swap_delta(perm, r, s, F_sym, D)`: variación exacta del costo al intercambiar dos vuelos, en O(n).
2. `solve_local_search`: descenso por el mejor intercambio con múltiples arranques (el EDA midió 3,2 % de éxito por arranque).
3. `solve_sa`: recocido simulado con intercambios, temperatura inicial calibrada con los intercambios aleatorios y enfriamiento
   geométrico.
4. Registradas en el benchmark (N = 3, 4, 10 × semillas 0–9); el notebook de comparación suma su sección.
5. Tests: `swap_delta` igual al recálculo completo, determinismo por semilla, resultados válidos, funcionan con
   `optimum=None` (no leen el óptimo).

## Fase C — EN STAND BY (necesita a Diego), día 2

1. `make_synthetic(n, seed)` en `src/qap/data.py` (cuadrícula Manhattan de 4 columnas, flujos con la distribución de qap10), o
   el cargador de las instancias que entregue la organización.
2. Mitad clásica del híbrido con una interfaz para que Diego enchufe su subsolver QAOA
   (`Subsolver = Callable[[Instance, perm, subset, seed], tuple[perm | None, dict]]`). Diego ya tiene un LNS propio en
   `src/qap/hybrid_study.py`: hay que acordar con él si se divide o se mantiene como está.
3. Corridas N = 14, 16, 20: tiempo, memoria, calidad y factibilidad frente a N=10.
4. Opcional: búsqueda tabú robusta.

## Coordinación

- **Diego:** dueño de `model.py`, `quantum.py`, `lambda_study.py`, `hybrid_study.py`. Recomendación: volver a correr N=4 con
  ≥ 22 000 disparos por configuración, más semillas y λ entre 1,25 y 1,5·λ*; la comparación se actualiza sola al regenerar el
  benchmark.
- **Felipe:** consume `results/benchmark.csv` y `results/comparison.csv` (endpoint `/api/benchmark`, diapositivas).

## Verificación

- `uv run pytest` y `uv run ruff check` sobre los archivos del modelo clásico en verde.
- `uv run python -m qap.benchmark` genera ambos CSV; `gap_pct` solo aparece en N=10 y en filas válidas.
- `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/07_comparacion.ipynb` sin errores.
