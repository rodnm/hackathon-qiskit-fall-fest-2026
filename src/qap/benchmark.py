"""Benchmark: classical solvers against the ingested quantum results. Owner: Rodrigo.

    uv run python -m qap.benchmark                              # sizes 3 4 10, seeds 0..9
    uv run python -m qap.benchmark --sizes 3 4 --methods bruteforce

Classical methods run here. QAOA and hybrid results come from Diego's scripts and are only
ingested from results/*.csv, never re-run. Writes results/benchmark.csv (one row per run) and
results/comparison.csv (aggregated per size, method and configuration).

Metrics follow the challenge: the known optimum is used only to evaluate, `gap_pct` is the
challenge gap 100 (C - 340) / 340 (n = 10, valid results only) and `gap_vs_control_pct` is the
distance to the control optimum of a reduced instance (our extension). Cost and penalized energy
are separate columns.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pandas as pd

from . import stats
from .classical import solve_bruteforce
from .data import ROOT, load_instance
from .types import Instance, Result

RESULTS = ROOT / "results"
BENCHMARK_CSV = RESULTS / "benchmark.csv"
COMPARISON_CSV = RESULTS / "comparison.csv"
MAX_FLOOR_N = 6  # the random floor needs the number of optima (exact enumeration of n!)

COLUMNS = [
    "instance", "n", "method", "config", "seed", "cost", "feasible", "optimal", "gap_pct",
    "gap_vs_control_pct", "seconds", "peak_mem_mb", "shots", "feasible_samples", "optimal_samples",
    "feasible_fraction", "penalized_energy", "params_json", "source",
]
LAMBDA_QAOA_COLUMNS = {"n", "lambda_factor", "seed", "feasible", "best_cost", "feasible_fraction",
                       "optimal_prob", "penalized_energy", "seconds", "params_json"}


@dataclass(frozen=True)
class ClassicalMethod:
    solve: Callable[..., Result]
    deterministic: bool = False  # run once (seed of the first requested seed)
    params: dict = field(default_factory=dict)


CLASSICAL: dict[str, ClassicalMethod] = {
    "bruteforce": ClassicalMethod(solve_bruteforce, deterministic=True),
}


def _nan(value: float | None) -> float:
    return math.nan if value is None else float(value)


def _evaluate(n: int, cost_value: float | None, feasible: bool) -> dict:
    """Validity, optimality and gap columns. The known optimum is used here only to evaluate."""
    optimum = load_instance(n).optimum
    valid = bool(feasible) and not (cost_value is None or math.isnan(float(cost_value)))
    if not valid:
        return {"cost": math.nan, "feasible": False, "optimal": False,
                "gap_pct": math.nan, "gap_vs_control_pct": math.nan}
    return {
        "cost": float(cost_value),
        "feasible": True,
        "optimal": optimum is not None and float(cost_value) == optimum,
        "gap_pct": _nan(stats.gap_pct(cost_value, n)),
        "gap_vs_control_pct": math.nan if n == stats.N_FULL
        else _nan(stats.gap_vs_control_pct(cost_value, optimum)),
    }


def _config(name: str, params: dict) -> str:
    return name if not params else name + " " + " ".join(f"{k}={v}" for k, v in sorted(params.items()))


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def _params(text: object) -> dict:
    try:
        return json.loads(text) if isinstance(text, str) else {}
    except json.JSONDecodeError:
        return {}


def row_from_result(inst: Instance, name: str, config: str, result: Result) -> dict:
    """Benchmark row for a classical Result (always a permutation: no shots, no penalty)."""
    return {
        "instance": inst.name, "n": inst.n, "method": name, "config": config, "seed": result.seed,
        **_evaluate(inst.n, result.cost, result.feasible),
        "seconds": result.seconds, "peak_mem_mb": result.peak_mem_mb,
        "shots": math.nan, "feasible_samples": math.nan, "optimal_samples": math.nan,
        "feasible_fraction": math.nan, "penalized_energy": math.nan,
        "params_json": json.dumps(result.params), "source": "qap.classical",
    }


def run_classical(sizes: list[int], seeds: list[int], methods: list[str]) -> pd.DataFrame:
    rows = []
    for n in sizes:
        inst = load_instance(n)
        for name in methods:
            method = CLASSICAL[name]
            config = _config(name, method.params)
            for seed in seeds[:1] if method.deterministic else seeds:
                result = method.solve(inst, seed=seed, **method.params)
                rows.append(row_from_result(inst, name, config, result))
                print(f"[classical] n={n} {config} seed={seed}: cost={result.cost} ({result.seconds:.2f}s)")
    return _frame(rows)


# --- ingestion of quantum / hybrid results (read-only) -------------------------------------------


@cache
def _lambda_star(n: int) -> float:
    from .model import penalty_threshold  # Diego's module, used read-only

    return penalty_threshold(load_instance(n))


@cache
def n_optima(n: int) -> int:
    """Number of optimal permutations of the first-n instance (small n only)."""
    from .model import exact_optimum  # Diego's module, used read-only

    return exact_optimum(load_instance(n))[1]


def ingest_lambda_qaoa(path: Path) -> pd.DataFrame:
    """QAOA runs from qap.lambda_study (one row per lambda factor and seed)."""
    rows = []
    for r in pd.read_csv(path).to_dict("records"):
        p = _params(r["params_json"])
        shots = float(p.get("shots", math.nan))
        n = int(r["n"])
        rows.append({
            "instance": f"qap10-n{n}", "n": n, "method": "qaoa",
            "config": f"qaoa lambda={r['lambda_factor']:g}*lambda* reps={p.get('reps', 1)}",
            "seed": int(r["seed"]), **_evaluate(n, r["best_cost"], bool(r["feasible"])),
            "seconds": r["seconds"], "peak_mem_mb": math.nan, "shots": shots,
            "feasible_samples": round(r["feasible_fraction"] * shots),
            "optimal_samples": round(r["optimal_prob"] * shots),
            "feasible_fraction": r["feasible_fraction"], "penalized_energy": r["penalized_energy"],
            "params_json": r["params_json"], "source": path.name,
        })
    return _frame(rows)


def ingest_qaoa_m5(path: Path) -> pd.DataFrame:
    """QAOA runs from src/run_qaoa_m5.py (reps sweep). Its optimal_prob is not reliable (the script
    built instances without the optimum), so optimal samples are left empty."""
    rows = []
    for r in pd.read_csv(path).to_dict("records"):
        n, shots = int(r["n"]), float(r["shots"])
        factor = r["lambda"] / _lambda_star(n)
        params = {"reps": int(r["reps"]), "maxiter": int(r["maxiter"]), "shots": int(shots),
                  "penalty": float(r["lambda"])}
        rows.append({
            "instance": f"qap10-n{n}", "n": n, "method": "qaoa",
            "config": f"qaoa lambda={factor:g}*lambda* reps={int(r['reps'])}",
            "seed": int(r["seed"]), **_evaluate(n, r["best_feasible_cost"], bool(r["feasible"])),
            "seconds": r["seconds"], "peak_mem_mb": r.get("peak_mem_mb", math.nan), "shots": shots,
            "feasible_samples": round(r["feasible_fraction"] * shots), "optimal_samples": math.nan,
            "feasible_fraction": r["feasible_fraction"], "penalized_energy": r["penalized_energy"],
            "params_json": json.dumps(params), "source": path.name,
        })
    return _frame(rows)


def ingest_hybrid(path: Path) -> pd.DataFrame:
    """Hybrid LNS runs from qap.hybrid_study (full instance; subproblem samples are not comparable
    with the random floor of the full QUBO, so shots are left empty)."""
    rows = []
    for r in pd.read_csv(path).to_dict("records"):
        n = int(r["n"])
        rows.append({
            "instance": r["instance"], "n": n, "method": r["method"], "config": r["run"],
            "seed": int(r["seed"]), **_evaluate(n, r["cost"], bool(r["feasible"])),
            "seconds": r["seconds"], "peak_mem_mb": r["peak_mem_mb"], "shots": math.nan,
            "feasible_samples": math.nan, "optimal_samples": math.nan,
            "feasible_fraction": r["feasible_fraction"], "penalized_energy": r["penalized_energy"],
            "params_json": r["params_json"], "source": path.name,
        })
    return _frame(rows)


INGESTERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    "lambda_qaoa.csv": ingest_lambda_qaoa,
    "qaoa_m5.csv": ingest_qaoa_m5,
    "hybrid_lns.csv": ingest_hybrid,
}


def ingest_results(results_dir: Path = RESULTS) -> pd.DataFrame:
    """All known quantum/hybrid result files, plus any qaoa_*.csv with the lambda_study columns.

    The same run can appear in several files (e.g. lambda=2*lambda*, reps=1 in both lambda_qaoa.csv
    and qaoa_m5.csv): rows are de-duplicated on (n, method, config, seed), keeping the first file.
    """
    frames = [fn(results_dir / name) for name, fn in INGESTERS.items() if (results_dir / name).exists()]
    for path in sorted(results_dir.glob("qaoa_*.csv")):
        if path.name not in INGESTERS and LAMBDA_QAOA_COLUMNS <= set(pd.read_csv(path, nrows=0).columns):
            frames.append(ingest_lambda_qaoa(path))
    if not frames:
        return _frame([])
    merged = pd.concat(frames, ignore_index=True)
    return merged.drop_duplicates(subset=["n", "method", "config", "seed"], keep="first").reset_index(drop=True)


# --- aggregation -----------------------------------------------------------------------------------


def compare(bench: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per (n, method, config): quality, success rate, time, and sampling vs the random floor."""
    rows = []
    for (n, method, config), g in bench.groupby(["n", "method", "config"], sort=True):
        n = int(n)
        valid = g[g["feasible"].astype(bool)]
        runs, reached = len(g), int(g["optimal"].astype(bool).sum())
        low, high = stats.wilson_interval(reached, runs)
        row = {
            "n": n, "method": method, "config": config, "runs": runs, "valid_runs": len(valid),
            "best_cost": valid["cost"].min(), "mean_cost": valid["cost"].mean(),
            "reached_optimum": reached, "reached_optimum_rate": reached / runs,
            "reached_optimum_ci_low": low, "reached_optimum_ci_high": high,
            "best_gap_pct": valid["gap_pct"].min(), "mean_gap_pct": valid["gap_pct"].mean(),
            "best_gap_vs_control_pct": valid["gap_vs_control_pct"].min(),
            "mean_seconds": g["seconds"].mean(), "median_seconds": g["seconds"].median(),
            "max_peak_mem_mb": g["peak_mem_mb"].max(),
        }
        sampled = g[g["shots"].notna()]
        if len(sampled) and n <= MAX_FLOOR_N:
            shots, k = int(sampled["shots"].sum()), int(sampled["feasible_samples"].sum())
            floor, optimal_floor = stats.random_floor(n, n_optima(n))
            f_low, f_high = stats.wilson_interval(k, shots)
            row.update({
                "total_shots": shots, "feasible_samples": k, "feasible_fraction": k / shots,
                "feasible_ci_low": f_low, "feasible_ci_high": f_high, "random_feasible_floor": floor,
                "feasible_vs_floor": k / shots / floor,
                "p_value_vs_floor": stats.binomial_vs_floor(k, shots, floor),
                "shots_to_detect_2x_floor": stats.shots_for_power(floor, 2),
            })
            if sampled["optimal_samples"].notna().all():
                k_opt = int(sampled["optimal_samples"].sum())
                row.update({
                    "optimal_samples": k_opt, "random_optimal_floor": optimal_floor,
                    "optimal_vs_floor": k_opt / shots / optimal_floor,
                    "p_value_optimal_vs_floor": stats.binomial_vs_floor(k_opt, shots, optimal_floor),
                })
        rows.append(row)
    return pd.DataFrame(rows)


def build_benchmark(sizes: list[int], seeds: list[int], methods: list[str], ingest: bool = True) -> pd.DataFrame:
    frames = [run_classical(sizes, seeds, methods)]
    if ingest:
        ingested = ingest_results()
        frames.append(ingested[ingested["n"].isin(sizes)])
    return pd.concat([f for f in frames if len(f)], ignore_index=True)


def write_outputs(bench: pd.DataFrame, comparison: pd.DataFrame) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    bench.to_csv(BENCHMARK_CSV, index=False)
    comparison.to_csv(COMPARISON_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", type=int, nargs="+", default=[3, 4, 10])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--methods", nargs="+", default=list(CLASSICAL), choices=list(CLASSICAL))
    parser.add_argument("--no-ingest", action="store_true", help="classical methods only")
    args = parser.parse_args()

    bench = build_benchmark(args.sizes, args.seeds, args.methods, ingest=not args.no_ingest)
    comparison = compare(bench)
    write_outputs(bench, comparison)
    cols = ["n", "method", "config", "runs", "best_cost", "reached_optimum_rate", "best_gap_pct",
            "mean_seconds", "feasible_vs_floor", "p_value_vs_floor"]
    print(comparison[[c for c in cols if c in comparison]].to_string(index=False))
    print(f"wrote {BENCHMARK_CSV.relative_to(ROOT)} ({len(bench)} rows), {COMPARISON_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
