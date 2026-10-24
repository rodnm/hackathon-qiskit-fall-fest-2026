# PART 3 — Felipe: PRODUCT & STORYTELLING ("GateFlow Quantum")

Felipe's proposal is `reto-ntt-data/GateFlow_Quantum_Recomendaciones.md` (React + Vite + TypeScript frontend, FastAPI
backend, Docker Compose, team **The Explorers**). This part adopts it as the product architecture and only adapts what
must change so it fits the shared code and the scoring rules.

**You own:** `frontend/`, `backend/`, `docker-compose.yml`, `.env.example`, `docs/` story assets (slides, pitch, video,
description), the README "Product & results" section, and the submission itself.
**You depend on:** Rodrigo's `load_instance` / `solve_bruteforce` / `solve_sa` and figures (first ready ≈ T+0:45), Diego's
`solve_qaoa` (≈ T+1:30) and `results/benchmark.csv` (≈ T+1:45). Until then build against the mock JSON in S2 so you never wait.
**Your job is also to protect the schedule:** you run the pre-presentation checklist (S7) and the rehearsal.

## What we keep from your proposal, and what we adapt

| Topic | Decision |
|---|---|
| Stack | **Keep:** React + Vite + TypeScript, Recharts, FastAPI + Pydantic, Docker Compose with 2 services (frontend on Nginx, backend), no DB/Redis/Celery. |
| Backend code | **Adapt:** the API is a thin layer over the shared `qap` package (`src/qap`). No separate `objective.py`, `classical_solver.py`, `quantum_solver.py`, `sample_data.py`: one implementation of the cost, one source of truth. Backend files: `backend/app/main.py`, `schemas.py`, `service.py`. |
| Dependencies | **Adapt:** managed by uv, not `requirements.txt`: `uv add fastapi "uvicorn[standard]"`, commit `pyproject.toml` + `uv.lock`. The backend Dockerfile installs with `uv sync --frozen --no-dev`. Streamlit is no longer needed (`uv remove streamlit` in your first PR). |
| Objective formula | **Fix:** §2.2 of your document sums over all ordered pairs, which counts each flight pair twice (cost 680 instead of the reference 340). The challenge convention is **each pair once**: `Σ_{i<k} Σ_{j≠l} F_ik·D_jl·x_ij·x_kl`. Correct the formula in your document and in the UI text; the backend must only use `qap.types.cost`. |
| Sizes | **Keep your split:** full 10×10 with the classical solver; QAOA on a reduced instance, compared with the classical optimum **of the same reduced instance**. We fix the reduced sizes to **N=3 and N=4** (N=4 default, 16 qubits); the server rejects QAOA for N > 4. Diego's hybrid N=10 run is shown from cached results, never live. |
| Honesty rules | **Keep all of §4.3:** original objective recomputed for every assignment, feasibility shown, penalized energy never presented as distance, no "quantum advantage" claim without evidence. |
| Repo layout | **Adapt:** `frontend/` and `backend/` live at the repo root next to `src/qap`; no extra `gateflow-quantum/` folder. |
| AI-tool guidance (§8) | **Keep:** one main coding tool + a second one for critical review; run everything yourself; no secrets in prompts. Keep a short note of what was AI-assisted (integrity rules of the bases, §11–12). |

## S0. First 15 minutes (12:45)
- Fix the objective formula in `GateFlow_Quantum_Recomendaciones.md` (§2.2) and add "each pair counted once".
- Add the `docs/story.md` skeleton and agree the API contract below with Rodrigo and Diego (they implement the solvers behind it).

## S1. Architecture (from your §3, adapted)

```text
Frontend (React + Vite + TS, Recharts)  ──HTTP/JSON──►  Backend (FastAPI + Pydantic)
 matrices · config · results · compare                    validate · API · service layer
                                                                │
                                          qap.data / qap.classical / qap.quantum  (shared package)
                                          data/ + results/benchmark.csv (read-only, committed)
                                 Docker Compose: `frontend` (Nginx) + `backend`
```

## S2. API contract (agree it first; build the frontend against mock JSON until the backend is real)

| Method | Endpoint | Behaviour |
|---|---|---|
| GET | `/api/health` | `{status: "ok", qiskit: "<version>"}` |
| GET | `/api/instance?n=4` | The qap10 sub-instance: `{name, n, F, D, optimum, layout}`; `layout` = gate coordinates on the 4-column grid (an assumption, used only to draw the map) |
| POST | `/api/validate` | `{F, D}` → `{ok, errors[]}`: shape, integers ≥ 0, F symmetric (stored upper-triangular), D symmetric with zero diagonal. Clear error messages |
| POST | `/api/optimize/classical` | `{n, method: "bruteforce" or "sa", seed}` → `ResultOut` (bruteforce only for n ≤ 10) |
| POST | `/api/optimize/qaoa` | `{n ≤ 4, lam, reps, maxiter, shots, seed}` → `ResultOut` (server timeout 90 s, run off the event loop) |
| GET | `/api/benchmark` | Rows of `results/benchmark.csv` as JSON (cached hybrid N=10, SA and QAOA runs) |

`ResultOut` mirrors the shared `Result` plus fields for transparency:
`{method, perm, assignment: [{flight, gate}], cost, feasible, seconds, peak_mem_mb, seed, params,
extras: {penalized_energy, feasible_fraction, history, samples}, reference_cost, gap_pct, reference_kind}` where
`reference_kind` is `"proven_optimum"` (brute force of that same instance) or `"best_found"`. This covers your requirement to
identify whether a result is a known optimum or the best solution found. `gap_pct` is computed **only for feasible results**.

Request to Diego: `extras["samples"]` = top-20 sampled bitstrings as `{perm | null, count, cost | null, energy}` so the UI can
plot the QAOA sample distribution (feasible vs infeasible).
Server safety: cap the sizes, time out the QAOA call, CORS only for the configured origin, never expose stack traces.

Mock JSON (commit it as `frontend/src/mocks/`): one `ResultOut` for brute force N=4 (cost 32), one for QAOA N=4, one benchmark
table. The real control values are 24 (N=3), 32 (N=4) and 340 (N=10).

## S3. Frontend (your §5, same screens) — `frontend/`
1. **Problem data:** F and D tables/heatmaps, sample data preloaded (qap10), validation errors shown as returned.
2. **Configuration:** N (3, 4, 10), solver (classical or QAOA), QAOA parameters with safe defaults (`reps=1`, `maxiter≈100`,
   `shots=4096`, `lam` from Diego's λ study).
3. **Results:** flight → gate table, **gate-grid map** (SVG, flows as edges with width proportional to passengers), total cost,
   measured time, feasibility badge, reference kind (proven optimum / best found).
4. **Compare:** classical vs QAOA **on the same N=3/4 instance** (table + Recharts bars: cost, time, feasible fraction), plus the
   QAOA sample distribution when `extras.samples` exists. A second block shows the cached N=10 results (brute force, SA, hybrid).
5. **Transparency:** instance size always visible; execution and validation errors never hidden; caption "units and operational
   conclusions are assumptions, not measurements".

Priority: **must** = Results + Compare + health/error states; **should** = Problem data + validation UI + sample distribution;
**could** = editing matrices by hand / CSV upload. Cut from the bottom if time runs out.

## S4. Docker & resilience (your §7)
- `docker-compose.yml`: `frontend` (Vite build → Nginx) and `backend` (FastAPI via uvicorn). Health checks, non-root user,
  API URL via `VITE_API_URL`, `.env.example`, no secrets in the repo.
- The backend image copies `pyproject.toml`, `uv.lock`, `src/qap`, `backend/`, `data/`, `results/`.
- **The demo must never depend on a live quantum run:** QAOA is live only for N ≤ 4 (seconds to about a minute on Aer);
  everything else is read from committed results. Keep **backup screenshots and the recorded video** (S6) in case the network
  or the simulator fails.
- Clean-build test from a fresh clone: `docker compose up --build` at **14:00** and again at **14:40**.
- Put the same instructions in the README (build, start, stop).

## S5. Narrative and slides — `docs/story.md`, `docs/slides.pptx`
- Product: **GateFlow Quantum**, team **The Explorers**. Tagline: *Fewer minutes walking for transferring passengers — a
  rigorous classical-vs-quantum comparison on gate assignment.*
- Hook (real numbers, assumed units): optimum 340 vs random mean ≈ 512 → **≈ 34 % less total walking**; identity assignment = 454.
- Honest verdict: classical solves 10×10 exactly in about 4 s; QAOA is demonstrated on 3×3/4×4 and compared on the same data;
  quantum is studied for behaviour and scaling, not claimed as faster.
- 8 slides: (1) title + team; (2) problem with the gate grid; (3) model + constraints + scale check 24/32/340;
  (4) architecture and pipeline (React → FastAPI → `qap` → Qiskit/Aer); (5) classical baseline + the 34 % hook;
  (6) QAOA on the reduced instance: feasible fraction, gap, λ; (7) scaling, limits, hybrid N=10 and the Day-2 plan;
  (8) conclusion, reproducibility (`uv sync`, `docker compose up`), credits.
  Every number on a slide comes from `results/benchmark.csv` or the verified facts in `00-shared.md`.

## S6. Pitch, video, submission
- **Pitch 2:30–3:00** (your §11, with times): 0:00–0:25 problem; 0:25–0:50 model (QAP); 0:50–1:15 classical 10×10 solution;
  1:15–1:50 QAOA on the reduced instance, compared with the classical optimum of the **same** instance (live, 30 s);
  1:50–2:30 measured cost, feasibility, time; 2:30–3:00 limitations and next step. Fallback: the recorded video.
- Q&A cheat sheet (agree the answers with Rodrigo and Diego): *Why quantum if brute force takes 4 s? What is λ and how did you
  choose it? Is this a quantum advantage? Why QAOA? How do you know it is feasible and correct (24/32/340)? How reproducible is
  it? What changes on real hardware?*
- **Demo video** (60–90 s, Win+G or OBS): the app flow of the pitch; upload it where the jury can open it without login.
- **Submission** (bases §8, due before 17:00, target 16:00): ☐ team name ☐ member names ☐ GitHub repo link ☐ demo link or video
  ☐ short description (~120 words, `docs/description.md`) ☐ PPT. Open **every link in a private window**. The repo is private
  today → see `04-calendar-and-decisions.md`, decision 2.

## S7. Pre-presentation checklist (your §10, adopted as acceptance criteria)
☐ Matrices have compatible dimensions ☐ invalid data is rejected with clear messages ☐ every shown solution assigns exactly one
gate per flight and no gate twice ☐ cost recomputed with the original objective ☐ classical solver works on 10×10 ☐ QAOA runs on
the reduced instance and its results are recorded ☐ the comparison uses exactly the same reduced data ☐ times are measured, not
estimated ☐ `docker compose up` works from a clean state ☐ reproducible example data ☐ backup screenshots/results.

## Schedule (clock time; T = 12:45)

| Time | What |
|---|---|
| 12:45–13:15 | S0, backend skeleton (`/api/health`, `/api/instance` on the real `qap` types), Vite skeleton, compose file, story skeleton |
| 13:15–14:00 | Frontend screens on mock JSON; `/api/validate`; `/api/optimize/classical` as soon as Rodrigo's `solve_bruteforce` lands (≈ 13:30); slides 1–5 |
| 14:00–14:30 | `/api/optimize/qaoa` with Diego's `solve_qaoa` (≈ 14:10), `/api/benchmark`; clean Docker build test #1 |
| 14:30–14:45 | **Feature freeze.** Bug fixes, backup screenshots, clean Docker build test #2 |
| 14:45–15:15 | Slides 6–8, pitch rehearsal ×3, video |
| 15:00–16:40 | Pitch window: **all three of us present** |
| by 16:00 | Submission sent and links verified (hard cutoff 17:00) |

**Load warning:** frontend + API + Docker + slides + video is a lot for one person. Rules: cut by the priorities in S3; Rodrigo
(after his baselines) takes the API tests and the clean-build check; the backend and compose scaffolding can be generated on request.

**Your definition of done:** the MVP definition of your document — a user selects the matrices, runs the classical solver on
10×10, runs QAOA on a reduced instance, sees feasible assignments and recomputed costs, compares both with measured times, and the
whole system starts with Docker Compose following the README — plus the slides, the rehearsal, the video and the submission.
