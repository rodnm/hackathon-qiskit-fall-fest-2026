"""Penalty study (M4): justify λ and check feasibility. Owner: Diego.

    uv run python -m qap.lambda_study               # full study, about 10 minutes
    uv run python -m qap.lambda_study --skip-qaoa   # exact parts only (threshold + spectrum)
    uv run python -m qap.lambda_study --plot-only   # redraw figures from results/lambda_*.csv

Three parts, all on the first n rows/columns of qap10:
  A. exact threshold λ* for n = 2..5 (enumeration of 2^(n²) vectors);
  B. exact spectrum of C + λ·P for n = 3, 4 over a range of λ/λ* (no QAOA);
  C. QAOA (Qiskit + Aer) for n = 3, 4 at λ ∈ {0.5, 1, 2, 4}·λ*, several seeds.
"""

from __future__ import annotations

import argparse
import json
import math
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from qiskit_optimization.converters import QuadraticProgramToQubo  # noqa: E402

from .data import ROOT, load_instance  # noqa: E402
from .model import build_qp, exact_optimum, penalty_threshold, spectrum_stats  # noqa: E402
from .quantum import solve_qaoa  # noqa: E402

RESULTS = ROOT / "results"
FIGURES = ROOT / "docs" / "figures"
THRESHOLD_CSV = RESULTS / "lambda_threshold.csv"
LANDSCAPE_CSV = RESULTS / "lambda_landscape.csv"
QAOA_CSV = RESULTS / "lambda_qaoa.csv"

THRESHOLD_SIZES = [2, 3, 4, 5]
LANDSCAPE_SIZES = [3, 4]
LANDSCAPE_FACTORS = [0.5, 0.75, 0.9, 1.1, 1.5, 2, 3, 4, 8, 16, 32]
QAOA_FACTORS = [0.5, 1, 2, 4]
QAOA_SEEDS = {3: [0, 1, 2, 3, 4], 4: [0, 1, 2]}
QAOA_PARAMS = {"reps": 1, "maxiter": 100, "shots": 4096}


def qiskit_auto_penalty(n: int) -> float:
    """Penalty that QuadraticProgramToQubo picks when none is given (for reference only)."""
    converter = QuadraticProgramToQubo()
    converter.convert(build_qp(load_instance(n)))
    return float(converter.penalty)


def threshold_table() -> pd.DataFrame:
    rows = []
    for n in THRESHOLD_SIZES:
        inst = load_instance(n)
        t0 = time.perf_counter()
        lam_star = penalty_threshold(inst)
        seconds = time.perf_counter() - t0
        optimum, n_optima = exact_optimum(inst)
        rows.append(
            {
                "n": n,
                "qubits": n * n,
                "optimum": optimum,
                "n_optima": n_optima,
                "lambda_star": lam_star,
                "lambda_star_over_optimum": lam_star / optimum,
                "qiskit_auto_penalty": qiskit_auto_penalty(n),
                "seconds": seconds,
            }
        )
        print(f"[A] n={n}  C*={optimum}  lambda*={lam_star:g}  ({seconds:.1f}s)")
    return pd.DataFrame(rows)


def landscape_table(thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n in LANDSCAPE_SIZES:
        inst = load_instance(n)
        lam_star = float(thresholds.set_index("n").loc[n, "lambda_star"])
        auto = float(thresholds.set_index("n").loc[n, "qiskit_auto_penalty"])
        factors = sorted(set(LANDSCAPE_FACTORS) | {auto / lam_star})
        for factor in factors:
            stats = spectrum_stats(inst, factor * lam_star)
            rows.append({"n": n, "lambda_factor": factor, "lambda_star": lam_star, **stats})
        print(f"[B] n={n}  {len(factors)} values of lambda")
    return pd.DataFrame(rows)


def qaoa_table(thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n, seeds in QAOA_SEEDS.items():
        inst = load_instance(n)
        lam_star = float(thresholds.set_index("n").loc[n, "lambda_star"])
        optimum, n_optima = exact_optimum(inst)
        for factor in QAOA_FACTORS:
            for seed in seeds:
                result = solve_qaoa(inst, seed=seed, penalty=factor * lam_star, **QAOA_PARAMS)
                extras = result.extras
                gap = None if result.cost is None else 100 * (result.cost - optimum) / optimum
                rows.append(
                    {
                        "n": n,
                        "lambda_factor": factor,
                        "lambda": factor * lam_star,
                        "seed": seed,
                        "feasible": result.feasible,
                        "best_cost": result.cost,
                        "gap_pct": gap,
                        "feasible_fraction": extras["feasible_fraction"],
                        "optimal_prob": extras["optimal_prob"],
                        "random_feasible_fraction": math.factorial(n) / 2 ** (n * n),
                        "random_optimal_prob": n_optima / 2 ** (n * n),
                        "penalized_energy": extras["penalized_energy"],
                        "nfev": extras["nfev"],
                        "depth": extras["depth"],
                        "two_qubit_gates": extras["two_qubit_gates"],
                        "seconds": result.seconds,
                        "params_json": json.dumps(result.params),
                    }
                )
                print(
                    f"[C] n={n}  lambda={factor:g}*lambda*  seed={seed}  cost={result.cost}  "
                    f"feasible={extras['feasible_fraction']:.4f}  "
                    f"p_opt={extras['optimal_prob']:.4f}  ({result.seconds:.1f}s)"
                )
                pd.DataFrame(rows).to_csv(QAOA_CSV, index=False)  # checkpoint after every run
    return pd.DataFrame(rows)


def plot_threshold(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(df["n"], df["lambda_star"], color="tab:blue", label="λ* (umbral exacto)")
    ax.plot(df["n"], df["optimum"], "o--", color="tab:gray", label="C* (cota segura λ* ≤ C*)")
    for n, lam, opt in zip(df["n"], df["lambda_star"], df["optimum"]):
        ax.annotate(f"{lam:g}", (n, lam), ha="center", va="bottom")
        ax.annotate(f"{opt}", (n, opt), ha="center", va="bottom", color="tab:gray")
    ax.set_xticks(df["n"], [f"N={n}\n({n * n} qubits)" for n in df["n"]])
    ax.set_ylabel("penalización")
    ax.set_title("Umbral de penalización λ* por enumeración exacta")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "lambda_threshold.png", dpi=150)
    plt.close(fig)


def plot_landscape(df: pd.DataFrame, thresholds: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for n, group in df.groupby("n"):
        group = group.sort_values("lambda_factor")
        line = axes[0].plot(group["lambda_factor"], group["rel_gap"], "o-", label=f"N={n}")[0]
        axes[1].plot(group["lambda_factor"], group["feasible_span"], "o-", label=f"N={n}")
        bad = group[~group["ground_optimal"]]
        axes[0].scatter(bad["lambda_factor"], bad["rel_gap"], s=120, facecolors="none",
                        edgecolors="red", zorder=3)
        auto = thresholds.set_index("n").loc[n, "qiskit_auto_penalty"]
        lam_star = thresholds.set_index("n").loc[n, "lambda_star"]
        for ax in axes:
            ax.axvline(auto / lam_star, color=line.get_color(), ls=":", alpha=0.7)
    for ax in axes:
        ax.axvspan(df["lambda_factor"].min(), 1, color="red", alpha=0.08)
        ax.set_xscale("log")
        ax.set_xlabel("λ / λ*")
        ax.legend()
    axes[0].set_ylabel("hueco relativo (E1 − E0) / (Emax − Emin)")
    axes[0].set_title("Hueco espectral (círculo rojo: mínimo no óptimo)")
    axes[1].set_ylabel("fracción del rango de energía con estados factibles")
    axes[1].set_title("Espacio que conserva el objetivo real")
    fig.suptitle("Zona roja: λ < λ*, mínimo no factible · punteado: penalización automática de Qiskit")
    fig.tight_layout()
    fig.savefig(FIGURES / "lambda_landscape.png", dpi=150)
    plt.close(fig)


def plot_qaoa(df: pd.DataFrame) -> None:
    metrics = [
        ("feasible_fraction", "random_feasible_fraction", "fracción de shots factibles", True),
        ("optimal_prob", "random_optimal_prob", "P(muestrear un óptimo)", True),
        ("gap_pct", None, "gap del mejor factible vs C* (%)", False),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for n, group in df.groupby("n"):
        stats = group.groupby("lambda_factor")[[m[0] for m in metrics]].agg(["mean", "std"])
        for ax, (col, baseline, label, log) in zip(axes, metrics):
            mean, std = stats[col]["mean"], stats[col]["std"].fillna(0)
            line = ax.errorbar(stats.index, mean, yerr=std, fmt="o-", capsize=3,
                               label=f"N={n} ({group['seed'].nunique()} seeds)")
            if baseline:
                ax.axhline(group[baseline].iloc[0], ls="--", color=line[0].get_color(), alpha=0.6,
                           label=f"N={n} azar uniforme")
            ax.set_ylabel(label)
            if log:
                ax.set_yscale("log")
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks(QAOA_FACTORS, [f"{f:g}" for f in QAOA_FACTORS])
        ax.set_xlabel("λ / λ*")
        ax.legend(fontsize=8)
    fig.suptitle(
        f"QAOA en Aer (reps={QAOA_PARAMS['reps']}, COBYLA maxiter={QAOA_PARAMS['maxiter']}, "
        f"{QAOA_PARAMS['shots']} shots) según la penalización"
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "lambda_qaoa.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-qaoa", action="store_true", help="only the exact parts A and B")
    parser.add_argument("--plot-only", action="store_true", help="redraw figures from the CSVs")
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    if args.plot_only:
        thresholds = pd.read_csv(THRESHOLD_CSV)
        landscape = pd.read_csv(LANDSCAPE_CSV)
        qaoa = pd.read_csv(QAOA_CSV) if QAOA_CSV.exists() else None
    else:
        thresholds = threshold_table()
        thresholds.to_csv(THRESHOLD_CSV, index=False)
        landscape = landscape_table(thresholds)
        landscape.to_csv(LANDSCAPE_CSV, index=False)
        qaoa = None if args.skip_qaoa else qaoa_table(thresholds)

    plot_threshold(thresholds)
    plot_landscape(landscape, thresholds)
    if qaoa is not None:
        plot_qaoa(qaoa)
    print(f"wrote CSVs in {RESULTS} and figures in {FIGURES}")


if __name__ == "__main__":
    main()
