import tracemalloc

import pytest

from qap.classical import solve_bruteforce
from qap.data import load_instance
from qap.types import cost

CONTROLS = [
    (3, 24),
    (4, 32),
    pytest.param(10, 340, marks=pytest.mark.slow),
]


@pytest.mark.parametrize("n, optimum", CONTROLS)
def test_bruteforce_reaches_the_control_optimum(n, optimum):
    inst = load_instance(n)
    result = solve_bruteforce(inst)
    assert result.feasible
    assert result.cost == optimum
    assert result.cost == cost(result.perm, inst)
    assert sorted(result.perm) == list(range(n))
    assert result.extras["proven_optimum"] is True


def test_bruteforce_is_deterministic():
    inst = load_instance(4)
    assert solve_bruteforce(inst).perm == solve_bruteforce(inst).perm


def test_bruteforce_keeps_a_callers_memory_tracing_alive():
    tracemalloc.start()
    try:
        solve_bruteforce(load_instance(3))
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()
