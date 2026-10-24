"""Shared contracts. Frozen after merge: announce any change to the team."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Instance:
    """Flights (items) to gates (locations). Pairs are counted once (i < k)."""

    name: str
    n: int
    F: np.ndarray  # (n, n) int, upper-triangular flows: F[i, k] with i < k, zeros elsewhere
    D: np.ndarray  # (n, n) int, symmetric distances, zero diagonal
    optimum: int | None = None

    def __post_init__(self) -> None:
        shape = (self.n, self.n)
        if self.F.shape != shape or self.D.shape != shape:
            raise ValueError(f"F and D must have shape {shape}")
        if not np.array_equal(self.F, np.triu(self.F, 1)):
            raise ValueError("F must be strictly upper-triangular")
        if not np.array_equal(self.D, self.D.T) or np.any(np.diag(self.D)):
            raise ValueError("D must be symmetric with a zero diagonal")

    @property
    def F_sym(self) -> np.ndarray:
        return self.F + self.F.T


@dataclass
class Result:
    method: str  # "bruteforce" | "sa" | "qaoa" | "hybrid_lns" | ...
    perm: tuple[int, ...] | None  # perm[i] = gate of flight i; None if nothing feasible was found
    cost: int | None  # true cost of perm, never the penalized energy
    feasible: bool
    seconds: float
    peak_mem_mb: float
    seed: int | None
    params: dict = field(default_factory=dict)  # everything needed to reproduce the run
    extras: dict = field(default_factory=dict)  # penalized_energy, feasible_fraction, history, ...


def cost(perm: tuple[int, ...] | np.ndarray, inst: Instance) -> int:
    """Sum over i < k of F[i, k] * D[perm[i], perm[k]]: the single source of truth for scale."""
    return int(costs(np.asarray(perm)[None, :], inst)[0])


def costs(perms: np.ndarray, inst: Instance) -> np.ndarray:
    """Vectorized cost of a (m, n) array of permutations."""
    i, k = np.triu_indices(inst.n, 1)
    return (inst.F[i, k] * inst.D[perms[:, i], perms[:, k]]).sum(axis=1)
