"""Statistical analysis and confidence intervals for dynamic Quoridor."""
from __future__ import annotations

import math
import random
from typing import Any


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    # For 95% confidence, z ~ 1.959963984540054
    z = 1.959963984540054
    z2 = z * z
    p_hat = k / n
    denominator = 1 + z2 / n
    centre_adj = p_hat + z2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) / n) + (z2 / (4 * n * n)))
    lower = max(0.0, (centre_adj - margin) / denominator)
    upper = min(1.0, (centre_adj + margin) / denominator)
    return lower, upper


def binomial_pmf(k: int, n: int, p: float) -> float:
    """Exact binomial probability mass function."""
    if not (0 <= k <= n):
        return 0.0
    return math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def exact_two_sided_binomial_p(k: int, n: int, p0: float = 0.5) -> float:
    """Exact two-sided binomial p-value testing H0: p = p0."""
    if n == 0:
        return 1.0
    pk = binomial_pmf(k, n, p0)
    total_p = 0.0
    eps = 1e-12
    for j in range(n + 1):
        pj = binomial_pmf(j, n, p0)
        if pj <= pk + eps:
            total_p += pj
    return min(1.0, total_p)


def win_rate_test(
    wins: int,
    games: int,
    seats: int = 1,
    players: int = 4,
) -> dict[str, Any]:
    """Test win rate against theoretical null baseline p0 = seats / players."""
    p0 = seats / players
    rate = (wins / games) if games > 0 else 0.0
    low, high = wilson_interval(wins, games)
    p_val = exact_two_sided_binomial_p(wins, games, p0)
    return {
        "wins": wins,
        "games": games,
        "win_rate": rate,
        "p0": p0,
        "ci_low": low,
        "ci_high": high,
        "p_value": p_val,
        "significant": p_val < 0.05,
    }


def paired_sign_test(wins_a: int, wins_b: int) -> float:
    """Exact paired sign test testing H0: p(A beats B) = 0.5 among decisive pairs."""
    m = wins_a + wins_b
    if m == 0:
        return 1.0
    return exact_two_sided_binomial_p(wins_a, m, 0.5)


def mean_rank_bootstrap_ci(
    ranks: list[float],
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap confidence interval for mean rank."""
    if not ranks:
        return 0.0, 0.0, 0.0
    mean_val = sum(ranks) / len(ranks)
    if len(ranks) == 1:
        return mean_val, mean_val, mean_val

    rng = random.Random(seed)
    n = len(ranks)
    boot_means: list[float] = []
    for _ in range(n_boot):
        sample = [ranks[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()

    alpha = 1.0 - ci
    low_idx = int(alpha / 2.0 * n_boot)
    high_idx = int((1.0 - alpha / 2.0) * n_boot)
    return mean_val, boot_means[low_idx], boot_means[min(high_idx, n_boot - 1)]


def holm_bonferroni(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[tuple[float, float, bool]]:
    """Holm-Bonferroni correction for multiple hypothesis testing.

    Returns:
        List of tuples (raw_p, adj_p, is_significant) in the same order as p_values.
    """
    m = len(p_values)
    if m == 0:
        return []

    # Sort p-values with their original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m

    cum_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        mult = m - rank
        adj = min(1.0, p * mult)
        cum_max = max(cum_max, adj)
        adjusted[orig_idx] = cum_max

    results = []
    for raw_p, adj_p in zip(p_values, adjusted):
        results.append((raw_p, adj_p, adj_p < alpha))
    return results


def clustered_bootstrap_mean_ci(
    game_clusters: list[list[float]],
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap confidence interval over clustered game data.

    Resamples games (clusters) with replacement to account for intra-game correlation.
    """
    flat = [val for cl in game_clusters for val in cl]
    if not flat:
        return 0.0, 0.0, 0.0
    orig_mean = sum(flat) / len(flat)

    n_games = len(game_clusters)
    if n_games <= 1:
        return orig_mean, orig_mean, orig_mean

    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(n_boot):
        boot_vals: list[float] = []
        for _ in range(n_games):
            g_idx = rng.randrange(n_games)
            boot_vals.extend(game_clusters[g_idx])
        if boot_vals:
            boot_means.append(sum(boot_vals) / len(boot_vals))
        else:
            boot_means.append(orig_mean)
    boot_means.sort()

    alpha = 1.0 - ci
    low_idx = int(alpha / 2.0 * n_boot)
    high_idx = int((1.0 - alpha / 2.0) * n_boot)
    return orig_mean, boot_means[low_idx], boot_means[min(high_idx, n_boot - 1)]


def power_binomial(n: int, p1: float, p0: float, alpha: float = 0.05) -> float:
    """Exact power of a two-sided binomial test testing H0: p = p0 when true rate is p1."""
    if n <= 0:
        return 0.0
    power = 0.0
    for k in range(n + 1):
        p_val = exact_two_sided_binomial_p(k, n, p0)
        if p_val <= alpha + 1e-12:
            power += binomial_pmf(k, n, p1)
    return power


def sample_size_binomial(
    p1: float,
    p0: float,
    target_power: float = 0.80,
    alpha: float = 0.05,
    max_n: int = 1000,
) -> int:
    """Find the minimum sample size n achieving target power for testing p0 vs p1."""
    for n in range(10, max_n + 1):
        pw = power_binomial(n, p1, p0, alpha)
        if pw >= target_power:
            return n
    return max_n
