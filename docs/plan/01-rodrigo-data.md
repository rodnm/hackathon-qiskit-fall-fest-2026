# PARTE 1 — Rodrigo: DATOS (exploración de datos, instancia, líneas base clásicas, benchmark)

**Eres responsable de:** `src/qap/types.py`, `data.py`, `classical.py`, `benchmark.py`, `tests/test_data.py`, `tests/test_classical.py`,
`notebooks/01_data.ipynb`, `data/qap10_FD.npz`, `results/`, `docs/figures/`.
**Entregas a los demás:** los contratos (T+0:20), `load_instance` + `qap10_FD.npz` (T+0:45), figuras (T+1:30),
`benchmark.py` + CSV (T+2:15). Todos dependen de tus dos primeros puntos: hazlos primero.

### D1. PR de contratos (0:00–0:20)
Implementa la Parte 0.5 tal cual. Aceptación: `uv run pytest` recolecta las pruebas (xfail/skip hasta que existan los solvers).

### D2. Recuperar F y D desde el MPS (0:20–0:45) — `data.py`
Algoritmo verificado (úsalo tal cual; límpialo y añade comentarios):
1. Lee solo la sección `COLUMNS`, omite las líneas `MARKER`. Agrega **por nombre de columna** (las entradas ocupan varias líneas):
   `cols[name].extend(zip(tokens[1::2], tokens[2::2]))`, solo para nombres que empiezan con `Y`.
2. Para cada columna `Y`: `obj` = valor en la fila `NOBJ`; las demás filas tienen la forma `C{r}A{aaa}`. Reúne los dos
   `aaa` distintos → `a<b`. Decodifica `(i, j) = divmod(a−1, 10)`, `(k, l) = divmod(b−1, 10)` (base 0; verifica con assert `i<k`, `j!=l`).
   Guarda `P[i,k,j,l] = obj`.
3. `Dp = P[0,1]` (el bloque de 10×10 para los vuelos 0,1); `g = gcd(todas las entradas no nulas de Dp)`; `D = Dp // g`.
4. Para cada `i<k`: los cocientes `P[i,k][D!=0] / D[D!=0]` deben ser todos iguales → esa constante es `F[i,k]`
   (**verifícala con assert; esta es la verificación de rango 1**). F resulta entera; la escala del gcd (10) queda en F.
5. `load_instance(n)` = primeras n filas/columnas de F y D, `optimum` = fuerza bruta para n ≤ 10 (en caché).
6. Guarda `data/qap10_FD.npz` (F, D) y `data/qap10_F.csv`, `data/qap10_D.csv` para que los otros dos nunca tengan que leer el MPS.

Criterio de terminado: `load_instance(3)`, `(4)`, `(10)` → óptimos de fuerza bruta **24, 32, 340**; la verificación de rango 1 pasa.

### D3. Solver exacto (0:45–1:00) — `classical.py: solve_bruteforce`
Enumeración por bloques, sin almacenar nunca todas las permutaciones (verificado, 4 s):
`perms = itertools.permutations(range(n))`; bucle: `chunk = np.fromiter(chain.from_iterable(islice(perms, 200_000)), np.int8)`,
redimensiona a `(-1, n)`, costo = `(F_upper_vector * D[chunk[:, iu0], chunk[:, iu1]]).sum(1)` con `iu = np.triu_indices(n, 1)`;
conserva el mínimo. Devuelve un `Result` (tiempo, memoria pico mediante `tracemalloc`).

### D4. Exploración para la narrativa (1:00–1:30) — `notebooks/01_data.ipynb` → `docs/figures/*.png`
Produce exactamente estas figuras (los nombres son la entrega a Felipe, que las usa en las diapositivas; etiquétalas como "unidades supuestas"):
1. `gate_grid.png` — las 10 puertas en la cuadrícula de 4 columnas con los ids de puerta y las distancias a una puerta de referencia.
2. `flows_heatmap.png` — mapa de calor de F_sym (vuelo × vuelo).
3. `top_flows.png` — gráfico de barras de los 10 mayores flujos (qué pares de vuelos importan más; hubs).
4. `random_cost_hist.png` — histograma del costo en 20 000 asignaciones aleatorias (media ≈ 512) con marcadores para
   la identidad (454) y el óptimo (340) → "34 % menos caminata".
5. `optimal_assignment.png` — la asignación óptima dibujada sobre la cuadrícula (vuelo → puerta) con aristas de flujo.
Incluye también una celda markdown de 5 líneas que explique la recuperación de F/D (este es el requisito "explica cómo recuperaste…") y el
control 24/32/340.

### D5. Heurísticas clásicas — `classical.py` (hecho, ver `05-modelo-clasico.md`)
- `swap_delta`: variación exacta del costo de un intercambio en O(n) (validada contra el recálculo completo).
- `solve_local_search(inst, seed, restarts=100)`: descenso por el mejor intercambio con 100 arranques aleatorios. En N=10 llega
  a 340 en 10 de 10 semillas, ~0,5 s por corrida.
- `solve_sa(inst, seed, iters=10_000, restarts=10)`: recocido simulado con temperatura inicial calibrada y enfriamiento
  geométrico. En N=10 llega a 340 en 9 de 10 semillas (gap medio del reto 0,29 %), ~2,8 s por corrida.
- Ninguna usa el óptimo conocido (arranque aleatorio, presupuesto fijo). Están registradas en el benchmark.
- Pendiente opcional (día 2): búsqueda tabú robusta.

### D6. Instancias para escalamiento (2:00–2:20) — `data.py: make_synthetic(n, seed)`
Misma estructura que qap10 para que los resultados sean comparables: D = distancia Manhattan sobre una cuadrícula de 4 columnas y `n` celdas;
F dispersa con densidad ≈ 29/45 (≈ 0.64), con valores no nulos tomados del conjunto de valores de qap10 {2,4,6,8,10,12,20}.
Se usa para N = 14, 16, 20 (la fuerza bruta es imposible: 14! = 8.7×10¹⁰ ≈ 27 h a la velocidad actual). Si los organizadores entregan
instancias del día 2, añade un cargador para su formato (soporta también `.dat` de QAPLIB).

### D7. Arnés de benchmark — `benchmark.py` + `stats.py` (hecho, ver `05-modelo-clasico.md`)
`uv run python -m qap.benchmark [--sizes 3 4 10] [--seeds 0 … 9] [--methods …]` corre los métodos clásicos e **ingiere sin volver a
correr** los resultados de Diego (`results/lambda_qaoa.csv`, `results/qaoa_m5.csv`, `results/hybrid_lns.csv`). Escribe
`results/benchmark.csv` (esquema en 0.5) y `results/comparison.csv`, con la brecha del reto solo para N=10 y filas válidas, y,
para QAOA, la fracción factible con IC de Wilson comparada con el piso del azar (test binomial). La tabla del día 1 y las figuras
están en `notebooks/07_comparacion.ipynb`.

### D8. Reproducibilidad + apoyo al README (2:30–3:00)
Clon nuevo en una carpeta temporal → `uv sync` → `uv run pytest` → `uv run python -m qap.benchmark …` reproduce el CSV.
Escribe las secciones del README "Setup", "Data recovery", "Reproduce results". Arregla lo que falle.

**Errores comunes:** las puertas y los vuelos van con base 0 en el código y con base 1 en los nombres del MPS. No cuentes los pares dos veces (solo F superior).
Nunca confíes en un costo que no provenga de `cost()`.

**Tu criterio de terminado:** pruebas de control en verde (24/32/340), 5 figuras con commit, CSV de benchmark con commit,
la reproducción desde un clon nuevo funciona.
