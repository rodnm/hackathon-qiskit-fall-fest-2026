# PART 2 — Diego: MODELS (QUBO/Ising, QAOA, hybrid decomposition)

**You own:** `src/qap/model.py`, `quantum.py`, `tests/test_model.py`, `tests/test_quantum.py`, `notebooks/02_qiskit.ipynb`,
`docs/figures/lambda_*.png`, `docs/figures/qaoa_*.png`.
**You depend on:** Step 0 contracts + `load_instance` (T+0:45). Until then, hard-code the first 4×4 of F and D from the
README/notebook to start the spike.
**You deliver:** spike verdict (T+0:30), `model.py` (T+1:00), N=3/4 QAOA (T+1:45), hybrid for N=10 (T+2:30).

### M1. Spike: which QAOA path? (0:00–0:30)
Question: does `qiskit_algorithms.QAOA(sampler=<Aer SamplerV2>, …)` run in a few seconds for N=3 and N=4?
- If yes → use `MinimumEigenOptimizer(QAOA(...))` (least code, most "standard Qiskit").
- If not → **fallback (known to work)**: `QAOAAnsatz(cost_operator=op, reps=p)` + `qiskit_aer.primitives.EstimatorV2`
  for the energy + `scipy.optimize.minimize(method="COBYLA")` over `(β, γ)`; then sample the final circuit with Aer
  `SamplerV2` (needs `measure_all`) and decode bitstrings. Measured: 0.07 s per energy evaluation at 16 qubits.
Never use the reference `StatevectorSampler/Estimator` for N ≥ 4 (87 s for N=3).

### M2. Model — `model.py` (0:30–1:00)
- `build_qp(inst) -> QuadraticProgram`: binary vars `x_{i}_{j}`; objective quadratic coefficients
  `F[i,k]·D[j,l]` for `i<k`, `j≠l`; equality constraints (each row sum = 1, each column sum = 1).
- `to_qubo(qp, lam) -> QuadraticProgram` via `QuadraticProgramToQubo(penalty=lam)`; `to_ising(qubo) -> (SparsePauliOp, offset)`.
  Relation (x = (1−Z)/2): `⟨op⟩ + offset` = penalized QUBO energy.
- Helpers: `decode(bitstring, n) -> perm | None` (None if not a permutation matrix), `is_feasible`,
  `true_cost(perm, inst)` (reuse `cost()`), `penalized_energy(x, qubo)`.
- **Qiskit bit-order trap:** a measured bitstring is little-endian (rightmost char = qubit 0). Reverse it before mapping
  to `x_{i}_{j}` (index `i*n+j`). Test this explicitly.
- Report the **penalized energy and the true feasible cost as different fields** (`Result.extras`, required by the challenge).

### M3. Model tests — `tests/test_model.py`
- For N=3 and N=4: enumerate all 2^(N²) bitstrings with numpy (512 / 65 536). Assert: (a) for every permutation the QUBO
  energy equals `cost(perm)` (penalty term is zero on feasible points); (b) for λ above the threshold, the argmin of
  the QUBO energy is a feasible optimal permutation (cost 24 / 32).

### M4. λ study (1:00–1:30) — the justification of the penalty
Exact threshold, cheap for N=3/4 (and N=5 chunked): `λ* = max over infeasible x of (C_opt − C(x)) / P(x)` where
`P(x) = Σ_i(Σ_j x_ij − 1)² + Σ_j(Σ_i x_ij − 1)²`. For λ > λ*, the QUBO ground state is feasible and optimal.
Choose `λ = 1.5–2 × λ*`; extrapolate the order of magnitude to N=10 (expect tens). Plot (`docs/figures/lambda_*.png`):
(1) λ* vs N, (2) for N=3/4 QAOA: feasible fraction and best feasible cost vs λ ∈ {0.5, 1, 2, 4}×λ*.
Message: too small → infeasible optimum; too large → flat landscape QAOA struggles. This is what the jury asks
("justifica su valor y comprueba la factibilidad").

### M5. Full QAOA on small N — `quantum.py: solve_qaoa` (1:00–1:45)
- N=3 (9 qubits) and N=4 (16 qubits). N=5 (25 qubits) only if time and only with Aer MPS/statevector check of memory.
- Params to record: `reps` ∈ {1, 2, 3}, optimizer COBYLA `maxiter` ≈ 100–200, `shots` = 4096, initial `(β, γ)` small
  and fixed per seed, seeds 0–4.
- Metrics (put in `Result.extras`): best **feasible** cost among samples, **feasible fraction** of shots,
  probability of sampling the optimal permutation, final penalized energy, iterations history, time.
  Compare with brute force (24 / 32). A QAOA that finds the optimum with a tiny feasible fraction is still worth reporting honestly.
- Circuit facts for the slides: qubits, depth, 2-qubit gate count after `transpile` (optionally to a fake backend).

### M6. Hybrid decomposition for N=10 (and N ≥ 14) — `quantum.py: solve_hybrid_lns` (1:45–2:30)
Large-neighborhood search with a QAOA subsolver (this is the challenge's own suggestion: "subinstancias, fijar decisiones,
optimizar vecindarios, reconstruir una asignación completa").
```
start: p = best of a quick classical heuristic or a random permutation  (record which one; seed it)
repeat T times (T ≈ 30):
    S = k flights  (k=3 → 9 qubits, k=4 → 16 qubits); choose randomly, or a flight + its heaviest-flow partners
    G = {p[i] for i in S}                      # the gates those flights currently use
    sub-problem variables y[i,g], i∈S, g∈G, one-hot rows/cols (k×k)
    cost(y) = Σ_{i<m in S} F[i,m]·D[g,g']·y[i,g]·y[m,g']                      # interactions inside S
            + Σ_{i∈S, m∉S} F_sym[i,m]·D[g, p[m]]·y[i,g]                      # linear: interaction with fixed flights
    build QUBO with λ_sub, run QAOA (Aer), take best FEASIBLE sample → new p'
    accept if cost(p') < cost(p)             # always evaluate with the global cost()
```
- Ablation (important for the jury): solve the **same** sub-problems by exact enumeration (k! ≤ 24 options). Expected:
  QAOA matches it at best; the subproblem is too small for quantum to add anything. Report this plainly.
- Record per run: final cost, gap vs 340, number of neighborhoods improved, feasible fraction per subproblem, total time.
- N ≥ 14: same code on synthetic instances (from Rodrigo's `make_synthetic`), k unchanged.

### M7. Stretch (only if everything above is green)
Warm-start QAOA from the best classical solution; classical repair of infeasible samples (**report original and repaired
results separately**); noisy simulation with an Aer noise model.

**Pitfalls:** don't confuse penalized energy and true cost; always re-evaluate candidates with `cost()`; fix seeds
(optimizer init, sampler seed, neighborhood choice); keep `reps` small (circuit depth grows with the number of Pauli terms).

**Your definition of done:** model tests green; `solve_qaoa` N=3/4 reproduces 24/32 (or documents why not);
λ figures committed; `solve_hybrid_lns` N=10 results in `results/benchmark.csv` with the ablation.
