"""Capa de servicio: única frontera entre la API y el paquete `qap` (reglas de S8).

- El coste de cada resultado se recalcula con `qap.types.cost`; nunca se copia el del solver.
- La referencia por N proviene de los óptimos de control verificados (24/32/340, tests de
  `qap.data`/`test_classical`); si el npz faltara, se recalcula con `solve_bruteforce`.
"""

import csv
import functools
import json
from pathlib import Path
from typing import Any

import numpy as np

from qap.classical import solve_bruteforce
from qap.data import load_instance
from qap.types import Instance, Result, cost

from .schemas import Assignment, GateCoord, InstanceOut, ResultOut, ValidateOut

ROOT = Path(__file__).resolve().parents[2]  # backend/app/service.py -> raíz del repo


def _plain(value: Any) -> Any:
    """Convierte escalares/arreglos de numpy a tipos JSON nativos (recursivo)."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


@functools.lru_cache(maxsize=None)
def reference(n: int) -> tuple[int, str]:
    """(coste de referencia, tipo) para n — óptimo demostrado de la instancia."""
    inst = load_instance(n)
    if inst.optimum is not None:
        return int(inst.optimum), "proven_optimum"
    res = solve_bruteforce(inst, seed=0)
    return int(res.cost), "proven_optimum"


@functools.lru_cache(maxsize=None)
def gate_layout() -> tuple[GateCoord, ...]:
    summary = json.loads(
        (ROOT / "data" / "processed" / "qap10_summary.json").read_text(encoding="utf-8")
    )
    coords = summary["gate_layout"]["coords_col_row"]
    return tuple(
        GateCoord(gate=j, col=col, row=row) for j, (col, row) in enumerate(coords)
    )


def instance_out(n: int) -> InstanceOut:
    inst = load_instance(n)
    return InstanceOut(
        name=inst.name,
        n=inst.n,
        F=inst.F.tolist(),
        D=inst.D.tolist(),
        optimum=inst.optimum,
        layout=list(gate_layout()[: inst.n]),
    )


def result_out(result: Result, inst: Instance) -> ResultOut:
    """Result -> ResultOut con coste recalculado, referencia y gap (solo factibles)."""
    perm = [int(g) for g in result.perm] if result.perm is not None else None
    feasible = bool(
        result.feasible and perm is not None and sorted(perm) == list(range(inst.n))
    )
    true_cost = int(cost(tuple(perm), inst)) if perm is not None else None
    ref, kind = reference(inst.n)
    gap = 100.0 * (true_cost - ref) / ref if (feasible and true_cost is not None) else None
    assignment = (
        [Assignment(flight=i, gate=g) for i, g in enumerate(perm)] if perm else []
    )
    return ResultOut(
        method=result.method,
        perm=perm,
        assignment=assignment,
        cost=true_cost,
        feasible=feasible,
        seconds=float(result.seconds),
        peak_mem_mb=float(result.peak_mem_mb),
        seed=result.seed,
        params=_plain(result.params),
        extras=_plain(result.extras),
        reference_cost=ref,
        gap_pct=gap,
        reference_kind=kind,
    )


def validate_matrices(F: list[list[int]], D: list[list[int]]) -> ValidateOut:
    """Valida {F, D} con mensajes que nombran la matriz (contrato de S2)."""
    errors: list[str] = []

    def check_shape(name: str, m: list[list[int]]) -> bool:
        if not m or any(not isinstance(row, list) or len(row) != len(m) for row in m):
            errors.append(f"{name}: debe ser una matriz cuadrada no vacía")
            return False
        return True

    f_ok = check_shape("F", F)
    d_ok = check_shape("D", D)
    if f_ok and d_ok and len(F) != len(D):
        errors.append("F y D: dimensiones incompatibles (len(F) != len(D))")
        f_ok = d_ok = False

    n = len(F) if f_ok else (len(D) if d_ok else 0)
    if n and n < 2:
        errors.append(f"n = {n}: se requiere n >= 2")

    for name, m, ok in (("F", F, f_ok), ("D", D, d_ok)):
        if not ok:
            continue
        bad = next(
            (
                f"{name}[{i}][{j}]: debe ser un entero >= 0 (recibido {v!r})"
                for i, row in enumerate(m)
                for j, v in enumerate(row)
                if isinstance(v, bool) or not isinstance(v, int) or v < 0
            ),
            None,
        )
        if bad is not None:
            errors.append(bad)

    if f_ok and n >= 2:
        symmetric = all(F[i][j] == F[j][i] for i in range(n) for j in range(n))
        upper = all(F[i][j] == 0 for i in range(n) for j in range(i))
        if not (symmetric or upper):
            errors.append(
                "F: debe ser simétrica (o triangular superior); se almacena triangular superior"
            )
    if d_ok and n >= 2:
        if any(D[i][j] != D[j][i] for i in range(n) for j in range(i)):
            errors.append("D: debe ser simétrica")
        if any(D[i][i] != 0 for i in range(n)):
            errors.append("D: la diagonal debe ser cero")

    return ValidateOut(ok=not errors, errors=errors[:20])


def benchmark_rows() -> list[dict[str, str]]:
    path = ROOT / "results" / "benchmark.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
