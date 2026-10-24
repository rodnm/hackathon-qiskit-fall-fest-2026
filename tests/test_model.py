"""Tests for the QUBO/Ising model (M2/M3). Owner: Diego."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from qap.model import (
    build_qp,
    decode,
    decode_x,
    is_feasible,
    penalized_energy,
    penalty_threshold,
    to_ising,
    to_qubo,
    true_cost,
    x_from_bits,
)
from qap.types import Instance, cost

F = np.array(
    [
        [0, 10, 4, 8],
        [0, 0, 6, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
)
D = np.array(
    [
        [0, 1, 2, 3],
        [1, 0, 1, 2],
        [2, 1, 0, 1],
        [3, 2, 1, 0],
    ]
)


def instance(n: int) -> Instance:
    return Instance(f"test{n}", n, F[:n, :n].copy(), D[:n, :n].copy())


@pytest.mark.parametrize("n, optimum", [(3, 24), (4, 32)])
def test_qp_reaches_control_optimum(n: int, optimum: int) -> None:
    inst = instance(n)
    qubo = to_qubo(build_qp(inst), lam=penalty_threshold(inst) * 2)
    # brute force over the 2^(n²) binary vectors: the argmin must be permutation of cost optimum
    vectors = ((np.arange(2 ** (n * n))[:, None] >> np.arange(n * n)) & 1).astype(int)
    energies = np.array([qubo.objective.evaluate(v) for v in vectors])
    perm = decode_x(vectors[int(np.argmin(energies))], n)
    assert is_feasible(perm, n)
    assert cost(perm, inst) == optimum


@pytest.mark.parametrize("n", [3, 4])
def test_qubo_energy_equals_cost_on_permutations(n: int) -> None:
    inst = instance(n)
    qubo = to_qubo(build_qp(inst), lam=penalty_threshold(inst) * 2)
    for perm in itertools.permutations(range(n)):
        x = np.zeros((n, n), dtype=int)
        x[np.arange(n), list(perm)] = 1
        assert np.isclose(penalized_energy(x.ravel(), qubo), true_cost(perm, inst))


@pytest.mark.parametrize("n", [3, 4])
def test_ising_offset_matches_ground_energy(n: int) -> None:
    from qiskit.quantum_info import Statevector

    inst = instance(n)
    qubo = to_qubo(build_qp(inst), lam=penalty_threshold(inst) * 2)
    op, offset = to_ising(qubo)
    assert op.num_qubits == n * n
    # check on a few random/feasible assignments
    for perm in list(itertools.permutations(range(n)))[:10]:
        x = np.zeros(n * n)
        for i, p in enumerate(perm):
            x[i * n + p] = 1
        qv = qubo.objective.evaluate(x)
        sv = Statevector.from_label("".join(str(int(b)) for b in x[::-1]))
        hv = float(np.real_if_close(sv.expectation_value(op)))
        assert np.isclose(hv + offset, qv)


def test_decode_little_endian() -> None:
    # measured bitstring: rightmost char = qubit 0. Identity permutation for n=3, reversed string.
    x = np.eye(3).ravel().astype(int)
    bits = "".join(str(int(b)) for b in x[::-1])
    assert decode(bits, 3) == (0, 1, 2)
    assert np.array_equal(x_from_bits(bits), x)
    assert decode("0", 3) is None


def test_penalty_threshold_positive() -> None:
    assert penalty_threshold(instance(3)) > 0
    assert penalty_threshold(instance(4)) > 0
