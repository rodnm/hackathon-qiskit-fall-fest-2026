"""Acceptance tests for the reconstructed qap10 instance.

Control optima from the challenge: N=3 -> 24, N=4 -> 32, N=10 -> 340. Each owner removes the
xfail marker from the tests of their module once the implementation lands.
"""

import pytest

from qap.classical import solve_bruteforce
from qap.data import load_instance

pending = pytest.mark.xfail(raises=NotImplementedError, reason="waiting for data.py / classical.py")


@pending
@pytest.mark.parametrize("n, optimum", [(3, 24), (4, 32), (10, 340)])
def test_bruteforce_reaches_control_optimum(n, optimum):
    result = solve_bruteforce(load_instance(n))
    assert result.feasible
    assert result.cost == optimum
