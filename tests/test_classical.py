import tracemalloc
from dataclasses import replace

import numpy as np
import pytest

from qap.classical import solve_bruteforce, solve_local_search, solve_sa, swap_delta
from qap.data import load_instance
from qap.types import cost

CONTROLS = [
    (3, 24),
    (4, 32),
    pytest.param(10, 340, marks=pytest.mark.slow),
]
FAST_SA = {"iters": 2_000, "restarts": 2}


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


@pytest.mark.parametrize("n", [4, 10])
def test_swap_delta_equals_full_recompute(n):
    inst = load_instance(n)
    rng = np.random.default_rng(0)
    for _ in range(1000):
        perm = rng.permutation(n)
        r, s = (int(v) for v in rng.choice(n, size=2, replace=False))
        swapped = perm.copy()
        swapped[r], swapped[s] = swapped[s], swapped[r]
        assert swap_delta(perm, r, s, inst.F_sym, inst.D) == cost(swapped, inst) - cost(perm, inst)


def heuristics():
    return [(solve_local_search, {"restarts": 20}), (solve_sa, FAST_SA)]


@pytest.mark.parametrize("solver, params", heuristics())
def test_heuristics_return_valid_consistent_results(solver, params):
    inst = load_instance(10)
    result = solver(inst, seed=0, **params)
    assert result.feasible
    assert sorted(result.perm) == list(range(10))
    assert result.cost == cost(result.perm, inst)
    assert result.cost >= 340  # never below the proven optimum


@pytest.mark.parametrize("solver, params", heuristics())
def test_heuristics_are_deterministic_by_seed(solver, params):
    inst = load_instance(10)
    assert solver(inst, seed=3, **params).perm == solver(inst, seed=3, **params).perm


@pytest.mark.parametrize("solver, params", heuristics())
def test_heuristics_reach_the_n4_control_optimum(solver, params):
    assert solver(load_instance(4), seed=0, **params).cost == 32


@pytest.mark.parametrize("solver, params", heuristics())
def test_heuristics_do_not_need_the_known_optimum(solver, params):
    blind = replace(load_instance(10), optimum=None)  # the challenge forbids using it as a starting point
    result = solver(blind, seed=0, **params)
    assert result.feasible and result.cost >= 340


def test_local_search_with_restarts_finds_340_on_qap10():
    # 100 restarts from random permutations: measured 10/10 seeds; this checks one seed end to end
    assert solve_local_search(load_instance(10), seed=0, restarts=100).cost == 340
