"""QUBO/Ising model for the gate assignment problem. Owner: Diego."""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import SparsePauliOp
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

from .types import Instance, cost


def build_qp(inst: Instance) -> QuadraticProgram:
    """x_{i}_{j} binary, min Σ_{i<k} F[i,k]·D[j,l]·x_ij·x_kl, one-hot rows and columns."""
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


def to_qubo(qp: QuadraticProgram, lam: float | None = None) -> QuadraticProgram:
    """Penalize the equality constraints; lam=None lets qiskit-optimization choose the penalty."""
    return QuadraticProgramToQubo(penalty=lam).convert(qp)


def to_ising(qubo: QuadraticProgram) -> tuple[SparsePauliOp, float]:
    """Return (operator, offset) with ⟨op⟩ + offset = penalized QUBO energy (x = (1 − Z)/2)."""
    op, offset = qubo.to_ising()
    return op, float(offset)


def decode(bitstring: str, n: int) -> tuple[int, ...] | None:
    """Measured bitstring (Qiskit: rightmost char = qubit 0) -> perm, or None if not a permutation."""
    try:
        return decode_x(x_from_bits(bitstring), n)
    except Exception:
        return None


def x_from_bits(bitstring: str) -> np.ndarray:
    """Little-endian bitstring -> binary vector in variable order (index i*n+j)."""
    return np.fromiter(bitstring[::-1], dtype=int)


def decode_x(x: np.ndarray, n: int) -> tuple[int, ...] | None:
    """Binary vector in variable order -> perm[i] = gate of flight i, or None if infeasible."""
    m = np.rint(np.asarray(x)).astype(int).reshape(n, n)
    if not (np.all(m.sum(axis=0) == 1) and np.all(m.sum(axis=1) == 1)):
        return None
    return tuple(int(j) for j in m.argmax(axis=1))


def is_feasible(perm: tuple[int, ...] | None, n: int) -> bool:
    """True if perm is a permutation of 0..n-1."""
    return perm is not None and len(perm) == n and sorted(perm) == list(range(n))


def true_cost(perm: tuple[int, ...], inst: Instance) -> int:
    """Real walking distance; always use this, never the penalized energy."""
    return cost(perm, inst)


def penalized_energy(x: np.ndarray, qubo: QuadraticProgram) -> float:
    return float(qubo.objective.evaluate(np.asarray(x)))


def penalty_threshold(inst: Instance) -> float:
    """λ* = max over infeasible x of (C_opt − C(x)) / P(x), with P the constraint violation.

    For λ > λ* the QUBO ground state is feasible and optimal. Exact enumeration: only for n <= 4.
    """
    if inst.n > 4:
        raise ValueError("penalty_threshold enumerates 2^(n²); use block decomposition for n >= 5")
    n = inst.n
    i_all, k_all = np.triu_indices(n, 1)
    bits = ((np.arange(2 ** (n * n))[:, None] >> np.arange(n * n)) & 1).astype(np.int8)
    x = bits.reshape(-1, n, n)
    rows = x.sum(axis=2)
    cols = x.sum(axis=1)
    violation = ((rows - 1) ** 2).sum(axis=1) + ((cols - 1) ** 2).sum(axis=1)
    feasible = violation == 0
    # perm[i] = gate of flight i
    perm = x.argmax(axis=2)
    objective = (inst.F[i_all, k_all][None, :] * inst.D[perm[:, i_all], perm[:, k_all]]).sum(axis=1)
    optimum = objective[feasible].min()
    infeasible = ~feasible
    return float(np.max((optimum - objective[infeasible]) / np.maximum(violation[infeasible], 1)))
