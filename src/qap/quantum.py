"""Qiskit-based solvers. Owner: Diego."""

from __future__ import annotations

from .types import Instance, Result


def solve_qaoa(inst: Instance, *, seed: int, **params) -> Result:
    raise NotImplementedError


def solve_hybrid_lns(inst: Instance, *, seed: int, **params) -> Result:
    raise NotImplementedError
