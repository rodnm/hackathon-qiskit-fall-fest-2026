"""QAOA on small N (M5) and hybrid LNS on N=10 (M6) experiments. Owner: Diego.

    uv run python -m qap.hybrid_study                 # both parts (~30 min)
    uv run python -m qap.hybrid_study --part qaoa     # M5 only: n=3,4 x reps 1-3 x seeds
    uv run python -m qap.hybrid_study --part hybrid   # M6 only: N=10, QAOA vs exact subsolver
    uv run python -m qap.hybrid_study --plot-only     # redraw figures from results/*.csv

Outputs: results/qaoa_small.csv, results/hybrid_lns.csv (shared benchmark schema first, then extra
columns), results/hybrid_lns_steps.csv (one row per LNS step) and docs/figures/qaoa_*.png.
"""

from __future__ import annotations

import argparse
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .data import ROOT, load_instance  # noqa: E402
from .model import exact_optimum  # noqa: E402
from .quantum import solve_hybrid_lns, solve_qaoa  # noqa: E402
from .types import Instance, Result  # noqa: E402

RESULTS = ROOT / "results"
FIGURES = ROOT / "docs" / "figures"
QAOA_CSV = RESULTS / "qaoa_small.csv"
HYBRID_CSV = RESULTS / "hybrid_lns.csv"
STEPS_CSV = RESULTS / "hybrid_lns_steps.csv"
REFERENCE_OPTIMUM = 340  # challenge reference for the full qap10

QAOA_SIZES = [3, 4]
QAOA_REPS = [1, 2, 3]
QAOA_SEEDS = [0, 1, 2, 3, 4]
QAOA_MAXITER = 150
QAOA_SHOTS = 4096

HYBRID_RUNS = [
    # (subsolver, neighborhood, k, seeds)
    ("exact", "random", 3, [0, 1, 2, 3, 4]),
    ("exact", "flow", 3, [0, 1, 2, 3, 4]),
    ("exact", "random", 4, [0, 1, 2, 3, 4]),
    ("qaoa", "random", 3, [0, 1, 2]),
    ("qaoa", "flow", 3, [0, 1, 2]),
]
HYBRID_ITERATIONS = 30


def gap_pct(result: Result, inst: Instance) -> float | None:
    reference = REFERENCE_OPTIMUM if inst.n == 10 else inst.optimum
    if not result.feasible or reference is None:
        return None
    return 100 * (result.cost - reference) / reference


def benchmark_row(result: Result, inst: Instance) -> dict:
    return {
        "instance": inst.name,
        "n": inst.n,
        "method": result.method,
        "seed": result.seed,
        "cost": result.cost,
        "feasible": result.feasible,
        "gap_pct": gap_pct(result, inst),
        "seconds": result.seconds,
        "peak_mem_mb": result.peak_mem_mb,
        "feasible_fraction": result.extras.get("feasible_fraction"),
        "penalized_energy": result.extras.get("penalized_energy"),
        "params_json": json.dumps(result.params),
    }


def qaoa_part() -> pd.DataFrame:
    rows = []
    configs = [(n, reps, True) for n in QAOA_SIZES for reps in QAOA_REPS]
    configs += [(n, 1, False) for n in QAOA_SIZES]  # raw operator: shows what normalizing fixed
    for n, reps, normalize in configs:
        inst = load_instance(n)
        _, n_optima = exact_optimum(inst)
        for seed in QAOA_SEEDS:
            result = solve_qaoa(inst, seed=seed, reps=reps, maxiter=QAOA_MAXITER, shots=QAOA_SHOTS,
                                normalize=normalize)
            extras = result.extras
            rows.append({
                **benchmark_row(result, inst),
                "reps": reps,
                "normalize": normalize,
                "optimal_prob": extras["optimal_prob"],
                "random_feasible_fraction": math.factorial(n) / 2 ** (n * n),
                "random_optimal_prob": n_optima / 2 ** (n * n),
                "qubits": extras["qubits"],
                "depth": extras["depth"],
                "two_qubit_gates": extras["two_qubit_gates"],
                "nfev": extras["nfev"],
            })
            print(f"[M5] n={n} reps={reps} normalize={normalize} seed={seed} cost={result.cost} "
                  f"feasible={extras['feasible_fraction']:.4f} p_opt={extras['optimal_prob']:.4f} "
                  f"({result.seconds:.1f}s)", flush=True)
            pd.DataFrame(rows).to_csv(QAOA_CSV, index=False)
    return pd.DataFrame(rows)


def hybrid_part() -> tuple[pd.DataFrame, pd.DataFrame]:
    inst = load_instance(10)
    rows, step_rows = [], []
    for subsolver, neighborhood, k, seeds in HYBRID_RUNS:
        for seed in seeds:
            result = solve_hybrid_lns(inst, seed=seed, k=k, iterations=HYBRID_ITERATIONS,
                                      subsolver=subsolver, neighborhood=neighborhood)
            extras = result.extras
            run = f"{result.method}-{neighborhood}-k{k}"
            rows.append({
                **benchmark_row(result, inst),
                "run": run,
                "k": k,
                "neighborhood": neighborhood,
                "start_cost": extras["start_cost"],
                "improved_neighborhoods": extras["improved_neighborhoods"],
                "exact_could_improve": extras["exact_could_improve"],
                "sub_optimum_match_rate": extras.get("sub_optimum_match_rate"),
                "sub_optimum_prob": extras.get("sub_optimum_prob"),
                "no_feasible_sample": extras.get("no_feasible_sample"),
                "qaoa_seconds": extras.get("qaoa_seconds"),
                "perm": json.dumps(list(result.perm)),
            })
            for step in extras["steps"]:
                step_rows.append({"run": run, "seed": seed, **{
                    key: (json.dumps(value) if isinstance(value, list) else value)
                    for key, value in step.items()
                }})
            print(f"[M6] {run} seed={seed} start={extras['start_cost']} -> cost={result.cost} "
                  f"gap={gap_pct(result, inst):.1f}% improved={extras['improved_neighborhoods']} "
                  f"({result.seconds:.1f}s)", flush=True)
            pd.DataFrame(rows).to_csv(HYBRID_CSV, index=False)
            pd.DataFrame(step_rows).to_csv(STEPS_CSV, index=False)
    return pd.DataFrame(rows), pd.DataFrame(step_rows)


def plot_qaoa(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for (n, normalize), group in df.groupby(["n", "normalize"]):
        stats = group.groupby("reps")[["feasible_fraction", "optimal_prob"]].agg(["mean", "std"])
        label = f"N={n} {'normalizado' if normalize else 'sin normalizar'}"
        style = "o-" if normalize else "x--"
        for ax, col in zip(axes, ["feasible_fraction", "optimal_prob"]):
            ax.errorbar(stats.index, stats[col]["mean"], yerr=stats[col]["std"].fillna(0),
                        fmt=style, capsize=3, label=label)
    for n, group in df.groupby("n"):
        for ax, col in zip(axes, ["random_feasible_fraction", "random_optimal_prob"]):
            ax.axhline(group[col].iloc[0], color="gray", ls=":", alpha=0.8)
            ax.annotate(f"azar N={n}", (QAOA_REPS[-1], group[col].iloc[0]), fontsize=8,
                        color="gray", va="bottom", ha="right")
    for ax, label in zip(axes, ["fracción de shots factibles", "P(muestrear un óptimo)"]):
        ax.set_yscale("log")
        ax.set_xticks(QAOA_REPS)
        ax.set_xlabel("reps (capas QAOA)")
        ax.set_ylabel(label)
        ax.legend(fontsize=8)
    fig.suptitle(f"QAOA en Aer, λ = 2·λ*, COBYLA maxiter={QAOA_MAXITER}, {QAOA_SHOTS} shots, "
                 f"{len(QAOA_SEEDS)} seeds (media ± desv.)")
    fig.tight_layout()
    fig.savefig(FIGURES / "qaoa_reps.png", dpi=150)
    plt.close(fig)


def plot_hybrid(runs: pd.DataFrame, steps: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    colors = dict(zip(runs["run"].unique(), plt.rcParams["axes.prop_cycle"].by_key()["color"]))
    for (run, seed), group in steps.groupby(["run", "seed"]):
        trace = [group["cost_before"].iloc[0], *group["cost_after"]]
        axes[0].plot(range(len(trace)), trace, color=colors[run], alpha=0.6,
                     label=run if seed == steps[steps["run"] == run]["seed"].min() else None)
    axes[0].axhline(REFERENCE_OPTIMUM, color="black", ls="--", label="óptimo 340")
    axes[0].set_xlabel("iteración LNS")
    axes[0].set_ylabel("costo global (distancia total)")
    axes[0].set_title("Trayectoria del costo, N=10")
    axes[0].legend(fontsize=8)

    summary = runs.groupby("run").agg(gap=("gap_pct", "mean"), gap_min=("gap_pct", "min"),
                                      gap_max=("gap_pct", "max"), seconds=("seconds", "mean"))
    x = np.arange(len(summary))
    axes[1].bar(x, summary["gap"], color=[colors[r] for r in summary.index])
    axes[1].errorbar(x, summary["gap"], yerr=[summary["gap"] - summary["gap_min"],
                                              summary["gap_max"] - summary["gap"]],
                     fmt="none", color="black", capsize=4)
    for xi, (gap, sec) in enumerate(zip(summary["gap"], summary["seconds"])):
        axes[1].annotate(f"{gap:.1f}%\n{sec:.0f}s", (xi, gap), ha="center", va="bottom", fontsize=8)
    axes[1].set_xticks(x, summary.index, rotation=20, ha="right", fontsize=8)
    axes[1].set_ylabel("gap final vs 340 (%) · media, mín–máx")
    axes[1].set_title("Ablación: subsolver QAOA vs enumeración exacta")
    fig.suptitle(f"LNS híbrido, {HYBRID_ITERATIONS} iteraciones, arranque aleatorio con semilla")
    fig.tight_layout()
    fig.savefig(FIGURES / "qaoa_hybrid_lns.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", choices=["qaoa", "hybrid", "all"], default="all")
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    if not args.plot_only and args.part in {"qaoa", "all"}:
        qaoa_part()
    if not args.plot_only and args.part in {"hybrid", "all"}:
        hybrid_part()
    if QAOA_CSV.exists():
        plot_qaoa(pd.read_csv(QAOA_CSV))
    if HYBRID_CSV.exists() and STEPS_CSV.exists():
        plot_hybrid(pd.read_csv(HYBRID_CSV), pd.read_csv(STEPS_CSV))
    print(f"wrote results in {RESULTS} and figures in {FIGURES}")


if __name__ == "__main__":
    main()
