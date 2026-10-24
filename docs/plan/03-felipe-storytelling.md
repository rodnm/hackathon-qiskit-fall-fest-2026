# PARTE 3 — PRODUCTO Y STORYTELLING ("AeroQ Optimizer")

La propuesta de Felipe es `reto-ntt-data/GateFlow_Quantum_Recomendaciones.md` (frontend con React + Vite + TypeScript, backend
FastAPI, Docker Compose, equipo **The Explorers**). Esta parte la adopta como arquitectura del producto y solo adapta lo que
debe cambiar para encajar con el código compartido y las reglas de puntuación.

**Nombre del producto (decidido por el equipo): AeroQ Optimizer.** La propuesta original lo llamaba GateFlow Quantum; ese nombre
ya no se usa. Nombres técnicos:

| Dónde | Nombre |
|---|---|
| Producto (diapositivas, pitch, título de la app) | AeroQ Optimizer |
| Equipo (formulario de entrega) | The Explorers |
| `frontend/package.json` → `"name"` | `aeroq-optimizer` |
| `docker-compose.yml` → `name:` | `aeroq` |
| FastAPI → `title` | `AeroQ Optimizer API` |

No se renombran el repositorio (`hackathon-qiskit-fall-fest-2026`) ni el paquete Python compartido (`qap`).

**Eres responsable de:** `frontend/`, `backend/`, `docker-compose.yml`, `.env.example`, los recursos narrativos de `docs/` (diapositivas, pitch, video,
descripción), la sección "Product & results" del README y el envío en sí.
**Dependes de:** `load_instance` / `solve_bruteforce` / `solve_sa` y las figuras de Rodrigo (primera versión lista ≈ T+0:45), `solve_qaoa` de Diego
(≈ T+1:30) y `results/benchmark.csv` (≈ T+1:45). Hasta entonces construye sobre el JSON simulado de S2 para no esperar nunca.
**Tu trabajo también es proteger el calendario:** diriges la lista de verificación previa a la presentación (S7) y el ensayo.

## Qué conservamos de tu propuesta y qué adaptamos

| Tema | Decisión |
|---|---|
| Stack | **Conservar:** React + Vite + TypeScript, Recharts, FastAPI + Pydantic, Docker Compose con 2 servicios (frontend en Nginx, backend), sin DB/Redis/Celery. |
| Código del backend | **Adaptar:** la API es una capa delgada sobre el paquete compartido `qap` (`src/qap`). Sin `objective.py`, `classical_solver.py`, `quantum_solver.py`, `sample_data.py` separados: una sola implementación del costo, una sola fuente de verdad. Archivos del backend: `backend/app/main.py`, `schemas.py`, `service.py`. |
| Dependencias | **Adaptar:** gestionadas con uv, no con `requirements.txt`: `uv add fastapi "uvicorn[standard]"`, haz commit de `pyproject.toml` + `uv.lock`. El Dockerfile del backend instala con `uv sync --frozen --no-dev`. Streamlit ya no es necesario (`uv remove streamlit` en tu primer PR). |
| Fórmula del objetivo | **Corregir:** el §2.2 de tu documento suma sobre todos los pares ordenados, lo que cuenta cada par de vuelos dos veces (costo 680 en lugar de la referencia 340). La convención del reto es **cada par una sola vez**: `Σ_{i<k} Σ_{j≠l} F_ik·D_jl·x_ij·x_kl`. Corrige la fórmula en tu documento y en el texto de la interfaz; el backend solo debe usar `qap.types.cost`. |
| Tamaños | **Conservar tu división:** 10×10 completo con el solver clásico; QAOA sobre una instancia reducida, comparada con el óptimo clásico **de esa misma instancia reducida**. Fijamos los tamaños reducidos en **N=3 y N=4** (N=4 por defecto, 16 qubits); el servidor rechaza QAOA para N > 4. La ejecución híbrida N=10 de Diego se muestra desde resultados en caché, nunca en vivo. |
| Reglas de honestidad | **Conservar todo el §4.3:** objetivo original recalculado para cada asignación, factibilidad visible, la energía penalizada nunca se presenta como distancia, ninguna afirmación de "ventaja cuántica" sin evidencia. |
| Estructura del repositorio | **Adaptar:** `frontend/` y `backend/` viven en la raíz del repo junto a `src/qap`; sin la carpeta adicional `gateflow-quantum/` de la propuesta original. |
| Guía de herramientas de IA (§8) | **Conservar:** una herramienta principal de programación + una segunda para revisión crítica; ejecuta todo tú mismo; sin secretos en los prompts. Lleva una nota breve de qué se hizo con ayuda de IA (reglas de integridad de las bases, §11–12). |

## S0. Primeros 15 minutos (12:45)
- Corrige la fórmula del objetivo en `GateFlow_Quantum_Recomendaciones.md` (§2.2) y añade "cada par contado una sola vez".
- Añade el esqueleto de `docs/story.md` y acuerda el contrato de la API que aparece más abajo con Rodrigo y Diego (ellos implementan los solvers detrás de él).

## S1. Arquitectura (de tu §3, adaptada)

```text
Frontend (React + Vite + TS, Recharts)  ──HTTP/JSON──►  Backend (FastAPI + Pydantic)
 matrices · config · results · compare                    validate · API · service layer
                                                                │
                                          qap.data / qap.classical / qap.quantum  (shared package)
                                          data/ + results/benchmark.csv (read-only, committed)
                                 Docker Compose: `frontend` (Nginx) + `backend`
```

## S2. Contrato de la API (acuérdalo primero; construye el frontend sobre JSON simulado hasta que el backend sea real)

| Método | Endpoint | Comportamiento |
|---|---|---|
| GET | `/api/health` | `{status: "ok", qiskit: "<version>"}` |
| GET | `/api/instance?n=4` | La subinstancia de qap10: `{name, n, F, D, optimum, layout}`; `layout` = coordenadas de las puertas en la cuadrícula de 4 columnas (un supuesto, usado solo para dibujar el mapa) |
| POST | `/api/validate` | `{F, D}` → `{ok, errors[]}`: forma, enteros ≥ 0, F simétrica (almacenada triangular superior), D simétrica con diagonal cero. Mensajes de error claros |
| POST | `/api/optimize/classical` | `{n, method: "bruteforce" or "sa", seed}` → `ResultOut` (fuerza bruta solo para n ≤ 10) |
| POST | `/api/optimize/qaoa` | `{n ≤ 4, lam, reps, maxiter, shots, seed}` → `ResultOut` (timeout del servidor 90 s, ejecutado fuera del event loop) |
| GET | `/api/benchmark` | Filas de `results/benchmark.csv` como JSON (ejecuciones en caché de híbrido N=10, SA y QAOA) |

`ResultOut` refleja el `Result` compartido más campos de transparencia:
`{method, perm, assignment: [{flight, gate}], cost, feasible, seconds, peak_mem_mb, seed, params,
extras: {penalized_energy, feasible_fraction, history, samples}, reference_cost, gap_pct, reference_kind}` donde
`reference_kind` es `"proven_optimum"` (fuerza bruta de esa misma instancia) o `"best_found"`. Esto cubre tu requisito de
identificar si un resultado es un óptimo conocido o la mejor solución encontrada. `gap_pct` se calcula **solo para resultados factibles**.

Petición a Diego: `extras["samples"]` = las 20 cadenas de bits muestreadas más frecuentes como `{perm | null, count, cost | null, energy}` para que la interfaz pueda
graficar la distribución de muestras de QAOA (factibles vs infactibles).
Seguridad del servidor: limita los tamaños, aplica timeout a la llamada de QAOA, permite una sola ejecución de QAOA a la vez (una segunda solicitud concurrente recibe HTTP 429),
nunca expongas stack traces. No hace falta configurar CORS detrás del proxy de Nginx (S4).

JSON simulado (haz commit en `frontend/src/mocks/`): un `ResultOut` para fuerza bruta N=4 (costo 32), uno para QAOA N=4, una tabla de
benchmark. Los valores de control reales son 24 (N=3), 32 (N=4) y 340 (N=10).

## S3. Frontend (tu §5, mismas pantallas) — `frontend/`
1. **Datos del problema:** tablas/mapas de calor de F y D, datos de ejemplo precargados (qap10), errores de validación mostrados tal como se devuelven.
2. **Configuración:** N (3, 4, 10), solver (clásico o QAOA), parámetros de QAOA con valores por defecto seguros (`reps=1`, `maxiter≈100`,
   `shots=4096`, `lam` del estudio de λ de Diego).
3. **Resultados:** tabla vuelo → puerta, **mapa de la cuadrícula de puertas** (SVG, flujos como aristas con grosor proporcional a los pasajeros), costo total,
   tiempo medido, insignia de factibilidad, tipo de referencia (óptimo demostrado / mejor encontrado).
4. **Comparar:** clásico vs QAOA **sobre la misma instancia N=3/4** (tabla + barras de Recharts: costo, tiempo, fracción factible), más la
   distribución de muestras de QAOA cuando existe `extras.samples`. Un segundo bloque muestra los resultados en caché de N=10 (fuerza bruta, SA, híbrido).
5. **Transparencia:** el tamaño de la instancia siempre visible; los errores de ejecución y de validación nunca se ocultan; leyenda "las unidades y las conclusiones
   operativas son supuestos, no mediciones".

Prioridad: **debe** = Resultados + Comparar + estados de salud/error; **debería** = Datos del problema + interfaz de validación + distribución de muestras;
**podría** = edición manual de matrices / carga de CSV. Recorta desde abajo si falta tiempo.

## S4. Docker y resiliencia (tu §7)
- `docker-compose.yml`: `frontend` (build de Vite → Nginx) y `backend` (FastAPI con uvicorn). Health checks, usuario no root,
  `.env.example`, sin secretos en el repo. **Simplificación:** Nginx hace proxy de `/api/` hacia `backend:8000` y el frontend siempre
  llama a la ruta relativa `/api/...`; en desarrollo el servidor de desarrollo de Vite hace proxy de `/api` hacia `localhost:8000`. Sin configuración de CORS y sin
  `VITE_API_URL` (S8 tiene los fragmentos de código).
- La imagen del backend copia `pyproject.toml`, `uv.lock`, `src/qap`, `backend/`, `data/`, `results/`.
- **La demo nunca debe depender de una ejecución cuántica en vivo:** QAOA es en vivo solo para N ≤ 4 (de segundos a cerca de un minuto en Aer);
  todo lo demás se lee de resultados con commit. Guarda **capturas de pantalla de respaldo y el video grabado** (S6) por si fallan la red
  o el simulador.
- Prueba de build limpio desde un clon nuevo: `docker compose up --build` a las **14:00** y de nuevo a las **14:40**.
- Pon las mismas instrucciones en el README (build, inicio, detención).

## S5. Narrativa y diapositivas — `docs/story.md`, `docs/slides.pptx`
- Producto: **AeroQ Optimizer**, equipo **The Explorers**. Eslogan: *Menos minutos caminando para los pasajeros en conexión — una comparación
  rigurosa entre clásico y cuántico sobre la asignación de puertas.*
- Gancho (números reales, unidades supuestas): óptimo 340 vs media aleatoria ≈ 512 → **≈ 34 % menos caminata total**; asignación identidad = 454.
- Veredicto honesto: el método clásico resuelve 10×10 de forma exacta en cerca de 4 s; QAOA se demuestra en 3×3/4×4 y se compara sobre los mismos datos;
  lo cuántico se estudia por su comportamiento y su escalamiento, sin afirmar que sea más rápido.
- 8 diapositivas: (1) título + equipo; (2) problema con la cuadrícula de puertas; (3) modelo + restricciones + verificación de escala 24/32/340;
  (4) arquitectura y pipeline (React → FastAPI → `qap` → Qiskit/Aer); (5) línea base clásica + el gancho del 34 %;
  (6) QAOA sobre la instancia reducida: fracción factible, brecha, λ; (7) escalamiento, límites, híbrido N=10 y el plan del Día 2;
  (8) conclusión, reproducibilidad (`uv sync`, `docker compose up`), créditos.
  Cada número en una diapositiva proviene de `results/benchmark.csv` o de los hechos verificados en `00-shared.md`.

## S6. Pitch, video, envío
- **Pitch 2:30–3:00** (tu §11, con tiempos): 0:00–0:25 problema; 0:25–0:50 modelo (QAP); 0:50–1:15 solución clásica 10×10;
  1:15–1:50 QAOA sobre la instancia reducida, comparado con el óptimo clásico de la **misma** instancia (en vivo, 30 s);
  1:50–2:30 costo medido, factibilidad, tiempo; 2:30–3:00 limitaciones y siguiente paso. Plan de contingencia: el video grabado.
- Hoja de respuestas para el Q&A (acuerda las respuestas con Rodrigo y Diego): *¿Por qué cuántico si la fuerza bruta toma 4 s? ¿Qué es λ y cómo lo
  elegiste? ¿Es esto una ventaja cuántica? ¿Por qué QAOA? ¿Cómo sabes que es factible y correcto (24/32/340)? ¿Qué tan reproducible es?
  ¿Qué cambia en hardware real?*
- **Video de la demo** (60–90 s, Win+G u OBS): el flujo de la app del pitch; súbelo donde el jurado pueda abrirlo sin iniciar sesión.
- **Envío** (bases §8, vence antes de las 17:00, objetivo 16:00): ☐ nombre del equipo ☐ nombres de los integrantes ☐ enlace al repositorio de GitHub ☐ enlace a la demo o video
  ☐ descripción breve (~120 palabras, `docs/description.md`) ☐ PPT. Abre **cada enlace en una ventana privada**. El repo es privado
  hoy → ver `04-calendar-and-decisions.md`, decisión 2.

## S7. Lista de verificación previa a la presentación (tu §10, adoptada como criterios de aceptación)
☐ Las matrices tienen dimensiones compatibles ☐ los datos inválidos se rechazan con mensajes claros ☐ cada solución mostrada asigna exactamente una
puerta a cada vuelo y ninguna puerta dos veces ☐ costo recalculado con el objetivo original ☐ el solver clásico funciona en 10×10 ☐ QAOA corre sobre
la instancia reducida y sus resultados quedan registrados ☐ la comparación usa exactamente los mismos datos reducidos ☐ los tiempos se miden, no se
estiman ☐ `docker compose up` funciona desde un estado limpio ☐ datos de ejemplo reproducibles ☐ capturas/resultados de respaldo.

## S8. Receta de construcción (copia y luego adapta)

**Primero el esqueleto mínimo funcional (walking skeleton) (listo a las 13:15, antes de cualquier funcionalidad).** Una porción vertical que prueba toda la cadena:
`GET /api/health` y `GET /api/instance?n=4` en FastAPI → una página de React que muestra "Backend OK" y las tablas F/D →
`docker compose up --build` sirviéndola en `http://localhost:8080`. Haz commit como primer PR. Todo lo demás se añade encima, así el
riesgo de integración se paga una sola vez, al inicio.

Estructura:
```text
backend/app/main.py      # FastAPI app and the 6 routes
backend/app/schemas.py   # Pydantic: InstanceOut, OptimizeRequest, ResultOut, ValidateRequest
backend/app/service.py   # calls qap.*; Result -> ResultOut; cached brute-force reference per n
backend/Dockerfile
frontend/Dockerfile  frontend/nginx.conf  frontend/vite.config.ts
frontend/src/{pages,components,services/api.ts,mocks}
frontend/public/demo-data/   # offline fallback (S9)
results/.gitkeep             # the folder must exist for the backend image build
docker-compose.yml  .env.example
```

Reglas de `service.py`:
- `reference(n)` = `solve_bruteforce(load_instance(n))`, en caché con `functools.lru_cache`; precalíentalo para N=3, 4 y 10 al iniciar
  (N=10 toma cerca de 4 s) para que ninguna solicitud lo pague. `gap_pct` y `reference_kind` provienen de aquí.
- Cada `ResultOut.cost` se recalcula con `qap.types.cost(perm, inst)`; nunca copies el costo que devuelve un solver.
- Los solvers bloqueantes se ejecutan fuera del event loop (`run_in_threadpool`); QAOA además bajo `asyncio.wait_for(..., 90)` y un lock
  que devuelve 429 cuando ya hay una ejecución en curso.

Dockerfile del backend (boceto; primero `--no-install-project` para que se almacenen en caché las capas de dependencias):
```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY backend ./backend
COPY data ./data
COPY results ./results
RUN uv sync --frozen --no-dev && useradd -m app
USER app
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
```
Frontend: multi-stage (build con `node` → `nginx`), con `location /api/ { proxy_pass http://backend:8000; proxy_read_timeout 120s; }`
(el timeout debe superar el límite de 90 s de QAOA). Compose: `frontend` publicado en `8080`, `backend` solo en la red interna,
`depends_on` con `condition: service_healthy`.
Notas prácticas: el primer build descarga Qiskit/Aer (varios minutos), así que **inicia un build antes de las 13:30** para calentar la caché;
Docker Desktop debe estar en ejecución; conserva el `.dockerignore` (`.venv`, `node_modules`, `.git`, `docs`, `reto-ntt-data`) o el contexto
del build será enorme.

Pruebas de humo de los endpoints (sirven también como criterios de "terminado"; automatízalas como `backend/tests/test_api.py` con `TestClient` de FastAPI):

| Solicitud | Esperado |
|---|---|
| `GET /api/health` | 200, `status = ok` |
| `GET /api/instance?n=4` | 200, `n = 4`, F triangular superior, D simétrica |
| `POST /api/optimize/classical {n:4, method:"bruteforce"}` | `cost = 32`, `feasible = true`, `reference_kind = proven_optimum`, `gap_pct = 0` |
| `POST /api/optimize/classical {n:10, method:"bruteforce"}` | `cost = 340` en cerca de 4 s |
| `POST /api/optimize/qaoa {n:5}` | 422 con un mensaje claro (QAOA limitado a N ≤ 4) |
| `POST /api/validate` con una D asimétrica | `ok = false` y un error que nombra la matriz |

## S9. Resiliencia: modo demo sin conexión y respaldos
- **Modo demo sin conexión:** un script (o una celda de notebook de Rodrigo) exporta `results/benchmark.csv` y los resultados de referencia de N=3/4/10
  a `frontend/public/demo-data/*.json`. Si `/api/health` falla, la interfaz cambia a esos archivos y muestra un banner visible
  "Offline demo data (pre-computed results)". Así el pitch nunca puede fallar por Docker, Aer o la red.
- **Respaldos:** capturas de pantalla de cada pantalla con resultados reales, el video grabado y el JSON exportado; guarda una copia en el
  laptop con el que se presenta y otra en una unidad compartida.
- **Entradas de demo probadas de antemano:** antes de las 14:30 ejecuta la demo en vivo de QAOA con 3 semillas fijas (N=4), anota el tiempo medido y el
  resultado de cada una, y usa solo esas semillas frente al jurado.

## S10. Mapa de la cuadrícula de puertas (el visual distintivo) — `frontend/src/components/GateGrid.tsx`
Props: `{coords, assignment, F, D}`. La puerta j se dibuja en `(j % 4, j // 4)` sobre una cuadrícula de 4 columnas (este es el diseño que codifica la matriz
de distancias D: distancia Manhattan; di "diseño supuesto"). Cada celda muestra el número de puerta y el vuelo asignado. Dibuja una arista
para cada par con F > 0, con grosor de trazo proporcional a F, intensidad de color según `F × distancia` (la contribución al costo); resalta
las 5 mayores contribuciones y muestra los números exactos al pasar el cursor. Dos modos: **asignación única** y **lado a lado**
(ingenua vs óptima, con ambos totales, 454 → 340 en qap10 N=10). Colores accesibles (no solo rojo/verde), leyenda, costo total
siempre visible.

## S11. Kit del pitch

**Demo en vivo, paso a paso (30–40 s):**
1. Abre la app en N=4 → muestra F/D y la cuadrícula de puertas. 2. Ejecuta el solver exacto → costo 32 en milisegundos, "óptimo demostrado".
3. Ejecuta QAOA (semilla probada de antemano) → muestra costo, factibilidad, fracción factible y tiempo medido, y la brecha respecto de 32.
4. Abre Comparar → misma instancia, mismos datos, ambos resultados lado a lado. 5. Cambia a la vista en caché de N=10 → 340, el gancho del 34 %.

**Preguntas probables del jurado (las respuestas deben mantenerse dentro de los hechos verificados):**
- *¿Por qué cuántico si la fuerza bruta toma 4 s?* No gana en velocidad con N=10 y no lo afirmamos; el método exacto no escala
  (14! ≈ 8.7×10¹⁰ permutaciones) y QAOA/híbrido es un banco de pruebas que medimos con honestidad en instancias que podemos verificar.
- *¿Qué es λ?* El peso de la penalización que encarece las asignaciones que violan "una puerta por vuelo"; Diego derivó su
  umbral de forma exacta en N=3/4 y comprobamos la factibilidad de cada resultado.
- *¿Es esto una ventaja cuántica?* No hay evidencia de una; reportamos costo, fracción factible y tiempo frente al óptimo clásico de
  la misma instancia.
- *¿Cómo saben que el modelo es correcto?* Los óptimos de control 24, 32 y 340 se reproducen con una búsqueda exacta; cada costo se
  recalcula con el objetivo original.
- *¿Es reproducible?* `uv.lock`, semillas fijas, parámetros almacenados con cada resultado, `docker compose up`.
- *¿Hardware real?* N=4 necesita 16 qubits con interacciones densas de dos qubits; el ruido y la profundidad del circuito degradarían el resultado;
  no hemos ejecutado en hardware.

**Borrador de la descripción breve (~120 palabras, edita los números con los resultados finales):**
> AeroQ Optimizer assigns connecting flights to airport gates so that transferring passengers walk less. We model the task as a
> quadratic assignment problem (MIPLIB qap10: 10 flights, 10 gates), recover its flow and distance matrices, and solve the full
> 10×10 case exactly in about 4 seconds. On reduced 3×3 and 4×4 instances we encode the problem as a QUBO and run QAOA with Qiskit
> Aer, comparing cost, feasibility and measured time against the exact optimum of the same instance. The web app (React, FastAPI,
> Docker Compose) shows the gate map, the assignments and the side-by-side comparison. The optimal assignment cuts total walking by
> about 34 % against a random one (assumed units). We report where the quantum approach does and does not help.

## Calendario (hora del reloj; T = 12:45)

| Hora | Qué |
|---|---|
| 12:45–13:15 | S0 + **esqueleto mínimo funcional (walking skeleton) (S8)**: `/api/health`, `/api/instance` sobre los tipos reales de `qap` → página de React → `docker compose up`; inicia el primer build de Docker para calentar la caché |
| 13:15–14:00 | Pantallas del frontend sobre JSON simulado; `/api/validate`; `/api/optimize/classical` en cuanto llegue `solve_bruteforce` de Rodrigo (≈ 13:30); diapositivas 1–5 |
| 14:00–14:30 | `/api/optimize/qaoa` con `solve_qaoa` de Diego (≈ 14:10), `/api/benchmark`; prueba de build limpio de Docker n.º 1 |
| 14:30–14:45 | **Congelamiento de funcionalidades.** Corrección de errores, capturas de respaldo, prueba de build limpio de Docker n.º 2 |
| 14:45–15:15 | Diapositivas 6–8, ensayo del pitch ×3, video |
| 15:00–16:40 | Ventana de pitch: **los tres presentamos** |
| antes de las 16:00 | Envío enviado y enlaces verificados (límite estricto 17:00) |

**Advertencia de carga:** frontend + API + Docker + diapositivas + video es mucho para una sola persona. Reglas: recorta según las prioridades de S3; Rodrigo
(tras sus líneas base) se encarga de las pruebas de la API y de la verificación del build limpio; el andamiaje del backend y de compose puede generarse bajo pedido.

**Tu criterio de terminado:** la definición de MVP de tu documento — un usuario selecciona las matrices, ejecuta el solver clásico en
10×10, ejecuta QAOA en una instancia reducida, ve asignaciones factibles y costos recalculados, compara ambos con tiempos medidos, y todo el
sistema inicia con Docker Compose siguiendo el README — además de las diapositivas, el ensayo, el video y el envío.
