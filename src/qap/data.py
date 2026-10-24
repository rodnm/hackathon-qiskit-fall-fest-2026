"""Instance loading. Owner: Rodrigo.

The MIPLIB file qap10.mps.gz is the Adams-Johnson linearization of a 10x10 QAP. Each `Y` column
is the product x_ij * x_kl (i < k, j != l) with objective coefficient F_ik * D_jl, so F and D can
be recovered by factorizing those coefficients. `python -m qap.data` regenerates data/qap10_FD.npz.
"""

from __future__ import annotations

import gzip
import re
from functools import lru_cache
from math import gcd
from pathlib import Path

import numpy as np

from .types import Instance

N_FULL = 10
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MPS_PATH = DATA_DIR / "qap10.mps.gz"
NPZ_PATH = DATA_DIR / "qap10_FD.npz"

_ROW_X = re.compile(r"C\d+A(\d+)$")


def parse_coefficients(path: Path = MPS_PATH) -> np.ndarray:
    """Objective coefficient of each linearization var: P[i, k, j, l] = F[i, k] * D[j, l]."""
    columns: dict[str, list[tuple[str, str]]] = {}
    section = None
    with gzip.open(path, "rt") as handle:
        for line in handle:
            if not line.startswith(" "):
                section = line.split()[0]
                continue
            if section != "COLUMNS" or "MARKER" in line:
                continue
            tokens = line.split()
            if tokens[0].startswith("Y"):
                # A column's entries span several lines: aggregate by column name.
                columns.setdefault(tokens[0], []).extend(zip(tokens[1::2], tokens[2::2]))

    P = np.zeros((N_FULL,) * 4, dtype=np.int64)
    for name, entries in columns.items():
        objective, indices = 0, set()
        for row, value in entries:
            if row == "NOBJ":
                objective = int(float(value))
            else:
                match = _ROW_X.match(row)
                if match is None:
                    raise ValueError(f"column {name}: unexpected row name {row!r}")
                indices.add(int(match.group(1)))
        if len(indices) != 2:
            raise ValueError(f"column {name}: expected two X variables, found {sorted(indices)}")
        a, b = sorted(indices)
        i, j = divmod(a - 1, N_FULL)
        k, l = divmod(b - 1, N_FULL)
        if not (i < k and j != l):
            raise ValueError(f"column {name}: variables x[{i},{j}] and x[{k},{l}] are not i<k, j!=l")
        P[i, k, j, l] = objective
    return P


def factor_matrices(P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split P[i, k, j, l] into F (upper-triangular flows) and D (distances).

    D is block (0, 1) divided by the gcd of its entries, so the scale constant lives in F.
    Every other block must be an exact integer multiple of D (the rank-1 verification).
    """
    n = P.shape[0]
    block = P[0, 1]
    scale = gcd(*(int(v) for v in block[block != 0]))
    D = block // scale
    mask = D != 0
    F = np.zeros((n, n), dtype=np.int64)
    for i in range(n):
        for k in range(i + 1, n):
            other = P[i, k]
            quotient, remainder = np.divmod(other[mask], D[mask])
            if remainder.any() or (quotient != quotient[0]).any() or other[~mask].any():
                raise ValueError(f"block (i={i}, k={k}) is not rank-1: F[i,k] * D does not fit it")
            F[i, k] = quotient[0]
    return F, D


def recover_matrices(path: Path = MPS_PATH) -> tuple[np.ndarray, np.ndarray]:
    """F (upper-triangular) and D recovered from the MPS file."""
    return factor_matrices(parse_coefficients(path))


@lru_cache(maxsize=1)
def _stored() -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    if NPZ_PATH.exists():
        with np.load(NPZ_PATH) as stored:
            return stored["F"], stored["D"], stored["optima"]
    F, D = recover_matrices()
    return F, D, None


def load_instance(n: int = N_FULL) -> Instance:
    """First n rows/columns of the qap10 matrices; `optimum` is None if the npz is missing."""
    if not 2 <= n <= N_FULL:
        raise ValueError(f"n must be between 2 and {N_FULL}, got {n}")
    F, D, optima = _stored()
    optimum = None if optima is None else int(optima[n])
    return Instance(f"qap10-n{n}", n, F[:n, :n].copy(), D[:n, :n].copy(), optimum)


def main() -> None:
    """Regenerate data/qap10_FD.npz and the CSV copies, with exact optima for n = 2..10."""
    from .classical import solve_bruteforce

    F, D = recover_matrices()
    optima = np.full(N_FULL + 1, -1, dtype=np.int64)
    for n in range(2, N_FULL + 1):
        result = solve_bruteforce(Instance(f"qap10-n{n}", n, F[:n, :n], D[:n, :n]))
        optima[n] = result.cost
        print(f"n={n:2d}  optimum={result.cost:4d}  {result.seconds:6.2f}s")
    np.savez(NPZ_PATH, F=F, D=D, optima=optima)
    np.savetxt(DATA_DIR / "qap10_F.csv", F, fmt="%d", delimiter=",")
    np.savetxt(DATA_DIR / "qap10_D.csv", D, fmt="%d", delimiter=",")
    print(f"wrote {NPZ_PATH.name}, qap10_F.csv, qap10_D.csv in {DATA_DIR}")


if __name__ == "__main__":
    main()
