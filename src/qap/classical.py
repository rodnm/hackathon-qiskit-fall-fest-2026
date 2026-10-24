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


def swap_delta(perm: np.ndarray, r: int, s: int, F_sym: np.ndarray, D: np.ndarray) -> int:
    """Exact cost change of swapping the gates of flights r and s, in O(n).

    Δ = Σ_{k≠r,s} (F_sym[r,k] − F_sym[s,k]) · (D[p_s,p_k] − D[p_r,p_k]) for symmetric F_sym and D
    with zero diagonal (the r–s pair itself keeps its distance).
    """
    pr, ps = perm[r], perm[s]
    terms = (F_sym[r] - F_sym[s]) * (D[ps, perm] - D[pr, perm])
    return int(terms.sum() - terms[r] - terms[s])


def _swap_pairs(n: int) -> list[tuple[int, int]]:
    return [(r, s) for r in range(n) for s in range(r + 1, n)]


def _result(method: str, inst: Instance, perm: np.ndarray, seconds: float, peak_mb: float, seed: int,
            params: dict, extras: dict) -> Result:
    best = tuple(int(g) for g in perm)
    return Result(method=method, perm=best, cost=cost(best, inst), feasible=True, seconds=seconds,
                  peak_mem_mb=peak_mb, seed=seed, params=params, extras=extras)


def solve_local_search(inst: Instance, *, seed: int, restarts: int = 100) -> Result:
    """Multi-start steepest descent over pair swaps, from random permutations.

    Never uses the known optimum: fixed number of restarts, best permutation found is returned.
    """
    owns_tracing = _start_tracing()
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    n, F_sym, D = inst.n, inst.F_sym, inst.D
    pairs = _swap_pairs(n)
    best_perm, best_cost, local_costs, steps = None, None, [], 0
    for _ in range(restarts):
        perm = rng.permutation(n)
        current = cost(perm, inst)
        while pairs:
            deltas = [swap_delta(perm, r, s, F_sym, D) for r, s in pairs]
            i = int(np.argmin(deltas))
            if deltas[i] >= 0:
                break
            r, s = pairs[i]
            perm[r], perm[s] = perm[s], perm[r]
            current += deltas[i]
            steps += 1
        local_costs.append(current)
        if best_cost is None or current < best_cost:
            best_perm, best_cost = perm.copy(), current
    seconds = time.perf_counter() - start
    peak_mb = _stop_tracing(owns_tracing)
    return _result(
        "local_search", inst, best_perm, seconds, peak_mb, seed, {"restarts": restarts},
        {"local_optima_distinct_costs": len(set(local_costs)),
         "restarts_at_best_found": local_costs.count(best_cost),
         "mean_local_optimum_cost": float(np.mean(local_costs)), "improving_swaps": steps},
    )


def solve_sa(
    inst: Instance,
    *,
    seed: int,
    iters: int = 10_000,
    restarts: int = 10,
    t0: float | None = None,
    alpha: float | None = None,
    final_ratio: float = 1e-3,
    history_every: int = 500,
) -> Result:
    """Simulated annealing over pair swaps with exact O(n) deltas and geometric cooling.

    t0=None calibrates the start temperature so that ~80 % of uphill moves are accepted at first
    (median uphill delta of random swaps); alpha=None cools from t0 to final_ratio·t0 in `iters`
    steps. Each restart begins from a new random permutation; the known optimum is never used.
    """
    owns_tracing = _start_tracing()
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    n, F_sym, D = inst.n, inst.F_sym, inst.D
    if t0 is None:
        uphill = []
        for _ in range(200):
            perm = rng.permutation(n)
            r, s = rng.choice(n, size=2, replace=False)
            delta = swap_delta(perm, int(r), int(s), F_sym, D)
            if delta > 0:
                uphill.append(delta)
        t0 = float(-np.median(uphill) / np.log(0.8)) if uphill else 1.0
    if alpha is None:
        alpha = final_ratio ** (1 / max(iters, 1))

    best_perm, best_cost, history, accepted = None, None, [], 0
    for _ in range(restarts):
        perm = rng.permutation(n)
        current = cost(perm, inst)
        if best_cost is None or current < best_cost:
            best_perm, best_cost = perm.copy(), current
        temperature = t0
        draws = rng.integers(0, n, size=(iters, 2))
        uniforms = rng.random(iters)
        for step in range(iters):
            r, s = int(draws[step, 0]), int(draws[step, 1])
            if r != s:
                delta = swap_delta(perm, r, s, F_sym, D)
                if delta <= 0 or uniforms[step] < np.exp(-delta / temperature):
                    perm[r], perm[s] = perm[s], perm[r]
                    current += delta
                    accepted += 1
                    if current < best_cost:
                        best_perm, best_cost = perm.copy(), current
            temperature *= alpha
            if step % history_every == 0:
                history.append(int(best_cost))
    seconds = time.perf_counter() - start
    peak_mb = _stop_tracing(owns_tracing)
    return _result(
        "sa", inst, best_perm, seconds, peak_mb, seed,
        {"iters": iters, "restarts": restarts, "t0": round(t0, 4), "alpha": alpha, "final_ratio": final_ratio},
        {"history_best_cost": history, "history_every": history_every,
         "acceptance_rate": accepted / max(iters * restarts, 1)},
    )
