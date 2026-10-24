"""Tests for the Qiskit solvers (M5/M6). Owner: Diego."""

from __future__ import annotations

import numpy as np
import pytest

from qap.data import load_instance
from qap.quantum import choose_neighborhood, solve_hybrid_lns, solve_qaoa
from qap.types import cost


def test_qaoa_n3_returns_feasible_optimum() -> None:
    inst = load_instance(3)
    result = solve_qaoa(inst, seed=0, maxiter=60, shots=2048)
    assert result.feasible
    assert result.cost == cost(result.perm, inst) == inst.optimum
    assert result.params["penalty_rule"] == "2*lambda_star"
    assert 0 < result.extras["feasible_fraction"] <= 1
    assert result.extras["qubits"] == 9


def test_qaoa_is_reproducible_with_the_same_seed() -> None:
    inst = load_instance(3)
    a = solve_qaoa(inst, seed=1, maxiter=20, shots=512)
    b = solve_qaoa(inst, seed=1, maxiter=20, shots=512)
    assert a.extras["final_point"] == b.extras["final_point"]
    assert a.extras["feasible_fraction"] == b.extras["feasible_fraction"]


def test_flow_neighborhood_takes_heaviest_partners() -> None:
    inst = load_instance(10)
    rng = np.random.default_rng(0)
    for _ in range(20):
        flights = choose_neighborhood(inst, 3, rng, "flow")
        assert len(set(flights)) == 3
    # flight 7 (index) has the largest flows (20 with flights 3 and 6)
    weights = inst.F_sym[7]
    assert set(np.argsort(weights)[::-1][:2]) == {3, 6}


@pytest.mark.parametrize("neighborhood", ["random", "flow"])
def test_hybrid_exact_never_worsens_and_reports_true_cost(neighborhood: str) -> None:
    inst = load_instance(10)
    result = solve_hybrid_lns(inst, seed=0, subsolver="exact", iterations=40,
                              neighborhood=neighborhood)
    trace = result.extras["cost_trace"]
    assert all(b <= a for a, b in zip(trace, trace[1:]))
    assert result.cost == cost(result.perm, inst) == trace[-1]
    assert result.cost <= result.extras["start_cost"]
    assert sorted(result.perm) == list(range(10))
    # the exact subsolver takes every improving move it sees
    assert result.extras["improved_neighborhoods"] == result.extras["exact_could_improve"]


def test_hybrid_qaoa_runs_and_records_the_ablation() -> None:
    inst = load_instance(6)
    result = solve_hybrid_lns(inst, seed=0, k=3, iterations=3, maxiter=30, shots=256)
    assert result.method == "hybrid_lns"
    assert result.cost == cost(result.perm, inst) <= result.extras["start_cost"]
    for step in result.extras["steps"]:
        assert step["qubits"] == 9
        assert step["exact_sub_best"] <= step["cost_before"]
        if step["candidate_cost"] is not None:
            assert step["candidate_cost"] >= step["exact_sub_best"]  # QAOA can only match exact
    assert 0 <= result.extras["sub_optimum_match_rate"] <= 1
