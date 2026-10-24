"""Qiskit-based solvers. Owner: Diego.

QAOA is built by hand (camino B): QAOAAnsatz + Aer EstimatorV2 + scipy COBYLA, then a single
SamplerV2 run. Measured 0.02-0.12 s per energy evaluation for 9-16 qubits. Never use the
reference StatevectorSampler/StatevectorEstimator (87 s for N=3).
"""

from __future__ import annotations

import time
import tracemalloc

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import EstimatorV2, SamplerV2
from scipy.optimize import minimize

from .model import (
    build_qp,
    decode_x,
    is_feasible,
    penalized_energy,
    to_ising,
    to_qubo,
    x_from_bits,
)
from .types import Instance, Result, cost


def solve_qaoa(
    inst: Instance,
    *,
    seed: int,
    reps: int = 1,
    maxiter: int = 100,
    shots: int = 4096,
    penalty: float | None = None,
    initial_point: np.ndarray | None = None,
) -> Result:
    """QAOA on the penalized QUBO. Cost is always the real cost; extras keep the energy."""
    qp = build_qp(inst)
    qubo = to_qubo(qp, penalty)
    op, offset = to_ising(qubo)

    tracemalloc.start()
    t0 = time.perf_counter()

    ansatz = QAOAAnsatz(cost_operator=op, reps=reps)
    pm = generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())
    isa = pm.run(ansatz)
    isa_op = op.apply_layout(isa.layout)

    # default_precision=0 -> exact expectation value (statevector), no shot noise in the loop
    estimator = EstimatorV2(options={"default_precision": 0.0})
    history: list[float] = []

    def energy(theta: np.ndarray) -> float:
        ev = float(estimator.run([(isa, isa_op, theta)]).result()[0].data.evs)
        history.append(ev + offset)
        return ev

    if initial_point is None:
        rng = np.random.default_rng(seed)
        initial_point = 0.1 + 0.01 * rng.standard_normal(isa.num_parameters)
    opt = minimize(
        energy, np.asarray(initial_point), method="COBYLA", options={"maxiter": maxiter}
    )

    measured = pm.run(ansatz.measure_all(inplace=False))
    sampler = SamplerV2(default_shots=shots, seed=seed)
    counts = sampler.run([(measured, opt.x)]).result()[0].data.meas.get_counts()

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
            "penalty": penalty,
            "initial_point": [float(v) for v in opt.x],
        },
        extras={
            "qubits": op.num_qubits,
            "pauli_terms": len(op),
            "depth": isa.depth(),
            "two_qubit_gates": sum(1 for instr in isa.data if instr.operation.num_qubits == 2),
            "offset": offset,
            "penalized_energy": float(opt.fun + offset),
            "best_feasible_cost": best_cost,
            "feasible_fraction": feasible_shots / shots,
            "optimal_prob": optimal_shots / shots,
            "top_sample_energy": penalized_energy(x_from_bits(top), qubo),
            "top_sample_feasible": is_feasible(decode_x(x_from_bits(top), inst.n), inst.n),
            "history": history,
            "nfev": len(history),
            "bruteforce": None,
        },
    )


def solve_hybrid_lns(inst: Instance, *, seed: int, **params) -> Result:
    raise NotImplementedError
