"""Tests for statistical methods in quoridor_n.stats."""
from __future__ import annotations

import pytest

from quoridor_n.stats import (
    clustered_bootstrap_mean_ci,
    exact_two_sided_binomial_p,
    holm_bonferroni,
    mean_rank_bootstrap_ci,
    paired_sign_test,
    power_binomial,
    sample_size_binomial,
    wilson_interval,
    win_rate_test,
)


def test_wilson_interval_and_exact_binomial_benchmark():
    """Verify reproduces exact benchmark: 12 of 20 gives p = 0.5034 and interval ~[0.387, 0.781]."""
    k, n = 12, 20
    low, high = wilson_interval(k, n)
    assert 0.385 <= low <= 0.390, f"Expected low ~0.387, got {low}"
    assert 0.780 <= high <= 0.785, f"Expected high ~0.781, got {high}"

    p_val = exact_two_sided_binomial_p(k, n, 0.5)
    assert round(p_val, 4) == 0.5034, f"Expected p=0.5034, got {p_val}"


def test_win_rate_test():
    """Verify win_rate_test helper outputs all expected keys."""
    res = win_rate_test(wins=45, games=100, seats=1, players=4)
    assert res["wins"] == 45
    assert res["games"] == 100
    assert res["win_rate"] == 0.45
    assert res["p0"] == 0.25
    assert res["significant"] is True  # 45/100 is significantly > 25%


def test_paired_sign_test():
    """Verify paired sign test computes exact binomial p for decisive matchups."""
    # 15 vs 5 decisive games
    p = paired_sign_test(15, 5)
    assert p < 0.05
    # 10 vs 10 decisive games
    p_tie = paired_sign_test(10, 10)
    assert p_tie == 1.0


def test_holm_bonferroni():
    """Verify Holm-Bonferroni maintains FWER and orders corrections monotonically."""
    raw_ps = [0.005, 0.04, 0.02, 0.15]
    adj = holm_bonferroni(raw_ps, alpha=0.05)
    assert len(adj) == 4
    # Lowest p (0.005) multiplied by 4 = 0.02
    assert adj[0][1] <= 0.02
    assert adj[0][2] is True


def test_mean_rank_and_clustered_bootstrap():
    """Verify bootstrap intervals contain the true sample mean."""
    ranks = [1.0, 2.0, 2.5, 4.0, 1.5, 3.0, 2.0, 1.0]
    mean_val, low, high = mean_rank_bootstrap_ci(ranks, n_boot=500, seed=42)
    assert low <= mean_val <= high

    clusters = [[1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [1.0, 0.0]]
    cl_mean, cl_low, cl_high = clustered_bootstrap_mean_ci(clusters, n_boot=500, seed=42)
    assert cl_low <= cl_mean <= cl_high


def test_power_calculations_confirm_sample_sizes():
    """Confirm power function: 35% vs 25% needs ~160 games; 60% vs 50% needs ~200 games."""
    n_35_25 = sample_size_binomial(0.35, 0.25, target_power=0.80)
    assert 140 <= n_35_25 <= 180, f"Expected ~160 games, got {n_35_25}"

    n_60_50 = sample_size_binomial(0.60, 0.50, target_power=0.80)
    assert 180 <= n_60_50 <= 220, f"Expected ~200 games, got {n_60_50}"
