"""Integrity of data/processed/qap10_summary.json, the data handoff written by notebooks/01_data.ipynb."""

import json

import pytest

from qap.data import DATA_DIR, load_instance
from qap.types import cost

SUMMARY_PATH = DATA_DIR / "processed" / "qap10_summary.json"


@pytest.fixture(scope="module")
def summary():
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_summary_matrices_match_the_loaded_instance(summary):
    inst = load_instance(10)
    assert summary["F_upper"] == inst.F.tolist()
    assert summary["D"] == inst.D.tolist()


def test_summary_optimal_perms_reach_the_stored_optima(summary):
    assert [sub["n"] for sub in summary["subinstances"]] == list(range(2, 11))
    for sub in summary["subinstances"]:
        inst = load_instance(sub["n"])
        assert sub["optimum"] == inst.optimum
        assert sorted(sub["optimal_perm"]) == list(range(sub["n"]))
        assert cost(sub["optimal_perm"], inst) == sub["optimum"]


def test_summary_gap_follows_the_challenge_formula(summary):
    for row in summary["reference_solutions_n10"]:
        assert row["gap_pct"] == pytest.approx(100 * (row["cost"] - 340) / 340, abs=0.005)
