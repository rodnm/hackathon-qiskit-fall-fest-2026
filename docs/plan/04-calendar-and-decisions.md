# PART 4 — Integration calendar and handoffs

T = start time (work backwards from the 15:00 pitch window; submission cutoff 17:00).

| When | Rodrigo (Data) | Diego (Models) | Felipe (Story) |
|---|---|---|---|
| T+0:00–0:20 | Step 0 contracts PR | Spike (M1) | Narrative one-pager (S1) |
| T+0:20–0:45 | Parser, F/D, npz (D2) → **handoff #1** | Reviews contracts; starts `model.py` | App skeleton with placeholders |
| T+0:45–1:30 | Brute force (D3), figures (D4) → **handoff #2** | `model.py` + tests (M2–M3), λ study (M4) | App tabs 1–2 |
| T+1:30–2:15 | SA / local search (D5), synthetic (D6) | QAOA N=3/4 (M5) → **handoff #3** | App tab 3, slides 1–5 |
| T+2:15–2:45 | Benchmark CSV (D7) → **handoff #4** | Hybrid N=10 + ablation (M6) | Wire real results, slides 6–8 |
| T+2:45–3:15 | Reproducibility + README (D8) | Final numbers, notebook cleanup | Video, rehearsal, submission |
| Before 15:00 | **Code freeze**, all PRs merged | | Final checks |

Handoffs: **#1** contracts + `load_instance` + `qap10_FD.npz` (Rodrigo → Diego and Felipe) · **#2** figures in
`docs/figures/` (Rodrigo → Felipe) · **#3** `solve_qaoa` N=3/4 results (Diego → Rodrigo for the benchmark, → Felipe for
slides) · **#4** `results/benchmark.csv` (Rodrigo → Felipe).
Sync points (5 min, standing): at T+1:15 (N=3/4 end-to-end with brute force + QAOA on the app placeholder),
at T+2:30 (freeze decisions on numbers shown to the jury), at code freeze.
If someone is blocked > 15 min, say it in the team chat immediately; the free person helps (typical: Rodrigo finishes
early → helps Felipe with charts/README; Diego stuck on QAOA → switch to the fallback path in M1).

**Day 2 (finalists, 08:30–13:00):** Rodrigo + Diego scale to N ≥ 14 (synthetic or organizers' instances; SA vs hybrid; time and
memory; where it stops being convenient), Felipe updates app tab 4 and polishes the pitch.

## Risks
- QAOA will probably not beat classical → we report it plainly; the rubric rewards pertinence and honesty, not a claimed advantage.
- Simulation cost → Aer only; N=5 optional; hybrid uses k ≤ 4.
- Parser/recovery subtleties → control optima 24/32/340 are the tests; don't proceed on failing controls.
- Team of 3 vs 4 in the bases; possible announced restrictions on generative AI / pre-existing code → ask the organizers
  and note what was AI-assisted.
- Merge conflicts → ownership table, small PRs, contracts frozen after Step 0.

## Verification (what "it works" means)
- `uv run pytest` green: instance recovery 24 / 32 / 340; QUBO energy == `cost()` on all feasible assignments (N=3/4);
  QAOA returns a feasible permutation for N=3.
- `uv run python -m qap.benchmark …` writes `results/benchmark.csv`; gaps only over feasible solutions.
- `uv run streamlit run src/app.py` renders all four tabs from committed results; N=4 live run completes.
- Fresh clone + `uv sync` + same seeds reproduces the CSV.

---

# PART 5 — Open decisions (please answer before/at kickoff)

1. **Team size:** bases say 4 members; we are 3. Confirm with the organizers.
2. **Repo visibility:** the jury must open the repo. It is **private** now. Options: make it public at submission time
   (MIPLIB data is public; consider removing `reto-ntt-data/` PDFs first, they are organizer documents) or invite the jury accounts.
3. **Who is who (decided):** Rodrigo = Data, Felipe = Storytelling, Diego = Models. Put names in `docs/team.md` and the
   submission (full names and the team name are still needed).
