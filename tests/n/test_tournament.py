"""Tests for dynamic Quoridor tournament harness."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from quoridor_n.tournament import (
    generate_seating_schedule,
    run_timing_benchmark,
    run_tournament,
    spec_with_seed,
)


def test_generate_seating_schedule_2p():
    """Verify 2P schedule swaps seats every game."""
    sched = generate_seating_schedule(["greedy", "random"], seating_mode="perms", reps=2, num_players=2)
    assert len(sched) == 4
    assert sched[0] == ("greedy", "random")
    assert sched[1] == ("random", "greedy")
    assert sched[2] == ("greedy", "random")
    assert sched[3] == ("random", "greedy")


def test_generate_seating_schedule_4p():
    """Verify 4P schedule supports perms and rotations."""
    rot = generate_seating_schedule(["a", "b", "c", "d"], seating_mode="rotations", reps=1, num_players=4)
    assert len(rot) == 4

    perms = generate_seating_schedule(["a", "b", "c", "d"], seating_mode="perms", reps=1, num_players=4)
    assert len(perms) == 24


def test_spec_with_seed():
    """Verify seed injection and override in agent spec."""
    assert spec_with_seed("greedy", 42) == "greedy:seed=42"
    assert spec_with_seed("paranoid:depth=2", 42) == "paranoid:depth=2,seed=42"
    assert spec_with_seed("paranoid:seed=10,depth=2", 42) == "paranoid:depth=2,seed=42"


def test_run_tournament_2p_and_4p_output_schema():
    """Verify returned tournament dictionary matches required specification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_2p = Path(tmpdir) / "test_2p.json"
        res_2p = run_tournament(
            table_specs=["greedy", "random"],
            seating_mode="perms",
            reps=1,
            board_size=7,
            num_players=2,
            workers=1,
            out_file=out_2p,
            profile="quick",
        )
        assert res_2p["games_planned"] == 2
        assert res_2p["games_played"] == 2
        assert res_2p["profile"] == "quick"
        assert res_2p["board_size"] == 7
        assert res_2p["num_players"] == 2
        assert "greedy" in res_2p["summary"]
        assert "random" in res_2p["summary"]
        assert len(res_2p["games"]) == 2
        assert out_2p.exists()

        out_4p = Path(tmpdir) / "test_4p.json"
        res_4p = run_tournament(
            table_specs=["greedy", "random", "greedy", "random"],
            seating_mode="fixed",
            reps=2,
            board_size=8,
            num_players=4,
            workers=1,
            out_file=out_4p,
            profile="quick",
        )
        assert res_4p["games_planned"] == 2
        assert res_4p["games_played"] == 2
        assert len(res_4p["games"]) == 2
        assert out_4p.exists()


def test_timing_benchmark():
    """Verify sequential timing benchmark measures median time and mean nodes."""
    res = run_timing_benchmark(["greedy", "random"], board_size=7, num_players=2, repeats=1)
    assert "greedy" in res
    assert "random" in res
    assert "median_time_per_move" in res["greedy"]
    assert "mean_nodes_per_move" in res["greedy"]
