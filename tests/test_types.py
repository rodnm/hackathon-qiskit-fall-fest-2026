import itertools

import numpy as np
import pytest

from qap.types import Instance, cost, costs


def tiny() -> Instance:
    F = np.array([[0, 3, 1], [0, 0, 2], [0, 0, 0]])
    D = np.array([[0, 1, 2], [1, 0, 1], [2, 1, 0]])
    return Instance("tiny", 3, F, D)


def test_cost_counts_each_pair_once():
    # perm = identity: 3*D[0,1] + 1*D[0,2] + 2*D[1,2] = 3 + 2 + 2
    assert cost((0, 1, 2), tiny()) == 7


def test_costs_matches_cost_on_all_permutations():
    inst = tiny()
    perms = np.array(list(itertools.permutations(range(3))))
    expected = [cost(p, inst) for p in perms]
    assert costs(perms, inst).tolist() == expected


def test_instance_rejects_non_upper_triangular_flows():
    with pytest.raises(ValueError):
        Instance("bad", 2, np.array([[0, 1], [1, 0]]), np.array([[0, 1], [1, 0]]))


def test_instance_rejects_asymmetric_distances():
    with pytest.raises(ValueError):
        Instance("bad", 2, np.array([[0, 1], [0, 0]]), np.array([[0, 1], [2, 0]]))
