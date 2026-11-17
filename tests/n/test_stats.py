"""Unit tests for statistical inference module in quoridor_n."""
import pytest
from quoridor_n.stats import (
    binomial_test,
    bootstrap_mean_ci,
    holm_bonferroni,
    paired_sign_test,
    required_sample_size,
    wilson_interval,
)


def test_wilson_interval_reproduces_repo_baseline():
    # In 2-player repo: 12 wins out of 20 games produces [38.7%, 78.1%]
    low, high = wilson_interval(12, 20)
    assert round(low * 100, 1) == 38.7
    assert round(high * 100, 1) == 78.1


def test_exact_binomial_test_reproduces_repo_p_value():
    # In 2-player repo: 12 wins out of 20 against p0=0.5 produces p = 0.5034
    p = binomial_test(12, 20, p0=0.5)
    assert round(p, 4) == 0.5034


def test_binomial_test_four_player_chance():
    # 4-player chance is p0 = 0.25 (1 seat out of 4)
    # If agent wins 40 out of 100 games:
    p = binomial_test(40, 100, p0=0.25)
    assert p < 0.01  # Highly significant above chance (40% vs 25%)

    # If agent wins 25 out of 100 games:
    p_null = binomial_test(25, 100, p0=0.25)
    assert round(p_null, 4) == 1.0


def test_paired_sign_test():
    # 20 games where agent A ranks better in 15 games, B in 5 games
    ranks_a = [1.0] * 15 + [3.0] * 5
    ranks_b = [2.0] * 15 + [1.0] * 5
    res = paired_sign_test(ranks_a, ranks_b)

    assert res["wins_a"] == 15
    assert res["wins_b"] == 5
    assert res["ties"] == 0
    assert res["n_effective"] == 20
    assert res["p_value"] < 0.05


def test_bootstrap_mean_ci():
    data = [1.0, 2.0, 2.0, 3.0, 1.0, 2.0, 4.0, 2.0]
    mean_val, low, high = bootstrap_mean_ci(data, n_resamples=5000, seed=42)
    assert low <= mean_val <= high
    assert round(mean_val, 2) == round(sum(data) / len(data), 2)


def test_holm_bonferroni_correction():
    raw_p = [0.01, 0.04, 0.03, 0.20]
    adj_p = holm_bonferroni(raw_p)

    assert len(adj_p) == len(raw_p)
    # Adjusted p-values must be >= raw p-values
    for r, a in zip(raw_p, adj_p):
        assert a >= r
        assert 0.0 <= a <= 1.0


def test_required_sample_size_sanity_check():
    # Prompt specification sanity check:
    # "detecting 35% against 25% needs roughly 160 games"
    n = required_sample_size(p0=0.25, p1=0.35, alpha=0.05, power=0.80)
    assert 150 <= n <= 170, f"Expected ~160 games, got {n}"
