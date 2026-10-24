"""Spike M1 - Camino A: MinimumEigenOptimizer(QAOA(sampler=Aer SamplerV2)).

Vía automática / alto nivel: se le pasa el QuadraticProgram y la librería construye el circuito,
lanza el optimizador clásico y devuelve la solución. Pregunta: ¿resuelve N=3 y N=4 en 2-5 s?

Uso:
    uv run python src/spike/spike_qaoa_camino_a.py
    uv run python src/spike/spike_qaoa_camino_a.py --n 3 4 --reps 1 2 --maxiter 100 --seed 0
"""

from __future__ import annotations

import argparse
import time

import numpy as np
from qiskit.result import QuasiDistribution
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo
from spike_common import brute_force, build_qp, cost, decode, make_instance, print_report


class QAOAQuasi(QAOA):
    """QAOA (qiskit-algorithms 0.4, SamplerV2) devuelve `eigenstate` como dict de probabilidades,
    pero MinimumEigenOptimizer (qiskit-optimization 0.7) trata los dict como amplitudes y las eleva
    al cuadrado: con N=4 todas caen bajo 1e-6 y solve() revienta. Lo envolvemos en QuasiDistribution."""

    def compute_minimum_eigenvalue(self, operator, aux_operators=None):
        result = super().compute_minimum_eigenvalue(operator, aux_operators)
        if isinstance(result.eigenstate, dict):
            result.eigenstate = QuasiDistribution(result.eigenstate)
        return result


def run(n: int, reps: int, maxiter: int, shots: int, seed: int, penalty: float | None) -> dict:
    inst = make_instance(n)
    qp = build_qp(inst)
    qubo = QuadraticProgramToQubo(penalty=penalty).convert(qp)
    op, offset = qubo.to_ising()

    algorithm_globals.random_seed = seed
    backend = AerSimulator(seed_simulator=seed)
    sampler = SamplerV2(default_shots=shots, seed=seed)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)

    history: list[float] = []
    qaoa = QAOAQuasi(
        sampler=sampler,
        optimizer=COBYLA(maxiter=maxiter),
        reps=reps,
        initial_point=np.full(2 * reps, 0.1),
        callback=lambda _count, _params, value, _meta: history.append(float(value)),
        transpiler=pm,
    )

    t0 = time.perf_counter()
    result = MinimumEigenOptimizer(qaoa).solve(qp)
    seconds = time.perf_counter() - t0

    perm = decode(result.x, n)
    feasible_prob = 0.0
    optimal_prob = 0.0
    best_feasible = None
    for s in result.samples:
        p = decode(s.x, n)
        if p is None:
            continue
        feasible_prob += s.probability
        c = cost(p, inst)
        best_feasible = c if best_feasible is None else min(best_feasible, c)
        if c == inst.optimum:
            optimal_prob += s.probability

    return {
        "method": "camino_a_min_eigen_optimizer",
        "n": n,
        "qubits": op.num_qubits,
        "pauli_terms": len(op),
        "penalty": "auto" if penalty is None else penalty,
        "reps": reps,
        "seed": seed,
        "seconds": seconds,
        "evals": len(history),
        "status": result.status.name,
        "perm": perm,
        "cost": cost(perm, inst) if perm is not None else None,
        "penalized_energy": float(result.fval),
        "best_feasible_cost": best_feasible,
        "feasible_fraction": feasible_prob,
        "optimal_prob": optimal_prob,
        "optimum": inst.optimum,
        "brute_force": brute_force(inst),
        "offset": offset,
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
