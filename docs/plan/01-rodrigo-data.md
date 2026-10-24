# PART 1 — Rodrigo: DATA (data exploration, instance, classical baselines, benchmark)

**You own:** `src/qap/types.py`, `data.py`, `classical.py`, `benchmark.py`, `tests/test_data.py`, `tests/test_classical.py`,
`notebooks/01_data.ipynb`, `data/qap10_FD.npz`, `results/`, `docs/figures/`.
**You deliver to others:** the contracts (T+0:20), `load_instance` + `qap10_FD.npz` (T+0:45), figures (T+1:30),
`benchmark.py` + CSV (T+2:15). Everyone depends on your first two items — do those first.

### D1. Contracts PR (0:00–0:20)
Implement Part 0.5 exactly. Acceptance: `uv run pytest` collects the tests (xfail/skip until the solvers exist).

### D2. Recover F and D from the MPS (0:20–0:45) — `data.py`
Verified algorithm (use it as is; clean it up and add comments):
1. Read only the `COLUMNS` section, skip `MARKER` lines. Aggregate **by column name** (entries span several lines):
   `cols[name].extend(zip(tokens[1::2], tokens[2::2]))`, only for names starting with `Y`.
2. For each `Y` column: `obj` = value on row `NOBJ`; the other rows look like `C{r}A{aaa}`. Collect the two distinct
   `aaa` → `a<b`. Decode `(i, j) = divmod(a−1, 10)`, `(k, l) = divmod(b−1, 10)` (0-based; assert `i<k`, `j!=l`).
   Store `P[i,k,j,l] = obj`.
3. `Dp = P[0,1]` (the 10×10 block for flights 0,1); `g = gcd(all nonzero entries of Dp)`; `D = Dp // g`.
4. For each `i<k`: the ratios `P[i,k][D!=0] / D[D!=0]` must all be equal → that constant is `F[i,k]`
   (**assert it; this is the rank-1 verification**). F ends up integer; the gcd scale (10) lives in F.
5. `load_instance(n)` = first n rows/cols of F and D, `optimum` = brute force for n ≤ 10 (cached).
6. Save `data/qap10_FD.npz` (F, D) and `data/qap10_F.csv`, `data/qap10_D.csv` so the other two never parse the MPS.

Definition of done: `load_instance(3)`, `(4)`, `(10)` → brute-force optima **24, 32, 340**; the rank-1 assertion passes.

### D3. Exact solver (0:45–1:00) — `classical.py: solve_bruteforce`
Chunked enumeration, never storing all permutations (verified, 4 s):
`perms = itertools.permutations(range(n))`; loop: `chunk = np.fromiter(chain.from_iterable(islice(perms, 200_000)), np.int8)`,
reshape `(-1, n)`, cost = `(F_upper_vector * D[chunk[:, iu0], chunk[:, iu1]]).sum(1)` with `iu = np.triu_indices(n, 1)`;
keep the min. Return a `Result` (time, peak memory via `tracemalloc`).

### D4. Exploration for the story (1:00–1:30) — `notebooks/01_data.ipynb` → `docs/figures/*.png`
Produce exactly these figures (names are the handoff to Felipe, who uses them in the slides; label as "assumed units"):
1. `gate_grid.png` — the 10 gates on the 4-column grid with gate ids and distances to a reference gate.
2. `flows_heatmap.png` — F_sym heatmap (flight × flight).
3. `top_flows.png` — bar chart of the 10 largest flows (which flight pairs matter most; hubs).
4. `random_cost_hist.png` — histogram of cost over 20 000 random assignments (mean ≈ 512) with markers for
   identity (454) and optimum (340) → "34 % less walking".
5. `optimal_assignment.png` — the optimal assignment drawn on the grid (flight → gate) with flow edges.
Also a 5-line markdown cell explaining the F/D recovery (this is the "explica cómo recuperaste…" requirement) and the
24/32/340 control.

### D5. Classical heuristics (1:15–2:00) — `classical.py`
- `solve_sa(inst, seed, iters, t0, alpha)`: simulated annealing over swaps. **O(n) delta evaluation** of a swap
  (don't recompute the full cost). Defaults to tune on N=10: `iters=200_000`, geometric cooling, 20 restarts,
  best-of. Report best cost, time, seed. Target: reaches 340 on qap10 most seeds.
- `solve_local_search(inst, seed)`: best-improvement 2-swap from random start with restarts (cheap baseline).
- Optional if time: robust tabu search (the classical reference method for QAP).

### D6. Instances for scaling (2:00–2:20) — `data.py: make_synthetic(n, seed)`
Same structure as qap10 so results are comparable: D = Manhattan distance on a grid with 4 columns and `n` cells;
F sparse with density ≈ 29/45 (≈ 0.64), nonzero values drawn from the qap10 value set {2,4,6,8,10,12,20}.
Used for N = 14, 16, 20 (brute force impossible: 14! = 8.7×10¹⁰ ≈ 27 h at today's speed). If the organizers hand out
day-2 instances, add a loader for their format (support QAPLIB `.dat` too).

### D7. Benchmark harness (2:00–2:30) — `benchmark.py`
`uv run python -m qap.benchmark --sizes 3 4 10 --methods bruteforce sa qaoa hybrid_lns --seeds 0 1 2 3 4`
writes `results/benchmark.csv` (schema in 0.5). Each row stores `params_json` and the seed. Gap computed only for
feasible rows. Methods from Diego are imported by name from `qap.quantum`; until they exist, skip them.

### D8. Reproducibility + README support (2:30–3:00)
Fresh clone in a temp folder → `uv sync` → `uv run pytest` → `uv run python -m qap.benchmark …` reproduces the CSV.
Write the README sections "Setup", "Data recovery", "Reproduce results". Fix whatever breaks.

**Pitfalls:** gates/flights are 0-indexed in code, 1-indexed in the MPS names. Don't count pairs twice (F upper only).
Never trust a cost unless it comes from `cost()`.

**Your definition of done:** control tests green (24/32/340), 5 figures committed, benchmark CSV committed,
fresh-clone reproduction works.
