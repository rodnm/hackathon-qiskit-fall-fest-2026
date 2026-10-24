"""Analiza la instancia MIPLIB ``qap10`` y reconstruye el QAP subyacente.

El fichero MPS no es un QUBO: es una linealizacion del QAP con 100 variables de
asignacion ``X`` y 4050 variables producto ``Y``. Este script:

1. Parsea el MPS (sin dependencias de solvers).
2. Verifica la estructura de la linealizacion.
3. Reconstruye las matrices de flujos ``F`` y distancias ``D``.
4. Opcionalmente enumera las 10! asignaciones para obtener el optimo exacto.

Uso:
    uv run python src/analyze_qap10.py
    uv run python src/analyze_qap10.py --solve
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
from pathlib import Path

import numpy as np

N = 10
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "qap10.mps" / "qap10.mps"


def open_text(path: Path):
    """Abre un MPS en texto plano o comprimido con gzip."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def parse_mps(path: Path):
    """Devuelve (nombre, filas, columnas, rhs) de un MPS entero."""
    section = None
    name = ""
    rows: list[tuple[str, str]] = []
    cols: dict[str, dict[str, float]] = collections.OrderedDict()
    rhs: dict[str, float] = {}
    current = None

    with open_text(path) as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if not line.startswith(" "):
                section = line.split()[0]
                if section == "NAME":
                    name = line.split(maxsplit=1)[1].strip()
                continue
            if "'MARKER'" in line:
                continue
            tokens = line.split()
            if section == "ROWS":
                rows.append((tokens[0], tokens[1]))
            elif section == "COLUMNS":
                current = tokens[0]
                cols.setdefault(current, {})[tokens[1]] = float(tokens[2])
                if len(tokens) == 5:
                    cols[current][tokens[3]] = float(tokens[4])
            elif section == "RHS":
                rhs[tokens[1]] = float(tokens[2])
                if len(tokens) == 5:
                    rhs[tokens[3]] = float(tokens[4])

    return name, rows, cols, rhs


def x_to_facility_location(index: int) -> tuple[int, int]:
    """Convierte el indice 1..100 de ``X`` a (instalacion, localizacion) 1-based."""
    return (index - 1) // N + 1, (index - 1) % N + 1


def build_qap(rows, cols):
    """Reconstruye F, D y Q a partir de las variables Y y las filas C."""
    rowcol: dict[str, dict[str, float]] = {name: {} for _, name in rows}
    for var, coefficients in cols.items():
        for row, value in coefficients.items():
            rowcol[row][var] = value

    # Cada Y aparece en 4 filas C y enlaza exactamente dos variables X.
    y_to_x: dict[str, tuple[str, str]] = {}
    for var in (v for v in cols if v.startswith("Y")):
        partners = sorted(
            {
                x
                for row in cols[var]
                for x in rowcol[row]
                if x.startswith("X")
            }
        )
        if len(partners) != 2:
            raise ValueError(f"{var}: se esperaban 2 X, se encontraron {partners}")
        y_to_x[var] = (partners[0], partners[1])

    # Q[i, k, j, l] = coeficiente de x_ij * x_kl.
    q = np.zeros((N + 1, N + 1, N + 1, N + 1))
    for var, (xa, xb) in y_to_x.items():
        i, j = x_to_facility_location(int(xa[1:]))
        k, l = x_to_facility_location(int(xb[1:]))
        q[i, k, j, l] = cols[var].get("NOBJ", 0.0)

    # Q = F_ik * D_jl. La matriz de localizaciones del par (1, 2) es 10 * D.
    d = q[1, 2, 1:, 1:] / q[1, 2, 1, 2]
    f = q[:, :, 1, 2]
    f = f + f.T
    return f[1:, 1:], d, q, y_to_x


def exact_solve(f: np.ndarray, d: np.ndarray, chunk_size: int = 200_000):
    """Enumera 10! permutaciones y devuelve (optimo, asignacion, valores)."""
    values = []
    best = float("inf")
    best_perm = None
    iterator = itertools.permutations(range(N))
    while True:
        chunk = np.array(list(itertools.islice(iterator, chunk_size)), dtype=np.int8)
        if chunk.size == 0:
            break
        objective = np.zeros(len(chunk), dtype=np.float64)
        for i in range(N):
            for k in range(i + 1, N):
                if f[i, k]:
                    objective += f[i, k] * d[chunk[:, i], chunk[:, k]]
        index = int(objective.argmin())
        if objective[index] < best:
            best = float(objective[index])
            best_perm = tuple(int(v) + 1 for v in chunk[index])
        values.append(objective.astype(np.int32))
    return best, best_perm, np.concatenate(values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--solve",
        action="store_true",
        help="enumera las 10! permutaciones para calcular el optimo exacto",
    )
    args = parser.parse_args()

    name, rows, cols, rhs = parse_mps(args.path)
    x_vars = [v for v in cols if v.startswith("X")]
    y_vars = [v for v in cols if v.startswith("Y")]
    row_types = collections.Counter(kind for kind, _ in rows)
    nnz = sum(len(c) for c in cols.values())
    row_nnz = collections.Counter(
        sum(1 for c in cols.values() if row in c) for _, row in rows
    )
    print(f"Instancia: {name}")
    print(f"Filas: {len(rows)} {dict(row_types)}")
    print(f"Columnas: {len(cols)} (X={len(x_vars)}, Y={len(y_vars)})")
    print(f"RHS distintos: {sorted(set(rhs.values()))}")
    print(f"NNZ: {nnz}  densidad: {nnz / (len(cols) * len(rows)):.4%}")
    print(f"NNZ por fila: {dict(row_nnz)}")
    print(
        "NNZ por columna:",
        dict(collections.Counter(len(coefficients) for coefficients in cols.values())),
    )
    print(
        "Y con objetivo cero:",
        sum(1 for v in y_vars if cols[v].get("NOBJ", 0.0) == 0),
        "/",
        len(y_vars),
    )

    f, d, q, y_to_x = build_qap(rows, cols)
    error = max(
        np.abs(q[i + 1, k + 1, 1:, 1:] - f[i, k] * d).max()
        for i in range(N)
        for k in range(i + 1, N)
    )
    print(f"\nPares Y -> X: {len(y_to_x)} (esperados 45*90 = {45 * 90})")
    print(f"Factorizacion Q = F*D, error maximo: {error:.2e}")
    print(f"F simetrica: {np.allclose(f, f.T)}  D simetrica: {np.allclose(d, d.T)}")
    print(f"F: {int((np.triu(f, 1) > 0).sum())}/45 pares no nulos, max={f.max():.0f}")
    print(f"D: max={d.max():.0f}, valores={sorted(set(d.ravel().tolist()))}")
    print("\nF =")
    print(f.astype(int))
    print("\nD =")
    print(d.astype(int))

    if args.solve:
        optimum, assignment, values = exact_solve(f, d)
        print("\n--- Enumeracion exacta (10! = 3,628,800) ---")
        print(f"Optimo: {optimum:.0f}")
        print(f"Asignacion optima (instalacion -> localizacion): {assignment}")
        print(
            "Distribucion: "
            f"min={values.min()} max={values.max()} "
            f"media={values.mean():.2f} mediana={np.median(values):.0f} "
            f"std={values.std():.2f}"
        )
        print(f"Optimos: {int((values == optimum).sum())}")
        print(f"Permutaciones con objetivo <= 400: {int((values <= 400).sum())}")


if __name__ == "__main__":
    main()
