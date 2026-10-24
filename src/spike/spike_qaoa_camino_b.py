"""Spike M1 - Camino B: bucle variacional artesanal.

1. Circuito: QAOAAnsatz(cost_operator=H, reps=p).
2. Energía: qiskit_aer.primitives.EstimatorV2 (C++; precisión 0 = valor esperado exacto).
3. Optimizador clásico: scipy.optimize.minimize(method="COBYLA") sobre (β, γ).
4. Medición final: una sola ejecución con Aer SamplerV2 (4096 shots) y decodificación de bitstrings.

Nunca StatevectorSampler/StatevectorEstimator de referencia (Python puro: 87 s con N=3).

Uso:
    uv run python src/spike/spike_qaoa_camino_b.py
    uv run python src/spike/spike_qaoa_camino_b.py --n 3 4 --reps 1 2 --maxiter 150 --seed 0 --penalty 20
"""

from __future__ import annotations

import argparse
import time

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import EstimatorV2, SamplerV2
from qiskit_optimization.converters import QuadraticProgramToQubo
from scipy.optimize import minimize
from spike_common import (
    bitstring_to_x,
    brute_force,
    build_qp,
    cost,
    decode,
    make_instance,
    print_report,
)


def run(n: int, reps: int, maxiter: int, shots: int, seed: int, penalty: float | None) -> dict:
    inst = make_instance(n)
    qp = build_qp(inst)
    qubo = QuadraticProgramToQubo(penalty=penalty).convert(qp)
    assert qubo.get_num_vars() == n * n, "el QUBO no debería tener variables de holgura"
    op, offset = qubo.to_ising()

    t0 = time.perf_counter()

    # 1. Circuito
    ansatz = QAOAAnsatz(cost_operator=op, reps=reps)
    pm = generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())
    isa = pm.run(ansatz)
    isa_op = op.apply_layout(isa.layout)

    # 2. Energía con Aer EstimatorV2 (exacta, determinista)
    estimator = EstimatorV2(options={"default_precision": 0.0})
    history: list[float] = []

    def energy(theta: np.ndarray) -> float:
        ev = float(estimator.run([(isa, isa_op, theta)]).result()[0].data.evs)
        history.append(ev + offset)
        return ev

    # 3. COBYLA de scipy sobre los parámetros (orden de isa.parameters: β..., γ...)
    rng = np.random.default_rng(seed)
    x0 = 0.1 + 0.01 * rng.standard_normal(isa.num_parameters)
    t_opt = time.perf_counter()
    opt = minimize(energy, x0, method="COBYLA", options={"maxiter": maxiter})
    opt_seconds = time.perf_counter() - t_opt

    # 4. Medición final con Aer SamplerV2
    measured = pm.run(ansatz.measure_all(inplace=False))
    sampler = SamplerV2(default_shots=shots, seed=seed)
    counts = sampler.run([(measured, opt.x)]).result()[0].data.meas.get_counts()
    seconds = time.perf_counter() - t0

    feasible_shots = 0
    optimal_shots = 0
    best_perm, best_cost = None, None
    for bitstring, c in counts.items():
        perm = decode(bitstring_to_x(bitstring), n)
        if perm is None:
            continue
        feasible_shots += c
        perm_cost = cost(perm, inst)
        if perm_cost == inst.optimum:
            optimal_shots += c
        if best_cost is None or perm_cost < best_cost:
            best_perm, best_cost = perm, perm_cost

    top = max(counts, key=counts.get)
    top_x = bitstring_to_x(top)

    return {
        "method": "camino_b_ansatz_estimator_scipy",
        "n": n,
        "qubits": op.num_qubits,
        "pauli_terms": len(op),
        "penalty": "auto" if penalty is None else penalty,
        "reps": reps,
        "seed": seed,
        "seconds": seconds,
        "optimizer_seconds": opt_seconds,
        "evals": len(history),
        "sec_per_eval": opt_seconds / max(len(history), 1),
        "depth": isa.depth(),
        "two_qubit_gates": sum(1 for inst_ in isa.data if inst_.operation.num_qubits == 2),
        "perm": best_perm,
        "cost": best_cost,
        "final_energy": float(opt.fun + offset),
        "top_sample_energy": float(qubo.objective.evaluate(top_x)),
        "top_sample_feasible": decode(top_x, n) is not None,
        "feasible_fraction": feasible_shots / shots,
        "optimal_prob": optimal_shots / shots,
        "optimum": inst.optimum,
        "brute_force": brute_force(inst),
        "offset": offset,
        "history": history,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, nargs="+", default=[3, 4], choices=[3, 4])
    parser.add_argument("--reps", type=int, nargs="+", default=[1])
    parser.add_argument("--maxiter", type=int, default=100)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--penalty", type=float, default=None, help="λ; por defecto el automático")
    args = parser.parse_args()

    for n in args.n:
        for reps in args.reps:
            print_report(run(n, reps, args.maxiter, args.shots, args.seed, args.penalty))


if __name__ == "__main__":
    main()
