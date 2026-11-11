"""Tests for tournament harness."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from quoridor.tournament import run_match


def test_run_match_workers_consistency_and_seat_swapping():
    """Verify 4-game greedy vs random run with workers=2 matches workers=1 and swaps seats."""
    # Run with 2 workers
    res_w2 = run_match("greedy", "random", games=4, seed=42, workers=2)
    # Run with 1 worker
    res_w1 = run_match("greedy", "random", games=4, seed=42, workers=1)

    assert res_w2["games_count"] == 4
    assert len(res_w2["games"]) == 4

    # Verify seat swapping: even games A is Player 0, odd games B is Player 0
    assert res_w2["games"][0]["a_player"] == 0
    assert res_w2["games"][1]["a_player"] == 1
    assert res_w2["games"][2]["a_player"] == 0
    assert res_w2["games"][3]["a_player"] == 1

    # Verify identical summaries between workers=1 and workers=2
    s2 = res_w2["summary"]
    s1 = res_w1["summary"]

    assert s2["wins_a"] == s1["wins_a"]
    assert s2["wins_b"] == s1["wins_b"]
    assert s2["draws"] == s1["draws"]
    assert s2["win_rate_a"] == s1["win_rate_a"]
    assert s2["mean_plies"] == s1["mean_plies"]

    # Verify game-by-game consistency
    for g1, g2 in zip(res_w1["games"], res_w2["games"]):
        assert g1["winner"] == g2["winner"]
        assert g1["plies"] == g2["plies"]


def test_tournament_output_schema():
    """Verify returned dictionary contains all required keys."""
    res = run_match("greedy", "random", games=2, seed=10, workers=1)
    assert "spec_a" in res
    assert "spec_b" in res
    assert "summary" in res
    assert "games" in res

    s = res["summary"]
    for key in (
        "wins_a",
        "wins_b",
        "draws",
        "win_rate_a",
        "mean_plies",
        "mean_nodes_per_move_a",
        "mean_ms_per_move_a",
        "mean_nodes_per_move_b",
        "mean_ms_per_move_b",
    ):
        assert key in s

