"""Unit tests for four-player tournament harness."""
import json
import pytest
from quoridor_n.tournament import (
    generate_seating_schedule,
    run_table_tournament,
    spec_with_seed,
)


def test_spec_with_seed():
    assert spec_with_seed("greedy", 42) == "greedy:seed=42"
    assert spec_with_seed("paranoid:depth=2", 42) == "paranoid:depth=2,seed=42"
    assert spec_with_seed("mcts:iterations=100,seed=1", 99) == "mcts:iterations=100,seed=99"


def test_seating_schedule_generation():
    specs = ["A", "B", "C", "D"]

    # Fixed
    s_fixed = generate_seating_schedule(specs, "fixed", reps=1)
    assert len(s_fixed) == 1
    assert s_fixed[0] == ("A", "B", "C", "D")

    # Rotations
    s_rot = generate_seating_schedule(specs, "rotations", reps=1)
    assert len(s_rot) == 4
    assert s_rot[0] == ("A", "B", "C", "D")
    assert s_rot[1] == ("B", "C", "D", "A")

    # Permutations (4! = 24)
    s_perms = generate_seating_schedule(specs, "perms", reps=1)
    assert len(s_perms) == 24
    assert len(set(s_perms)) == 24

    # Repetitions
    s_perms_2 = generate_seating_schedule(specs, "perms", reps=2)
    assert len(s_perms_2) == 48


def test_tournament_execution_and_resumability(tmp_path):
    table = ["greedy", "greedy", "greedy", "greedy"]
    res1 = run_table_tournament(
        table_specs=table,
        seating_mode="fixed",
        reps=2,
        max_turns=30,
        out_dir=tmp_path,
        table_name="resumable_test",
    )
    assert res1["total_games"] == 2
    out_file = tmp_path / "resumable_test.json"
    assert out_file.exists()

    # Re-run without force should read existing
    res2 = run_table_tournament(
        table_specs=table,
        seating_mode="fixed",
        reps=2,
        max_turns=30,
        out_dir=tmp_path,
        table_name="resumable_test",
        force=False,
    )
    assert res2["total_games"] == 2
    assert res2["games"] == res1["games"]
