import math

import pandas as pd
import pytest

from qap import benchmark

LAMBDA_QAOA = benchmark.RESULTS / "lambda_qaoa.csv"


@pytest.fixture(scope="module")
def lambda_rows():
    return benchmark.ingest_lambda_qaoa(LAMBDA_QAOA)


@pytest.fixture(scope="module")
def lambda_comparison(lambda_rows):
    return benchmark.compare(lambda_rows).set_index(["n", "config"])


def test_classical_rows_carry_the_control_optima():
    bench = benchmark.run_classical([3, 4], seeds=[0, 1], methods=["bruteforce"])
    assert list(bench["cost"]) == [24, 32]
    assert bench["optimal"].all() and bench["feasible"].all()
    assert len(bench) == 2  # deterministic: one run per size, not one per seed
    assert bench["gap_pct"].isna().all()  # challenge gap only for n = 10
    assert (bench["gap_vs_control_pct"] == 0).all()
    assert list(bench.columns) == benchmark.COLUMNS


def test_qaoa_at_n3_beats_the_random_floor(lambda_comparison):
    row = lambda_comparison.loc[(3, "qaoa lambda=2*lambda* reps=1")]
    assert row["feasible_samples"] == 765
    assert row["total_shots"] == 20_480
    assert row["feasible_vs_floor"] == pytest.approx(3.19, abs=0.01)
    assert row["p_value_vs_floor"] < 1e-100


def test_qaoa_at_n4_is_not_conclusive(lambda_comparison):
    row = lambda_comparison.loc[(4, "qaoa lambda=2*lambda* reps=1")]
    assert row["feasible_samples"] == 7
    assert row["total_shots"] == 12_288
    assert row["p_value_vs_floor"] == pytest.approx(0.169, abs=0.01)


def test_qaoa_run_without_valid_samples_has_no_cost_or_gap(lambda_rows):
    empty = lambda_rows[(lambda_rows["n"] == 4) & (lambda_rows["feasible_samples"] == 0)]
    assert len(empty) > 0
    assert not empty["feasible"].any()
    assert empty["cost"].isna().all()
    assert empty["gap_pct"].isna().all() and empty["gap_vs_control_pct"].isna().all()


def test_ingested_duplicates_are_counted_once():
    merged = benchmark.ingest_results()
    keys = merged[["n", "method", "config", "seed"]]
    assert not keys.duplicated().any()


def test_gap_columns_respect_the_challenge_rules():
    bench = pd.concat([benchmark.run_classical([4], [0], ["bruteforce"]),
                       benchmark.ingest_lambda_qaoa(LAMBDA_QAOA)], ignore_index=True)
    small = bench[bench["n"] < 10]
    assert small["gap_pct"].isna().all()
    valid = small[small["feasible"]]
    assert valid["gap_vs_control_pct"].notna().all()
    assert all(math.isnan(v) for v in small.loc[~small["feasible"], "gap_vs_control_pct"])
