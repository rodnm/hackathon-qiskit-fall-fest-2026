"""QUBO/Ising model for the gate assignment problem. Owner: Diego."""

from __future__ import annotations

import itertools

import numpy as np
from qiskit.quantum_info import SparsePauliOp
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

from .types import Instance, cost, costs


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


def build_subproblem(
    inst: Instance, perm: tuple[int, ...], flights: tuple[int, ...]
) -> tuple[QuadraticProgram, tuple[int, ...]]:
    """LNS sub-problem: re-assign `flights` among the gates they use now, other flights fixed.

    Variables y_{a}_{b}: flight flights[a] -> gate gates[b] (k×k one-hot rows and columns).
    Objective = interactions inside the neighborhood (quadratic) + interactions with the fixed
    flights (linear) + fixed-fixed interactions (constant), so on any feasible y it equals the
    global cost() of the reconstructed assignment. Returns (qp, gates).
    """
    k = len(flights)
    gates = tuple(int(perm[i]) for i in flights)
    inside = set(flights)
    fixed = [m for m in range(inst.n) if m not in inside]
    F_sym = inst.F_sym

    qp = QuadraticProgram(f"{inst.name}-lns")
    for a in range(k):
        for b in range(k):
            qp.binary_var(f"y_{a}_{b}")

    quadratic = {}
    for a, c in itertools.combinations(range(k), 2):
        flow = F_sym[flights[a], flights[c]]
        if not flow:
            continue
        for b in range(k):
            for d in range(k):
                if b != d:
                    quadratic[(f"y_{a}_{b}", f"y_{c}_{d}")] = int(flow * inst.D[gates[b], gates[d]])
    linear = {
        f"y_{a}_{b}": int(sum(F_sym[flights[a], m] * inst.D[gates[b], perm[m]] for m in fixed))
        for a in range(k)
        for b in range(k)
    }
    constant = int(
        sum(inst.F[i, m] * inst.D[perm[i], perm[m]] for i, m in itertools.combinations(fixed, 2))
    )
    qp.minimize(constant=constant, linear=linear, quadratic=quadratic)
    for a in range(k):
        qp.linear_constraint({f"y_{a}_{b}": 1 for b in range(k)}, "==", 1, f"row_{a}")
    for b in range(k):
        qp.linear_constraint({f"y_{a}_{b}": 1 for a in range(k)}, "==", 1, f"col_{b}")
    return qp, gates


def qp_penalty_threshold(qp: QuadraticProgram, n: int) -> float:
    """λ* of any n×n one-hot QuadraticProgram (e.g. an LNS sub-problem), by enumeration (n <= 4)."""
    if n > 4:
        raise ValueError("qp_penalty_threshold enumerates 2^(n²) vectors: only n <= 4")
    xs = all_binary_vectors(n * n)
    objective = penalized_energies(xs, qp)  # the constrained qp has no penalty: plain objective
    violation = constraint_violation(xs, n)
    feasible = violation == 0
    return float(np.max((objective[feasible].min() - objective[~feasible]) / violation[~feasible]))


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


def all_binary_vectors(num_vars: int, start: int = 0, stop: int | None = None) -> np.ndarray:
    """Binary vectors b in [start, stop) in variable order (row holds the bits of b, index 0 first)."""
    stop = 2**num_vars if stop is None else stop
    return ((np.arange(start, stop)[:, None] >> np.arange(num_vars)) & 1).astype(np.int8)


def qap_objective(xs: np.ndarray, inst: Instance) -> np.ndarray:
    """C(x) = Σ_{i<k} Σ_{j,l} F[i,k]·D[j,l]·x_ij·x_kl for any binary x, feasible or not."""
    x = np.asarray(xs, dtype=np.int64).reshape(-1, inst.n, inst.n)
    pair_distance = x @ inst.D @ x.transpose(0, 2, 1)  # [b, i, k] = Σ_{j,l} x_ij D_jl x_kl
    return (pair_distance * inst.F).sum(axis=(1, 2))


def constraint_violation(xs: np.ndarray, n: int) -> np.ndarray:
    """P(x) = Σ_i (Σ_j x_ij − 1)² + Σ_j (Σ_i x_ij − 1)²; zero iff x is a permutation matrix."""
    x = np.asarray(xs, dtype=np.int64).reshape(-1, n, n)
    return ((x.sum(axis=2) - 1) ** 2).sum(axis=1) + ((x.sum(axis=1) - 1) ** 2).sum(axis=1)


def exact_optimum(inst: Instance) -> tuple[int, int]:
    """(C*, number of optimal permutations) by enumerating the n! permutations (small n only)."""
    perms = np.array(list(itertools.permutations(range(inst.n))))
    values = costs(perms, inst)
    best = int(values.min())
    return best, int((values == best).sum())


def penalty_threshold(inst: Instance, chunk_bits: int = 20) -> float:
    """λ* = max over infeasible x of (C_opt − C(x)) / P(x), with P the constraint violation.

    For λ > λ* the QUBO ground state is feasible and optimal. Exact enumeration of the 2^(n²)
    binary vectors in chunks of 2^chunk_bits: instant for n <= 4, about a minute for n = 5.
    """
    if inst.n > 5:
        raise ValueError("penalty_threshold enumerates 2^(n²) vectors: only n <= 5 is tractable")
    optimum, _ = exact_optimum(inst)
    num_vars = inst.n * inst.n
    total, step = 2**num_vars, 2 ** min(chunk_bits, num_vars)
    threshold = -np.inf
    for start in range(0, total, step):
        xs = all_binary_vectors(num_vars, start, start + step)
        violation = constraint_violation(xs, inst.n)
        infeasible = violation > 0
        ratio = (optimum - qap_objective(xs[infeasible], inst)) / violation[infeasible]
        threshold = max(threshold, float(ratio.max()))
    return threshold


def default_penalty(inst: Instance, factor: float = 2.0) -> tuple[float, str]:
    """Penalty used by the solvers and the rule that produced it (recorded in Result.params).

    n <= 4: factor·λ* (exact threshold). Larger n: cost of the identity assignment, a feasible
    cost, so it is >= C* >= λ* (safe but loose bound, see FORMULACION.md §3.1).
    """
    if inst.n <= 4:
        return factor * penalty_threshold(inst), f"{factor:g}*lambda_star"
    return float(cost(tuple(range(inst.n)), inst)), "cost_identity_upper_bound"


def spectrum_stats(inst: Instance, lam: float) -> dict:
    """Exact spectrum of E_λ = C + λ·P over all 2^(n²) states (n <= 4).

    rel_gap = (E1 − E0) / (Emax − Emin), with E1 the first level above the ground level: it shrinks
    as λ grows, a standard proxy for a harder landscape for QAOA. feasible_span is the fraction of
    the energy range occupied by feasible states (how much room the real objective keeps).
    """
    if inst.n > 4:
        raise ValueError("spectrum_stats needs the full spectrum: only n <= 4")
    xs = all_binary_vectors(inst.n * inst.n)
    objective = qap_objective(xs, inst)
    violation = constraint_violation(xs, inst.n)
    energy = objective + lam * violation
    feasible = violation == 0
    optimum = objective[feasible].min()
    e_min, e_max = energy.min(), energy.max()
    ground = energy == e_min
    levels = np.unique(energy)
    return {
        "lam": float(lam),
        "ground_energy": float(e_min),
        "ground_feasible": bool(feasible[ground].all()),
        "ground_optimal": bool(feasible[ground].all() and (objective[ground] == optimum).all()),
        "rel_gap": float((levels[1] - levels[0]) / (e_max - e_min)),
        "feasible_span": float((objective[feasible].max() - optimum) / (e_max - e_min)),
        "energy_range": float(e_max - e_min),
    }
