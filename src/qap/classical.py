"""Classical baselines. Owner: Rodrigo."""

from __future__ import annotations

import time
import tracemalloc
from itertools import chain, islice, permutations
from math import factorial

import numpy as np

from .types import Instance, Result, cost, costs

CHUNK = 200_000


def _start_tracing() -> bool:
    """Start tracemalloc unless a caller (e.g. the benchmark) already traces; return ownership."""
    owns = not tracemalloc.is_tracing()
    if owns:
        tracemalloc.start()
    tracemalloc.reset_peak()
    return owns


def _stop_tracing(owns: bool) -> float:
    """Peak traced memory in MiB since _start_tracing; stop tracing only if we started it."""
    _, peak = tracemalloc.get_traced_memory()
    if owns:
        tracemalloc.stop()
    return peak / 2**20


def solve_bruteforce(inst: Instance, *, seed: int = 0) -> Result:
    """Exact solver: enumerates every permutation in chunks, never storing them all."""
    owns_tracing = _start_tracing()
    start = time.perf_counter()
    n = inst.n
    best_cost, best_perm = None, None
    perms = permutations(range(n))
    while True:
        flat = np.fromiter(chain.from_iterable(islice(perms, CHUNK)), dtype=np.int8)
        if flat.size == 0:
            break
        chunk = flat.reshape(-1, n).astype(np.int64)
        values = costs(chunk, inst)
        idx = int(values.argmin())  # argmin keeps the first minimum: deterministic ties
        if best_cost is None or values[idx] < best_cost:
            best_cost, best_perm = int(values[idx]), chunk[idx]
    seconds = time.perf_counter() - start
    peak_mb = _stop_tracing(owns_tracing)
    perm = tuple(int(g) for g in best_perm)
    return Result(
        method="bruteforce",
        perm=perm,
        cost=cost(perm, inst),
        feasible=True,
        seconds=seconds,
        peak_mem_mb=peak_mb,
        seed=seed,
        params={"chunk": CHUNK},
        extras={"proven_optimum": True, "evaluated": factorial(n)},
    )


def solve_sa(inst: Instance, *, seed: int, **params) -> Result:
    raise NotImplementedError
