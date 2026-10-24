"""Piezas compartidas por los spikes de QAOA (camino A y camino B): instancia, modelo y decodificación."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
from qiskit_optimization import QuadraticProgram

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qap.types import Instance, cost  # noqa: E402

# Primeros 4x4 de qap10 (salida de src/analyze_qap10.py). F triangular superior.
F4 = np.array(
    [
        [0, 10, 4, 8],
        [0, 0, 6, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
)
D4 = np.array(
    [
        [0, 1, 2, 3],
        [1, 0, 1, 2],
        [2, 1, 0, 1],
        [3, 2, 1, 0],
    ]
)
OPTIMA = {3: 24, 4: 32}


def make_instance(n: int) -> Instance:
    return Instance(f"qap10[:{n}]", n, F4[:n, :n].copy(), D4[:n, :n].copy(), OPTIMA[n])


def build_qp(inst: Instance) -> QuadraticProgram:
    n = inst.n
    qp = QuadraticProgram(inst.name)
    for i in range(n):
        for j in range(n):
            qp.binary_var(f"x_{i}_{j}")
    quadratic = {}
    for i in range(n):
        for k in range(i + 1, n):
            if not inst.F[i, k]:
                continue
            for j in range(n):
                for l in range(n):
                    if j != l and inst.D[j, l]:
                        quadratic[(f"x_{i}_{j}", f"x_{k}_{l}")] = int(inst.F[i, k] * inst.D[j, l])
    qp.minimize(quadratic=quadratic)
    for i in range(n):
        qp.linear_constraint({f"x_{i}_{j}": 1 for j in range(n)}, "==", 1, f"row_{i}")
    for j in range(n):
        qp.linear_constraint({f"x_{i}_{j}": 1 for i in range(n)}, "==", 1, f"col_{j}")
    return qp


def decode(x: np.ndarray, n: int) -> tuple[int, ...] | None:
    """x en el orden de variables de qp (índice i*n+j) -> perm, o None si no es permutación."""
    m = np.rint(np.asarray(x)).astype(int).reshape(n, n)
    if not (np.all(m.sum(axis=0) == 1) and np.all(m.sum(axis=1) == 1)):
        return None
    return tuple(int(j) for j in m.argmax(axis=1))


def bitstring_to_x(bitstring: str) -> np.ndarray:
    """Las cadenas medidas en Qiskit son little-endian (el carácter más a la derecha = qubit 0)."""
    return np.fromiter(bitstring[::-1], dtype=int)


def brute_force(inst: Instance) -> int:
    return min(cost(p, inst) for p in itertools.permutations(range(inst.n)))


def print_report(r: dict, limit_s: float = 5.0) -> None:
    print(f"\n=== N={r['n']}  reps={r['reps']}  ({r['qubits']} qubits, {r['pauli_terms']} términos) ===")
    for key, value in r.items():
        if key != "history":
            print(f"  {key:>20}: {value}")
    verdict = "OK" if r["seconds"] <= limit_s else "LENTO"
    print(f"  {'veredicto':>20}: {r['seconds']:.2f} s -> {verdict} (límite {limit_s:.0f} s)")
