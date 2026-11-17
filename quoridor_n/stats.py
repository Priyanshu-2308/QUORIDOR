"""Statistical inference utilities for multi-agent Quoridor experiments."""
from __future__ import annotations

import math
import random
from typing import Any, Sequence


def wilson_interval(wins: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.
    
    Returns:
        (lower_bound, upper_bound) in range [0.0, 1.0].
    """
    if n <= 0:
        return (0.0, 1.0)

    # Standard normal quantile: 1.95996 for 95% confidence
    if abs(confidence - 0.95) < 1e-4:
        z = 1.959963984540054
    else:
        # Approximate using rational formula if other confidence passed
        alpha = 1.0 - confidence
        z = math.sqrt(2.0) * math.erfcinv(alpha)  # type: ignore

    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half_width = (z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)) / denom

    return (max(0.0, center - half_width), min(1.0, center + half_width))


def binomial_test(wins: int, n: int, p0: float = 0.5) -> float:
    """Exact two-sided binomial test against arbitrary null probability p0.
    
    The two-sided p-value is defined as the sum of probabilities of all outcomes
    that are no more likely than the observed outcome under the null hypothesis.
    """
    if n <= 0:
        return 1.0
    if not (0.0 < p0 < 1.0):
        raise ValueError(f"p0 must be in (0, 1), got {p0}")

    # Compute exact binomial probability mass function P(k) = C(n, k) * p0^k * (1 - p0)^(n - k)
    log_p0 = math.log(p0)
    log_q0 = math.log(1.0 - p0)

    pmf: list[float] = []
    for k in range(n + 1):
        log_prob = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * log_p0 + (n - k) * log_q0
        pmf.append(math.exp(log_prob))

    obs_prob = pmf[wins]
    tol = 1e-12

    # Two-sided p-value: sum of probabilities where P(k) <= P(wins) + tol
    p_value = sum(p for p in pmf if p <= obs_prob + tol)
    return min(1.0, p_value)


def paired_sign_test(ranks_a: Sequence[float], ranks_b: Sequence[float]) -> dict[str, Any]:
    """Non-parametric paired sign test on game ranks for two agents at the same table.
    
    Tests whether Agent A has a significantly different rank distribution than Agent B.
    """
    if len(ranks_a) != len(ranks_b):
        raise ValueError("ranks sequences must have equal length")

    wins_a = 0
    wins_b = 0
    ties = 0

    for ra, rb in zip(ranks_a, ranks_b):
        if ra < rb:  # Lower rank is better (e.g. 1st is better than 2nd)
            wins_a += 1
        elif rb < ra:
            wins_b += 1
        else:
            ties += 1

    n_diff = wins_a + wins_b
    p_value = binomial_test(wins_a, n_diff, p0=0.5) if n_diff > 0 else 1.0

    return {
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties": ties,
        "n_effective": n_diff,
        "p_value": p_value,
    }


def bootstrap_mean_ci(
    data: Sequence[float],
    n_resamples: int = 10000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap percentile 95% confidence interval for the mean.
    
    Returns:
        (observed_mean, lower_ci, upper_ci).
    """
    n = len(data)
    if n == 0:
        return (0.0, 0.0, 0.0)

    obs_mean = sum(data) / n
    if n == 1:
        return (obs_mean, obs_mean, obs_mean)

    rng = random.Random(seed)
    boot_means: list[float] = []

    for _ in range(n_resamples):
        sample = [data[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = (1.0 - confidence) / 2.0
    low_idx = int(math.floor(alpha * n_resamples))
    high_idx = int(math.ceil((1.0 - alpha) * n_resamples)) - 1
    high_idx = min(high_idx, n_resamples - 1)

    return (obs_mean, boot_means[low_idx], boot_means[high_idx])


def holm_bonferroni(p_values: Sequence[float]) -> list[float]:
    """Adjust a family of p-values using the step-down Holm-Bonferroni method."""
    m = len(p_values)
    if m == 0:
        return []

    # Sort indices by raw p-value
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted_indexed: list[tuple[int, float]] = []

    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        mult = m - rank
        raw_adj = mult * p
        running_max = max(running_max, raw_adj)
        adj_p = min(1.0, running_max)
        adjusted_indexed.append((orig_idx, adj_p))

    # Restore original order
    adjusted_indexed.sort(key=lambda item: item[0])
    return [p for _, p in adjusted_indexed]


def required_sample_size(
    p0: float,
    p1: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Calculate the required sample size to detect a win rate p1 against null p0.
    
    Uses standard asymptotic normal formula:
        n = (z_{alpha/2} * sqrt(p0 * (1 - p0)) + z_{power} * sqrt(p1 * (1 - p1)))^2 / (p1 - p0)^2
    """
    diff = abs(p1 - p0)
    if diff < 1e-6:
        raise ValueError("p1 must differ from p0")

    # Quantiles for alpha=0.05 two-sided and power=0.80
    z_alpha = 1.959963984540054
    z_beta = 0.8416212335729143

    var0 = p0 * (1.0 - p0)
    var1 = p1 * (1.0 - p1)

    numerator = z_alpha * math.sqrt(var0) + z_beta * math.sqrt(var1)
    n = (numerator / diff) ** 2
    return int(math.ceil(n))
