# PART 4 — Integration calendar and handoffs

Clock times, Saturday 24 Oct. Step 0 (contracts, PR #3) is already merged. **T = 12:45.** The relative times inside each
person's file (`T+0:45`, …) are counted from T. Pitch window 15:00–16:40 (all three present), submission target 16:00,
hard cutoff 17:00.

| Clock | Rodrigo (Data) | Diego (Models) | Felipe (Product & story) |
|---|---|---|---|
| 12:45–13:10 | Parser, F/D, npz (D2) → **handoff #1** | Spike (M1), start `model.py` | Formula fix, backend/Vite/Docker skeleton on mock JSON (S0–S2) |
| 13:10–13:45 | Brute force (D3) → `solve_bruteforce` ≈ 13:30; figures (D4) → **handoff #2** | `model.py` + tests (M2–M3), λ study (M4) | Frontend screens on mock JSON, `/api/validate`, `/api/optimize/classical`, slides 1–5 |
| 13:45–14:30 | SA (D5), benchmark harness (D7) | QAOA N=3/4 (M5) → **handoff #3** ≈ 14:10 | `/api/optimize/qaoa`, `/api/benchmark`, Docker clean-build test #1 (14:00) |
| 14:30–14:45 | `results/benchmark.csv` (N=3/4/10: brute force, SA, QAOA) → **handoff #4** | Hybrid N=10 (M6) if ready; final numbers | **Feature freeze**, bug fixes, backup screenshots, Docker test #2 |
| 14:45–15:15 | README repro check (D8), API tests | Notebook cleanup, Q&A answers | Slides 6–8, rehearsal ×3, video |
| 15:00–16:40 | **Pitch window, all present** | | |
| by 16:00 | | | Submission sent and links verified |

**Priority tiers (so nobody tries to do everything before 14:45):**
- **Must before freeze:** D2, D3, D5, D7 (rows for N=3/4/10) · M1–M5 · S2 backend + Results/Compare screens, Docker, slides, submission.
- **Should:** M6 hybrid N=10 and the ablation · D4 figures · D8 reproducibility · S3 validation UI and sample distribution.
- **Day 2 / stretch:** D6 synthetic N ≥ 14 and scaling runs, M7 (warm start, repair, noise), editing matrices in the UI.

Handoffs: **#1** `load_instance` + `qap10_FD.npz` (Rodrigo → Diego and Felipe) · **#2** figures in `docs/figures/`
(Rodrigo → Felipe) · **#3** `solve_qaoa` N=3/4 results and `extras.samples` (Diego → Rodrigo for the benchmark, → Felipe for the
API and the slides) · **#4** `results/benchmark.csv` (Rodrigo → Felipe).
Sync points (5 min, standing): **14:00** (N=3/4 end-to-end: brute force + QAOA behind the API, shown in the UI), **14:30**
(freeze the numbers shown to the jury), **14:45** (code freeze, all PRs merged).
If someone is blocked > 15 min, say it in the team chat immediately; the free person helps (typical: Rodrigo finishes early →
API tests, Docker check and README; Diego stuck on QAOA → switch to the fallback path in M1).

**Day 2 (finalists, 08:30–13:00):** Rodrigo + Diego scale to N ≥ 14 (synthetic or organizers' instances; SA vs hybrid; time and
memory; where it stops being convenient), Felipe adds the scaling view to the app and polishes the pitch.

## Risks
- QAOA will probably not beat classical → we report it plainly; the rubric rewards pertinence and honesty, not a claimed advantage.
- Simulation cost → Aer only; N=5 optional; hybrid uses k ≤ 4.
- Parser/recovery subtleties → control optima 24/32/340 are the tests; don't proceed on failing controls.
- Felipe carries frontend + API + Docker + slides + video → priority tiers above, Rodrigo helps after his baselines.
- Team of 3 vs 4 in the bases; possible announced restrictions on generative AI / pre-existing code → ask the organizers
  and note what was AI-assisted.
- Merge conflicts → ownership table, small PRs, contracts frozen after Step 0.

## Verification (what "it works" means)
- `uv run pytest` green: instance recovery 24 / 32 / 340; QUBO energy == `cost()` on all feasible assignments (N=3/4);
  QAOA returns a feasible permutation for N=3.
- `uv run python -m qap.benchmark …` writes `results/benchmark.csv`; gaps only over feasible solutions.
- `docker compose up --build` from a fresh clone serves the app; the N=4 QAOA live run completes; N=10 results load from
  committed files.
- Fresh clone + `uv sync` + same seeds reproduces the CSV.

---

# PART 5 — Open decisions (please answer before/at kickoff)

1. **Team size:** bases say 4 members; we are 3. Confirm with the organizers.
2. **Repo visibility:** the jury must open the repo. It is **private** now. Options: make it public at submission time
   (MIPLIB data is public; consider removing `reto-ntt-data/` PDFs first, they are organizer documents) or invite the jury accounts.
3. **Who is who (decided):** Rodrigo = Data, Felipe = Product & storytelling (GateFlow Quantum, team The Explorers),
   Diego = Models. Put the full names in `docs/team.md` and the submission.
