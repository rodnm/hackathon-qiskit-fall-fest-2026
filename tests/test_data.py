import numpy as np
import pytest

from qap import data
from qap.data import factor_matrices, load_instance, parse_coefficients, recover_matrices


@pytest.fixture(scope="module")
def matrices():
    return recover_matrices()


def test_flows_are_strictly_upper_triangular(matrices):
    F, _ = matrices
    assert np.array_equal(F, np.triu(F, 1))


def test_distances_are_manhattan_on_a_four_column_grid(matrices):
    _, D = matrices
    gates = range(10)
    manhattan = [[abs(j % 4 - m % 4) + abs(j // 4 - m // 4) for m in gates] for j in gates]
    assert np.array_equal(D, np.array(manhattan))


def test_flow_summary_matches_the_instance(matrices):
    F, _ = matrices
    assert F[0, 1] == 10
    assert F.sum() == 228
    assert np.count_nonzero(F) == 29


def test_rank_one_check_rejects_a_corrupted_block():
    P = parse_coefficients()
    P[2, 5, 0, 1] += 1
    with pytest.raises(ValueError, match="not rank-1"):
        factor_matrices(P)


@pytest.mark.parametrize("n, optimum", [(3, 24), (4, 32), (10, 340)])
def test_load_instance_carries_the_control_optimum(n, optimum):
    inst = load_instance(n)
    assert inst.n == n
    assert inst.optimum == optimum


@pytest.mark.parametrize("n", [1, 11])
def test_load_instance_rejects_sizes_out_of_range(n):
    with pytest.raises(ValueError):
        load_instance(n)


def test_mps_fallback_gives_the_same_matrices_as_the_npz(monkeypatch):
    from_npz = load_instance(10)
    monkeypatch.setattr(data, "NPZ_PATH", data.DATA_DIR / "missing.npz")
    data._stored.cache_clear()
    try:
        from_mps = load_instance(10)
    finally:
        data._stored.cache_clear()
    assert np.array_equal(from_npz.F, from_mps.F)
    assert np.array_equal(from_npz.D, from_mps.D)
    assert from_mps.optimum is None
