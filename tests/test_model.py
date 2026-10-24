"""Tests for the QUBO/Ising model (M2/M3). Owner: Diego.

Every Qiskit object (QuadraticProgram, QUBO, SparsePauliOp, measured bitstrings) is checked against
an independent classical reference: the exhaustive enumeration of the 2^(n²) binary vectors and the
shared `cost()` function. Instances are the first n rows/columns of qap10 (optima 24 and 32).
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2

from qap.data import load_instance
from qap.model import (
    all_binary_vectors,
    build_qp,
    build_subproblem,
    constraint_violation,
    decode,
    decode_x,
    default_penalty,
    exact_optimum,
    is_feasible,
    penalized_energies,
    penalized_energy,
    penalty_threshold,
    qap_objective,
    qp_penalty_threshold,
    spectrum_stats,
    to_ising,
    to_qubo,
    true_cost,
    x_from_bits,
)
from qap.types import cost

SIZES = [3, 4]
CONTROL = [(3, 24), (4, 32)]
THRESHOLD = [(3, 10.0), (4, 13.0)]


def perm_to_x(perm: tuple[int, ...], n: int) -> np.ndarray:
    """Permutation -> binary vector in variable order (index i*n + j)."""
    x = np.zeros((n, n), dtype=np.int8)
    x[np.arange(n), list(perm)] = 1
    return x.ravel()


def qubo_for(n: int, factor: float = 2.0):
    inst = load_instance(n)
    return inst, to_qubo(build_qp(inst), lam=factor * penalty_threshold(inst))


# --- QuadraticProgram -----------------------------------------------------------------------


@pytest.mark.parametrize("n", SIZES)
def test_quadratic_program_structure(n: int) -> None:
    qp = build_qp(load_instance(n))
    assert qp.get_num_binary_vars() == n * n
    # variable order convention: x_{i}_{j} at flat index i*n + j
    assert [v.name for v in qp.variables] == [f"x_{i}_{j}" for i in range(n) for j in range(n)]
    assert len(qp.linear_constraints) == 2 * n
    assert all(c.rhs == 1 for c in qp.linear_constraints)


# --- QUBO (M3 a, b) -------------------------------------------------------------------------


@pytest.mark.parametrize("n", SIZES)
def test_qubo_energy_equals_cost_on_every_permutation(n: int) -> None:
    """(a) The penalty vanishes on feasible points, so the QUBO energy is the true cost."""
    inst, qubo = qubo_for(n)
    for perm in itertools.permutations(range(n)):
        assert penalized_energy(perm_to_x(perm, n), qubo) == pytest.approx(true_cost(perm, inst))


@pytest.mark.parametrize("n, optimum", CONTROL)
def test_qubo_argmin_is_feasible_and_optimal(n: int, optimum: int) -> None:
    """(b) With λ above the threshold the QUBO ground state is the optimal permutation."""
    inst, qubo = qubo_for(n)
    vectors = all_binary_vectors(n * n)
    perm = decode_x(vectors[int(np.argmin(penalized_energies(vectors, qubo)))], n)
    assert is_feasible(perm, n)
    assert cost(perm, inst) == optimum == inst.optimum


@pytest.mark.parametrize("n", SIZES)
def test_qubo_equals_objective_plus_penalty_everywhere(n: int) -> None:
    inst = load_instance(n)
    lam = 3.0
    qubo = to_qubo(build_qp(inst), lam=lam)
    vectors = all_binary_vectors(n * n)
    expected = qap_objective(vectors, inst) + lam * constraint_violation(vectors, n)
    assert np.allclose(penalized_energies(vectors, qubo), expected)


@pytest.mark.parametrize("n", SIZES)
def test_vectorized_energies_match_qiskit(n: int) -> None:
    _, qubo = qubo_for(n)
    vectors = np.random.default_rng(0).integers(0, 2, size=(50, n * n))
    expected = [qubo.objective.evaluate(v) for v in vectors]
    assert np.allclose(penalized_energies(vectors, qubo), expected)


# --- Penalty λ (M4 justification) -----------------------------------------------------------


@pytest.mark.parametrize("n, threshold", THRESHOLD)
def test_penalty_threshold_is_exact(n: int, threshold: float) -> None:
    """λ* is tight: just above it the ground state is feasible, just below it is not."""
    inst = load_instance(n)
    lam_star = penalty_threshold(inst)
    assert lam_star == pytest.approx(threshold)
    vectors = all_binary_vectors(n * n)
    violation = constraint_violation(vectors, n)

    above = to_qubo(build_qp(inst), lam=1.01 * lam_star)
    best = int(np.argmin(penalized_energies(vectors, above)))
    assert violation[best] == 0
    assert cost(decode_x(vectors[best], n), inst) == inst.optimum

    below = to_qubo(build_qp(inst), lam=0.99 * lam_star)
    assert violation[int(np.argmin(penalized_energies(vectors, below)))] > 0


def test_penalty_threshold_below_simple_bound() -> None:
    """λ* <= C* because C(x) >= 0 and P(x) >= 1 on infeasible points."""
    for n in SIZES:
        inst = load_instance(n)
        assert 0 < penalty_threshold(inst) <= inst.optimum


@pytest.mark.parametrize("n", SIZES)
def test_penalty_threshold_chunked_matches_single_pass(n: int) -> None:
    inst = load_instance(n)
    assert penalty_threshold(inst, chunk_bits=5) == penalty_threshold(inst)


@pytest.mark.parametrize("n, optimum", CONTROL)
def test_exact_optimum_matches_control(n: int, optimum: int) -> None:
    best, n_optima = exact_optimum(load_instance(n))
    assert best == optimum
    assert n_optima >= 1


def test_default_penalty_rules() -> None:
    lam, rule = default_penalty(load_instance(4))
    assert lam == pytest.approx(2 * 13.0) and rule == "2*lambda_star"
    inst = load_instance(10)
    lam, rule = default_penalty(inst)
    assert rule == "cost_identity_upper_bound"
    assert lam >= inst.optimum  # a feasible cost bounds C*, which bounds λ*


@pytest.mark.parametrize("n", SIZES)
def test_spectrum_stats_feasibility_flips_at_threshold(n: int) -> None:
    inst = load_instance(n)
    lam_star = penalty_threshold(inst)
    below, above = spectrum_stats(inst, 0.9 * lam_star), spectrum_stats(inst, 1.1 * lam_star)
    assert not below["ground_feasible"]
    assert above["ground_optimal"] and above["ground_energy"] == pytest.approx(inst.optimum)
    # a larger penalty stretches the spectrum: the real objective keeps a smaller share of it
    far = spectrum_stats(inst, 8 * lam_star)
    assert far["feasible_span"] < above["feasible_span"]
    assert far["rel_gap"] < above["rel_gap"]


# --- Ising operator (x = (1 - Z)/2) ---------------------------------------------------------


@pytest.mark.parametrize("n", SIZES)
def test_ising_diagonal_matches_qubo_on_every_basis_state(n: int) -> None:
    """⟨b|H|b⟩ + offset equals the QUBO energy on all 2^(n²) computational basis states."""
    _, qubo = qubo_for(n)
    op, offset = to_ising(qubo)
    assert op.num_qubits == n * n
    assert all(set(label) <= {"I", "Z"} for label in op.paulis.to_labels())
    # diagonal index b = basis state |b⟩, qubit q = bit q of b = row b of all_binary_vectors
    diagonal = op.to_matrix(sparse=True).diagonal().real
    assert np.allclose(diagonal + offset, penalized_energies(all_binary_vectors(n * n), qubo))


@pytest.mark.parametrize("n, optimum", CONTROL)
def test_ising_ground_state_is_optimal_permutation(n: int, optimum: int) -> None:
    inst, qubo = qubo_for(n)
    op, offset = to_ising(qubo)
    diagonal = op.to_matrix(sparse=True).diagonal().real
    ground = int(np.argmin(diagonal))
    perm = decode_x(all_binary_vectors(n * n)[ground], n)
    assert cost(perm, inst) == optimum
    assert diagonal[ground] + offset == pytest.approx(optimum)


# --- Bit order: circuit -> measurement -> decode (same primitive and transpiler as solve_qaoa) ---


@pytest.mark.parametrize("n", SIZES)
def test_measured_bitstrings_decode_to_prepared_permutation(n: int) -> None:
    """Prepare |x(perm)⟩ with X on qubit i*n + perm[i], sample on Aer, decode, get perm back."""
    perms = list(itertools.permutations(range(n)))
    pm = generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())
    circuits = []
    for perm in perms:
        qc = QuantumCircuit(n * n)
        for i, j in enumerate(perm):
            qc.x(i * n + j)
        qc.measure_all()
        circuits.append(pm.run(qc))

    results = SamplerV2(default_shots=16, seed=0).run(circuits).result()
    for perm, result in zip(perms, results):
        counts = result.data.meas.get_counts()
        assert len(counts) == 1  # basis state: deterministic outcome
        (bitstring,) = counts
        assert decode(bitstring, n) == perm
        assert np.array_equal(x_from_bits(bitstring), perm_to_x(perm, n))


@pytest.mark.parametrize("k", [2, 3, 4])
def test_subproblem_objective_equals_global_cost(k: int) -> None:
    """On every feasible y the sub-problem objective is the global cost of the rebuilt perm."""
    inst = load_instance(10)
    rng = np.random.default_rng(k)
    for _ in range(5):
        perm = tuple(int(g) for g in rng.permutation(10))
        flights = tuple(sorted(int(i) for i in rng.choice(10, size=k, replace=False)))
        qp, gates = build_subproblem(inst, perm, flights)
        assert gates == tuple(perm[i] for i in flights)
        for local in itertools.permutations(range(k)):
            new = list(perm)
            for a, b in enumerate(local):
                new[flights[a]] = gates[b]
            assert qp.objective.evaluate(perm_to_x(local, k)) == cost(tuple(new), inst)


@pytest.mark.parametrize("k", [3, 4])
def test_subproblem_threshold_makes_ground_state_feasible(k: int) -> None:
    inst = load_instance(10)
    rng = np.random.default_rng(0)
    perm = tuple(int(g) for g in rng.permutation(10))
    flights = tuple(sorted(int(i) for i in rng.choice(10, size=k, replace=False)))
    qp, _ = build_subproblem(inst, perm, flights)
    lam_star = qp_penalty_threshold(qp, k)
    vectors = all_binary_vectors(k * k)
    violation = constraint_violation(vectors, k)
    above = penalized_energies(vectors, to_qubo(qp, 1.01 * lam_star))
    below = penalized_energies(vectors, to_qubo(qp, 0.99 * lam_star))
    assert violation[int(np.argmin(above))] == 0
    assert violation[int(np.argmin(below))] > 0


def test_decode_rejects_non_permutations() -> None:
    assert decode("0", 3) is None
    assert decode("0" * 9, 3) is None
    # x = [1,1,0 | 0,0,0 | 0,0,1] (flight 0 on two gates, flight 1 on none), measured reversed
    assert decode("100000011", 3) is None
    # perm (0,2,1) -> x = 100|001|010, measured "010100001"; reading it unreversed gives (1,0,2)
    assert decode("010100001", 3) == (0, 2, 1)
