"""Statistics for comparing solvers with the challenge's metrics. Owner: Rodrigo.

The challenge defines the gap only for the full instance and only on valid solutions:
gap(%) = 100 (C - 340) / 340. For the reduced instances (N < 10) we report the distance to the
control optimum in a separate column, as our own extension.
"""

from __future__ import annotations

import math

from scipy.stats import binomtest, norm

C_STAR = 340  # reference optimum of the full instance (n = 10)
N_FULL = 10


def _missing(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def random_floor(n: int, n_optima: int) -> tuple[float, float]:
    """(feasible fraction, optimal probability) of uniformly random one-hot bitstrings (n² qubits)."""
    states = 2 ** (n * n)
    return math.factorial(n) / states, n_optima / states


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval (95 % by default) for a proportion k/n."""
    if n == 0:
        return math.nan, math.nan
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def binomial_vs_floor(k: int, n: int, p0: float) -> float:
    """One-sided p-value of observing >= k successes in n trials if the true rate were the floor p0."""
    return float(binomtest(k, n, p0, alternative="greater").pvalue)


def shots_for_power(p0: float, multiple: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Shots needed to detect a rate of `multiple` x p0 against p0 (one-sided normal approximation)."""
    p1 = multiple * p0
    z_alpha, z_beta = norm.ppf(1 - alpha), norm.ppf(power)
    numerator = z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p1 * (1 - p1))
    return math.ceil((numerator / (p1 - p0)) ** 2)


def gap_pct(cost: float | None, n: int) -> float | None:
    """Challenge gap 100 (C - 340) / 340: only for the full instance (n = 10) and a valid cost."""
    if n != N_FULL or _missing(cost):
        return None
    return 100 * (cost - C_STAR) / C_STAR


def gap_vs_control_pct(cost: float | None, optimum: float | None) -> float | None:
    """Distance to the control optimum of a reduced instance (our extension, not the challenge gap)."""
    if _missing(cost) or _missing(optimum):
        return None
    return 100 * (cost - optimum) / optimum
