"""Qiskit-based solvers. Owner: Diego.

QAOA is built by hand (camino B): QAOAAnsatz + Aer EstimatorV2 + scipy COBYLA, then a single
SamplerV2 run. Measured 0.02-0.12 s per energy evaluation for 9-16 qubits. Never use the
reference StatevectorSampler/StatevectorEstimator (87 s for N=3).

`run_qaoa` works on any QUBO (full instance or LNS sub-problem); `solve_qaoa` and
`solve_hybrid_lns` wrap it and always re-evaluate candidates with the global `cost()`.
"""

from __future__ import annotations

import itertools
import time
import tracemalloc
from functools import lru_cache

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import EstimatorV2, SamplerV2
from qiskit_optimization import QuadraticProgram
from scipy.optimize import minimize

from .model import (
    build_qp,
    build_subproblem,
    decode_x,
    default_penalty,
    is_feasible,
    penalized_energy,
    qp_penalty_threshold,
    to_ising,
    to_qubo,
    x_from_bits,
)
from .types import Instance, Result, cost, costs


@lru_cache(maxsize=1)
def _pass_manager():
    return generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())


def run_qaoa(
    qubo: QuadraticProgram,
    *,
    seed: int,
    reps: int = 1,
    maxiter: int = 100,
    shots: int = 4096,
    initial_point: np.ndarray | None = None,
    normalize: bool = True,
    init: str = "grid",
) -> tuple[dict[str, int], dict]:
    """Optimize QAOA angles on the QUBO's Ising operator and sample the final circuit.

    normalize=True divides the cost operator by its largest |coefficient| before building the
    ansatz, so γ lives on a scale where COBYLA can move (with raw coefficients of tens, γ = 0.1
    already wraps the phases several times). Energies in `info` are always in QUBO units.
    init="grid" starts COBYLA from the best point of an 8×8 grid over (β, γ) (same angles in every
    layer, one batched Estimator call); init="fixed" starts near (0.1, 0.1) with seeded noise.
    Returns (counts with Qiskit little-endian bitstrings, info).
    """
    op, offset = to_ising(qubo)
    scale = float(np.max(np.abs(op.coeffs.real))) if normalize else 1.0
    cost_op = (op / scale).simplify()

    ansatz = QAOAAnsatz(cost_operator=cost_op, reps=reps)
    pm = _pass_manager()
    isa = pm.run(ansatz)
    isa_op = cost_op.apply_layout(isa.layout)

    # default_precision=0 -> exact expectation value (statevector), no shot noise in the loop
    estimator = EstimatorV2(options={"default_precision": 0.0})
    history: list[float] = []

    def energy(theta: np.ndarray) -> float:
        ev = float(estimator.run([(isa, isa_op, theta)]).result()[0].data.evs)
        history.append(ev * scale + offset)
        return ev

    grid_evals = 0
    if initial_point is None and init == "grid":
        # QAOAAnsatz parameter order is [β_0..β_{p-1}, γ_0..γ_{p-1}]
        betas = np.linspace(0, np.pi / 2, 9)[1:]
        gammas = np.linspace(0, np.pi, 9)[1:]
        points = np.array([[b] * reps + [g] * reps for b in betas for g in gammas])
        evs = np.asarray(estimator.run([(isa, isa_op, points)]).result()[0].data.evs)
        initial_point = points[int(np.argmin(evs))]
        grid_evals = len(points)
    elif initial_point is None and init == "fixed":
        rng = np.random.default_rng(seed)
        initial_point = 0.1 + 0.01 * rng.standard_normal(isa.num_parameters)
    elif initial_point is None:
        raise ValueError(f"unknown init {init!r}")
    initial_point = np.asarray(initial_point, dtype=float)
    opt = minimize(energy, initial_point, method="COBYLA", options={"maxiter": maxiter})

    measured = pm.run(ansatz.measure_all(inplace=False))
    sampler = SamplerV2(default_shots=shots, seed=seed)
    counts = sampler.run([(measured, opt.x)]).result()[0].data.meas.get_counts()

    info = {
        "initial_point": [float(v) for v in initial_point],
        "final_point": [float(v) for v in opt.x],
        "qubits": op.num_qubits,
        "pauli_terms": len(op),
        "depth": isa.depth(),
        "two_qubit_gates": sum(1 for instr in isa.data if instr.operation.num_qubits == 2),
        "offset": offset,
        "operator_scale": scale,
        "penalized_energy": float(opt.fun * scale + offset),
        "history": history,
        "nfev": len(history),
        "grid_evals": grid_evals,
    }
    return counts, info


def solve_qaoa(
    inst: Instance,
    *,
    seed: int,
    reps: int = 1,
    maxiter: int = 100,
    shots: int = 4096,
    penalty: float | None = None,
    initial_point: np.ndarray | None = None,
    normalize: bool = True,
    init: str = "grid",
) -> Result:
    """QAOA on the penalized QUBO of the full instance (n <= 4 in practice: n² qubits).

    Cost is always the real cost of the best feasible sample; extras keep the penalized energy.
    penalty=None uses `default_penalty` (2·λ* for n <= 4) instead of qiskit-optimization's automatic
    penalty, which is far above the threshold and flattens the landscape.
    Peak memory only covers Python allocations (Aer's C++ statevector is not traced).
    """
    if penalty is None:
        penalty, penalty_rule = default_penalty(inst)
    else:
        penalty_rule = "explicit"
    qubo = to_qubo(build_qp(inst), penalty)

    tracemalloc.start()
    t0 = time.perf_counter()
    counts, info = run_qaoa(
        qubo,
        seed=seed,
        reps=reps,
        maxiter=maxiter,
        shots=shots,
        initial_point=initial_point,
        normalize=normalize,
        init=init,
    )
    seconds = time.perf_counter() - t0
    peak_mb = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()

    best_perm, best_cost = None, None
    feasible_shots = optimal_shots = 0
    for bitstring, hits in counts.items():
        perm = decode_x(x_from_bits(bitstring), inst.n)
        if not is_feasible(perm, inst.n):
            continue
        feasible_shots += hits
        perm_cost = cost(perm, inst)
        if inst.optimum is not None and perm_cost == inst.optimum:
            optimal_shots += hits
        if best_cost is None or perm_cost < best_cost:
            best_perm, best_cost = perm, perm_cost

    top = max(counts, key=counts.get)
    initial = info.pop("initial_point")
    return Result(
        method="qaoa",
        perm=best_perm,
        cost=best_cost,
        feasible=best_perm is not None,
        seconds=seconds,
        peak_mem_mb=peak_mb,
        seed=seed,
        params={
            "reps": reps,
            "maxiter": maxiter,
            "shots": shots,
            "penalty": float(penalty),
            "penalty_rule": penalty_rule,
            "normalize": normalize,
            "init": init,
            "initial_point": initial,
        },
        extras={
            **info,
            "best_feasible_cost": best_cost,
            "feasible_fraction": feasible_shots / shots,
            "optimal_prob": optimal_shots / shots,
            "top_sample_energy": penalized_energy(x_from_bits(top), qubo),
            "top_sample_feasible": is_feasible(decode_x(x_from_bits(top), inst.n), inst.n),
        },
    )


def choose_neighborhood(
    inst: Instance, k: int, rng: np.random.Generator, rule: str = "random"
) -> tuple[int, ...]:
    """k flights to re-optimize: uniformly at random, or a random flight + its heaviest partners."""
    if rule == "random":
        return tuple(sorted(int(i) for i in rng.choice(inst.n, size=k, replace=False)))
    if rule == "flow":
        anchor = int(rng.integers(inst.n))
        weight = inst.F_sym[anchor].astype(float) + 1e-3 * rng.random(inst.n)  # random tie-break
        weight[anchor] = -np.inf
        partners = np.argsort(weight)[::-1][: k - 1]
        return tuple(sorted([anchor, *(int(i) for i in partners)]))
    raise ValueError(f"unknown neighborhood rule {rule!r}")


def _reassign(perm: tuple[int, ...], flights: tuple[int, ...], gates: tuple[int, ...],
              local: tuple[int, ...]) -> tuple[int, ...]:
    """New global perm: flight flights[a] goes to gate gates[local[a]], the rest stay."""
    new = list(perm)
    for a, b in enumerate(local):
        new[flights[a]] = gates[b]
    return tuple(new)


def solve_hybrid_lns(
    inst: Instance,
    *,
    seed: int,
    k: int = 3,
    iterations: int = 30,
    subsolver: str = "qaoa",
    neighborhood: str = "random",
    start: str = "random",
    reps: int = 1,
    maxiter: int = 100,
    shots: int = 1024,
    penalty_factor: float = 2.0,
    normalize: bool = True,
    init: str = "grid",
) -> Result:
    """Large-neighborhood search: re-optimize k flights at a time, the rest fixed.

    Each sub-problem is a k×k QAP with a linear term (interaction with the fixed flights), built as
    a QuadraticProgram (`build_subproblem`); its penalty is penalty_factor·λ*_sub, with λ*_sub exact
    by enumerating the 2^(k²) vectors. subsolver="qaoa" solves it with `run_qaoa` (k² qubits) and
    keeps the best feasible sample; subsolver="exact" enumerates the k! reassignments. Every step
    also solves the same sub-problem exactly (ablation: did QAOA find the sub-optimum?). A move is
    accepted only if the global cost() strictly decreases.
    """
    if subsolver not in {"qaoa", "exact"}:
        raise ValueError(f"unknown subsolver {subsolver!r}")
    if not 2 <= k <= min(4, inst.n):
        raise ValueError("k must be between 2 and min(4, n): k² qubits per sub-problem")
    rng = np.random.default_rng(seed)
    if start == "random":
        current = tuple(int(g) for g in rng.permutation(inst.n))
    elif start == "identity":
        current = tuple(range(inst.n))
    else:
        raise ValueError(f"unknown start {start!r}")
    local_perms = list(itertools.permutations(range(k)))

    tracemalloc.start()
    t0 = time.perf_counter()
    start_perm, current_cost = current, cost(current, inst)
    steps: list[dict] = []
    qaoa_seconds = 0.0
    for step in range(iterations):
        flights = choose_neighborhood(inst, k, rng, neighborhood)
        qp, gates = build_subproblem(inst, current, flights)

        # exact reference for the same sub-problem: all k! reassignments, global cost()
        candidates = np.array([_reassign(current, flights, gates, p) for p in local_perms])
        candidate_costs = costs(candidates, inst)
        exact_best = int(candidate_costs.min())
        record = {"step": step, "flights": list(flights), "cost_before": current_cost,
                  "exact_sub_best": exact_best}

        if subsolver == "exact":
            best = int(candidate_costs.argmin())
            new_perm, new_cost = tuple(int(g) for g in candidates[best]), exact_best
        else:
            lam = max(penalty_factor * qp_penalty_threshold(qp, k), 1.0)
            t_q = time.perf_counter()
            counts, info = run_qaoa(to_qubo(qp, lam), seed=seed * 1000 + step, reps=reps,
                                    maxiter=maxiter, shots=shots, normalize=normalize, init=init)
            qaoa_seconds += time.perf_counter() - t_q
            new_perm, new_cost, feasible_shots, optimal_shots = None, None, 0, 0
            for bitstring, hits in counts.items():
                local = decode_x(x_from_bits(bitstring), k)
                if local is None:
                    continue
                feasible_shots += hits
                perm = _reassign(current, flights, gates, local)
                perm_cost = cost(perm, inst)
                optimal_shots += hits * (perm_cost == exact_best)
                if new_cost is None or perm_cost < new_cost:
                    new_perm, new_cost = perm, perm_cost
            record.update(
                lambda_sub=lam,
                feasible_fraction=feasible_shots / shots,
                sub_optimum_prob=optimal_shots / shots,
                qaoa_found_sub_optimum=new_cost == exact_best,
                qubits=info["qubits"],
                depth=info["depth"],
                two_qubit_gates=info["two_qubit_gates"],
            )

        accepted = new_cost is not None and new_cost < current_cost
        if accepted:
            current, current_cost = new_perm, new_cost
        record.update(candidate_cost=new_cost, accepted=accepted, cost_after=current_cost)
        steps.append(record)

    seconds = time.perf_counter() - t0
    peak_mb = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()

    extras = {
        "start": start,
        "start_perm": list(start_perm),
        "start_cost": cost(start_perm, inst),
        "improved_neighborhoods": sum(s["accepted"] for s in steps),
        "exact_could_improve": sum(s["exact_sub_best"] < s["cost_before"] for s in steps),
        "cost_trace": [s["cost_after"] for s in steps],
        "steps": steps,
    }
    if subsolver == "qaoa":
        extras.update(
            feasible_fraction=float(np.mean([s["feasible_fraction"] for s in steps])),
            sub_optimum_match_rate=float(np.mean([s["qaoa_found_sub_optimum"] for s in steps])),
            sub_optimum_prob=float(np.mean([s["sub_optimum_prob"] for s in steps])),
            no_feasible_sample=sum(s["candidate_cost"] is None for s in steps),
            qaoa_seconds=qaoa_seconds,
            qubits=k * k,
        )
    return Result(
        method="hybrid_lns" if subsolver == "qaoa" else "hybrid_lns_exact",
        perm=current,
        cost=current_cost,
        feasible=True,
        seconds=seconds,
        peak_mem_mb=peak_mb,
        seed=seed,
        params={
            "k": k,
            "iterations": iterations,
            "subsolver": subsolver,
            "neighborhood": neighborhood,
            "start": start,
            "reps": reps,
            "maxiter": maxiter,
            "shots": shots,
            "penalty_factor": penalty_factor,
            "normalize": normalize,
        },
        extras=extras,
    )
