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
    if len(bitstring) != n * n:
        return None
    return decode_x(x_from_bits(bitstring), n)


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


def penalized_energies(xs: np.ndarray, qubo: QuadraticProgram) -> np.ndarray:
    """Vectorized penalized_energy for a (m, num_vars) array of binary vectors."""
    obj = qubo.objective
    xs = np.asarray(xs, dtype=float)
    quad = obj.quadratic.to_array(symmetric=False)
    return np.einsum("bi,ij,bj->b", xs, quad, xs) + xs @ obj.linear.to_array() + obj.constant


def all_binary_vectors(num_vars: int) -> np.ndarray:
    """All 2^num_vars binary vectors in variable order (row b holds the bits of b, index 0 first)."""
    return ((np.arange(2**num_vars)[:, None] >> np.arange(num_vars)) & 1).astype(np.int8)


def qap_objective(xs: np.ndarray, inst: Instance) -> np.ndarray:
    """C(x) = Σ_{i<k} Σ_{j,l} F[i,k]·D[j,l]·x_ij·x_kl for any binary x, feasible or not."""
    x = np.asarray(xs, dtype=np.int64).reshape(-1, inst.n, inst.n)
    return np.einsum("bij,ik,jl,bkl->b", x, inst.F, inst.D, x)


def constraint_violation(xs: np.ndarray, n: int) -> np.ndarray:
    """P(x) = Σ_i (Σ_j x_ij − 1)² + Σ_j (Σ_i x_ij − 1)²; zero iff x is a permutation matrix."""
    x = np.asarray(xs, dtype=np.int64).reshape(-1, n, n)
    return ((x.sum(axis=2) - 1) ** 2).sum(axis=1) + ((x.sum(axis=1) - 1) ** 2).sum(axis=1)


def penalty_threshold(inst: Instance) -> float:
    """λ* = max over infeasible x of (C_opt − C(x)) / P(x), with P the constraint violation.

    For λ > λ* the QUBO ground state is feasible and optimal. Exact enumeration: only for n <= 4.
    """
    if inst.n > 4:
        raise ValueError("penalty_threshold enumerates 2^(n²); use block decomposition for n >= 5")
    xs = all_binary_vectors(inst.n * inst.n)
    objective = qap_objective(xs, inst)
    violation = constraint_violation(xs, inst.n)
    feasible = violation == 0
    optimum = objective[feasible].min()
    return float(np.max((optimum - objective[~feasible]) / violation[~feasible]))
