"""Classical baselines. Owner: Rodrigo."""

from __future__ import annotations

from .types import Instance, Result


def solve_bruteforce(inst: Instance, *, seed: int = 0) -> Result:
    raise NotImplementedError


def solve_sa(inst: Instance, *, seed: int, **params) -> Result:
    raise NotImplementedError
