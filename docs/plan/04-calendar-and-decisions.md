# PARTE 4 — Calendario de integración y entregas

Hora del reloj, sábado 24 de octubre. El Paso 0 (contratos, PR #3) ya está integrado (merge). **T = 12:45.** Los tiempos relativos dentro del archivo de
cada persona (`T+0:45`, …) se cuentan desde T. Ventana de pitch 15:00–16:40 (los tres presentes), objetivo de envío 16:00,
límite estricto 17:00.

| Hora | Rodrigo (Datos) | Diego (Modelos) | Felipe (Producto y narrativa) |
|---|---|---|---|
| 12:45–13:10 | Parser, F/D, npz (D2) → **entrega #1** | Spike (M1), inicia `model.py` | Corrección de la fórmula, esqueleto de backend/Vite/Docker sobre JSON simulado (S0–S2) |
| 13:10–13:45 | Fuerza bruta (D3) → `solve_bruteforce` ≈ 13:30; figuras (D4) → **entrega #2** | `model.py` + pruebas (M2–M3), estudio de λ (M4) | Pantallas del frontend sobre JSON simulado, `/api/validate`, `/api/optimize/classical`, diapositivas 1–5 |
| 13:45–14:30 | SA (D5), arnés de benchmark (D7) | QAOA N=3/4 (M5) → **entrega #3** ≈ 14:10 | `/api/optimize/qaoa`, `/api/benchmark`, prueba de build limpio de Docker n.º 1 (14:00) |
| 14:30–14:45 | `results/benchmark.csv` (N=3/4/10: fuerza bruta, SA, QAOA) → **entrega #4** | Híbrido N=10 (M6) si está listo; números finales | **Congelamiento de funcionalidades**, corrección de errores, capturas de respaldo, prueba de Docker n.º 2 |
| 14:45–15:15 | Verificación de reproducibilidad del README (D8), pruebas de la API | Limpieza del notebook, respuestas para preguntas y respuestas | Diapositivas 6–8, ensayo ×3, video |
| 15:00–16:40 | **Ventana de pitch, todos presentes** | | |
| antes de las 16:00 | | | Envío enviado y enlaces verificados |

**Niveles de prioridad (para que nadie intente hacerlo todo antes de las 14:45):**
- **Debe estar antes del congelamiento:** D2, D3, D5, D7 (filas para N=3/4/10) · M1–M5 · backend S2 + pantallas de Resultados/Comparar, Docker, diapositivas, envío.
- **Debería:** M6 híbrido N=10 y la ablación · figuras de D4 · reproducibilidad D8 · interfaz de validación de S3 y distribución de muestras.
- **Día 2 / opcional:** D6 sintéticas N ≥ 14 y ejecuciones de escalamiento, M7 (arranque en caliente, reparación, ruido), edición de matrices en la interfaz.

Entregas: **#1** `load_instance` + `qap10_FD.npz` (Rodrigo → Diego y Felipe) · **#2** figuras en `docs/figures/`
(Rodrigo → Felipe) · **#3** resultados de `solve_qaoa` N=3/4 y `extras.samples` (Diego → Rodrigo para el benchmark, → Felipe para la
API y las diapositivas) · **#4** `results/benchmark.csv` (Rodrigo → Felipe).
Puntos de sincronización (5 min, fijos): **14:00** (N=3/4 de extremo a extremo: fuerza bruta + QAOA detrás de la API, mostrado en la interfaz), **14:30**
(congelar los números que se muestran al jurado), **14:45** (congelamiento de código, todos los PR integrados).
Si alguien está bloqueado > 15 min, debe decirlo de inmediato en el chat del equipo; la persona libre ayuda (típico: Rodrigo termina antes →
pruebas de la API, verificación de Docker y README; Diego atascado con QAOA → cambia a la alternativa de M1).

**Día 2 (finalistas, 08:30–13:00):** Rodrigo + Diego escalan a N ≥ 14 (sintéticas o instancias de los organizadores; SA vs híbrido; tiempo y
memoria; dónde deja de ser conveniente), Felipe añade la vista de escalamiento a la app y pule el pitch.

## Riesgos
- QAOA probablemente no superará al clásico → lo reportamos tal cual; la rúbrica premia la pertinencia y la honestidad, no una ventaja afirmada.
- Costo de simulación → solo Aer; N=5 opcional; el híbrido usa k ≤ 4.
- Sutilezas del parser/recuperación → los óptimos de control 24/32/340 son las pruebas; no avances si fallan los controles.
- Felipe lleva frontend + API + Docker + diapositivas + video → niveles de prioridad anteriores, Rodrigo ayuda tras sus líneas base.
- Equipo de 3 vs 4 en las bases; posibles restricciones anunciadas sobre IA generativa / código preexistente → pregunta a los organizadores
  y anota qué se hizo con ayuda de IA.
- Conflictos de merge → tabla de propiedad, PR pequeños, contratos congelados tras el Paso 0.

## Verificación (qué significa "funciona")
- `uv run pytest` en verde: recuperación de la instancia 24 / 32 / 340; energía QUBO == `cost()` en todas las asignaciones factibles (N=3/4);
  QAOA devuelve una permutación factible para N=3.
- `uv run python -m qap.benchmark …` escribe `results/benchmark.csv`; brechas solo sobre soluciones factibles.
- `docker compose up --build` desde un clon nuevo sirve la app; la ejecución en vivo de QAOA con N=4 termina; los resultados de N=10 se cargan desde
  archivos con commit.
- Clon nuevo + `uv sync` + las mismas semillas reproduce el CSV.

---

# PARTE 5 — Decisiones abiertas (por favor responder antes/en el kickoff)

1. **Tamaño del equipo:** las bases dicen 4 integrantes; somos 3. Confirmar con los organizadores.
2. **Visibilidad del repositorio:** el jurado debe poder abrir el repo. Ahora es **privado**. Opciones: hacerlo público en el momento del envío
   (los datos de MIPLIB son públicos; considera eliminar antes los PDF de `reto-ntt-data/`, son documentos de los organizadores) o invitar a las cuentas del jurado.
3. **Quién es quién (decidido):** Rodrigo = Datos, Felipe = Producto y storytelling (GateFlow Quantum, equipo The Explorers),
   Diego = Modelos. Pon los nombres completos en `docs/team.md` y en el envío.
