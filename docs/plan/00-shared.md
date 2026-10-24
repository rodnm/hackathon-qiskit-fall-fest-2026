# PART 0 — Shared context

## 0.1 The challenge in one paragraph
NTT DATA × IBM Quantum Hackathon. Instance MIPLIB `qap10`: assign 10 items to 10 locations minimizing
C(x) = Σ_{i<k} Σ_{j≠l} F_ik·D_jl·x_ij·x_kl (each pair once), x a permutation matrix. Reference optimum **C* = 340**.
We must use **Qiskit substantively**, compare against a **classical baseline**, report cost, feasibility and time
honestly (including when quantum does not help), and make results **reproducible**. Day 1 (today, 10:00–17:00,
pitch window 15:00–16:40): stage 1 (N=3/4, optionally N=10). Day 2 (finalists): scalability N ≥ 14.

Scoring (NTT): model/data/feasibility 25 · Qiskit relevance & justification 30 · assignment quality vs classical 20 ·
rigor (time, limits, scaling) 15 · clarity & operational meaning 10. Event rubric on top: innovation/validation 25,
Qiskit + pitch clarity 25, technical rigor/reproducibility 15, architecture 15. Quantum Hub track: an environment to
**represent, run, visualize and compare** classical vs quantum/hybrid solutions.

## 0.2 Our framing (Track A)
10 connecting **flights** → 10 **gates**. F_ik = passengers transferring between flights i and k.
D_jl = walking distance between gates j and l. Goal: minimize total passenger walking distance.
**Units are assumptions, not measurements** (the challenge requires saying this explicitly).

## 0.3 Facts already verified (do not re-derive)
- `data/qap10.mps.gz` has 100 assignment vars `X001..X100` (x_ij = `X{10·(i−1)+j}`) and 4050 linearization vars
  `Y…A…` whose objective coefficient is F_ik·D_jl. A column's entries span several lines of the file.
- **F and D recover exactly.** D = Manhattan distance on a **4-column grid with 10 cells** (gates 0–3 / 4–7 / 8–9),
  symmetric; every (i,k) block of coefficients is rank-1 → integer F (values 2…20, 29 of 45 pairs nonzero,
  total flow 228).
- **Brute force over 10! = 3 628 800 permutations takes 4.0 s** and returns **340**; optimal permutation
  `[2 6 3 0 8 4 5 1 7 9]` (flight i → gate perm[i]). Control optima: N=3 → **24**, N=4 → **32**.
- Naive baselines for the story: identity assignment = 454; random assignment mean ≈ 512 (min 372, max 654).
  The optimum (340) is **≈ 34 % less walking than a random assignment**.
- Qiskit stack works (Qiskit 2.6.1, qiskit-optimization 0.7.0, qiskit-algorithms 0.4.0, Aer 0.18):
  `QuadraticProgram` → `QuadraticProgramToQubo` → `to_ising` gives N=3 → 9 qubits / 45 Pauli terms,
  N=4 → 16 qubits / 112 terms. `MinimumEigenOptimizer(QAOA(...))` found 24 on N=3.
  **Speed trap:** the reference `StatevectorSampler/Estimator` took **87 s** for N=3 and never finished for N=4.
  **Aer `EstimatorV2` evaluates a 16-qubit QAOA circuit in ~0.07 s → always use Aer primitives.**
- Consequence (say it in the pitch): the exact classical solver answers N=10 in 4 s, so quantum will not win on speed.
  Our value is a correct model, a rigorous comparison, honest limits, and a clear product.

## 0.4 Repo rules (everyone)
- `main` is protected by convention: **branch → commit → push branch → PR**. Never push to `main`.
  Branch names: `feat/data-…`, `feat/models-…`, `feat/story-…`. One small PR per slice, reviewed by one teammate
  (target review time: < 10 min).
- **One writer per file** (ownership below). Need a change in someone else's file → tell them / open a tiny PR to them.
- Commit messages: imperative sentence describing *why* (see `git log`). No AI-attribution lines in commits/PRs.
- Setup: `uv sync`; run things with `uv run …`. New dependency: `uv add <pkg>` and commit `pyproject.toml` + `uv.lock`.
- Integrity (bases §11–12): cite sources (MIPLIB, Qiskit docs, QAOA paper), note what was AI-assisted, and **every
  member must be able to explain every part of the solution** at the pitch.

## 0.5 Step 0 — Shared contracts (first ~20 min; Rodrigo writes it, everyone reviews it)
Everything below lives in `src/qap/` and is **frozen after merge** (changes must be announced to the team).

```python
# src/qap/types.py
@dataclass(frozen=True)
class Instance:
    name: str; n: int
    F: np.ndarray      # (n,n) int, upper-triangular: F[i,k], i<k (flows); zeros elsewhere
    D: np.ndarray      # (n,n) int, symmetric, zero diagonal (distances)
    optimum: int | None
    @property
    def F_sym(self): return self.F + self.F.T

@dataclass
class Result:
    method: str                      # "bruteforce" | "sa" | "qaoa" | "hybrid_lns" | ...
    perm: tuple[int, ...] | None     # perm[i] = gate of flight i; None if no feasible solution found
    cost: int | None                 # TRUE cost of perm (never the penalized energy)
    feasible: bool
    seconds: float; peak_mem_mb: float; seed: int | None
    params: dict                     # everything needed to reproduce (reps, lambda, maxiter, shots, k, ...)
    extras: dict                     # penalized_energy, feasible_fraction, history, repaired, ...
```
- `cost(perm, inst)` = Σ_{i<k} F[i,k]·D[perm[i], perm[k]] — **the single source of truth for scale** (each pair once).
  A vectorized version `costs(perms_2d, inst)` for many permutations.
- Solver signature for every method: `solve_xxx(inst: Instance, *, seed: int, **params) -> Result`.
- Variable order convention for QUBO: `x_{i}_{j}` named `f"x_{i}_{j}"`, flattened index `i*n + j`.
- Benchmark CSV schema (`results/benchmark.csv`):
  `instance,n,method,seed,cost,feasible,gap_pct,seconds,peak_mem_mb,feasible_fraction,penalized_energy,params_json`.
  `gap_pct = 100·(cost−340)/340` **only when feasible and n=10**; for other n use the brute-force optimum as reference.
- Stubs raising `NotImplementedError` for every solver + `tests/` with the control values (24 / 32 / 340) marked as the
  acceptance tests each owner must turn green.
