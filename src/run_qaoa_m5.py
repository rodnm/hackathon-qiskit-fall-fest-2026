"""M5: QAOA completo en N pequeño con el Camino B.

Ejecuta solve_qaoa para N=3 (9 qubits) y N=4 (16 qubits) con:
- reps ∈ {1,2,3}
- maxiter ≈ 100-200
- shots = 4096
- inicialización pequeña y fija por semilla
- semillas 0-4
Guarda resultados en results/qaoa_m5.csv y logs.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from qap.model import penalty_threshold
from qap.quantum import solve_qaoa
from qap.types import Instance


F = np.array([[0,10,4,8],[0,0,6,0],[0,0,0,0],[0,0,0,0]])
D = np.array([[0,1,2,3],[1,0,1,2],[2,1,0,1],[3,2,1,0]])


def instance(n: int) -> Instance:
    return Instance(f"test{n}", n, F[:n,:n].copy(), D[:n,:n].copy())


def run():
    root = Path(__file__).resolve().parents[1]
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for n in [3, 4]:
        inst = instance(n)
        lam = penalty_threshold(inst) * 2.0  # 1.5-2x lambda*
        for reps in [1, 2, 3]:
            for seed in [0, 1, 2, 3, 4]:
                maxiter = 150 if reps >= 2 else 100
                print(f"Running N={n} reps={reps} seed={seed} maxiter={maxiter} lambda={lam:.3f}")
                t0 = time.time()
                try:
                    res = solve_qaoa(
                        inst,
                        seed=seed,
                        reps=reps,
                        maxiter=maxiter,
                        shots=4096,
                        penalty=lam,
                    )
                    elapsed = time.time() - t0
                    rows.append({
                        "n": n,
                        "reps": reps,
                        "seed": seed,
                        "maxiter": maxiter,
                        "shots": 4096,
                        "lambda": lam,
                        "method": res.method,
                        "qubits": res.extras.get("qubits"),
                        "pauli_terms": res.extras.get("pauli_terms"),
                        "depth": res.extras.get("depth"),
                        "two_qubit_gates": res.extras.get("two_qubit_gates"),
                        "feasible": res.feasible,
                        "best_feasible_cost": res.cost,
                        "optimum": inst.optimum,
                        "brute_force": inst.optimum,
                        "feasible_fraction": res.extras.get("feasible_fraction"),
                        "optimal_prob": res.extras.get("optimal_prob"),
                        "penalized_energy": res.extras.get("penalized_energy"),
                        "nfev": res.extras.get("nfev"),
                        "seconds": res.seconds,
                        "peak_mem_mb": res.peak_mem_mb,
                    })
                    print(f"  -> cost={res.cost} feasible={res.feasible} ff={res.extras.get('feasible_fraction'):.4f} opt_prob={res.extras.get('optimal_prob'):.4f} t={res.seconds:.2f}s")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    rows.append({
                        "n": n,
                        "reps": reps,
                        "seed": seed,
                        "maxiter": maxiter,
                        "shots": 4096,
                        "lambda": lam,
                        "error": str(e),
                    })
    
    csv_path = results_dir / "qaoa_m5.csv"
    if rows:
        keys = rows[0].keys()
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved {csv_path}")
    
    with open(logs_dir / "qaoa_m5_summary.json", "w") as f:
        json.dump(rows, f, indent=2)
    print(f"Saved logs/qaoa_m5_summary.json")


if __name__ == "__main__":
    run()
