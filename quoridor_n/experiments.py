"""Experiment orchestration runner for four-player Quoridor suite."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import time

from .tournament import run_table_tournament


def run_all_experiments(
    results_dir: str = "results_n",
    workers: int | None = None,
    profile: str = "full",
) -> None:
    """Execute pre-registered experiments E0 to E3 and ablations."""
    out_p = Path(results_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    if workers is None:
        workers = min(8, os.cpu_count() or 4)

    print(f"=== Commencing Four-Player Experiment Suite (Profile: {profile}, Workers: {workers}) ===")

    # Determine repetitions based on profile
    if profile == "quick":
        reps_e0_greedy = 2
        reps_e0_paranoid = 1
        reps_e1 = 2
        reps_e2 = 1
        reps_e3 = 1
        reps_a5 = 1
    else:  # "full" pre-registered configuration
        reps_e0_greedy = 12   # 12 reps * 4 rotations = 48 games
        reps_e0_paranoid = 6  # 6 reps * 4 rotations = 24 games
        reps_e1 = 12          # 12 reps * 4 rotations = 48 games
        reps_e2 = 7           # 7 reps * 24 perms = 168 games
        reps_e3 = 7           # 7 reps * 24 perms = 168 games
        reps_a5 = 2           # 2 reps * 24 perms = 48 games

    # --- E0: Seat Bias ---
    print("\n--- Running E0: Seat Bias Baseline ---")
    run_table_tournament(
        table_specs=["greedy", "greedy", "greedy", "greedy"],
        seating_mode="rotations",
        reps=reps_e0_greedy,
        max_turns=300,
        base_seed=10000,
        workers=workers,
        out_dir=out_p,
        table_name="e0_seat_bias_greedy",
    )
    run_table_tournament(
        table_specs=["paranoid:depth=2", "paranoid:depth=2", "paranoid:depth=2", "paranoid:depth=2"],
        seating_mode="rotations",
        reps=reps_e0_paranoid,
        max_turns=300,
        base_seed=11000,
        workers=workers,
        out_dir=out_p,
        table_name="e0_seat_bias_paranoid",
    )

    # --- E1: Skill Ladder ---
    print("\n--- Running E1: Skill Ladder vs 3 Greedy Baselines ---")
    ladder_agents = [
        ("paranoid_d2", "paranoid:depth=2"),
        ("paranoid_d3", "paranoid:depth=3"),
        ("maxn_d2", "maxn:depth=2"),
        ("mcts_iter250", "mcts:iterations=250"),
    ]

    for name, spec in ladder_agents:
        reps = reps_e1 if name != "paranoid_d3" else max(1, reps_e1 // 2)
        print(f"  Testing {name} ({spec}) vs 3 Greedy ({reps * 4} games)...")
        run_table_tournament(
            table_specs=[spec, "greedy", "greedy", "greedy"],
            seating_mode="rotations",
            reps=reps,
            max_turns=300,
            base_seed=20000 + hash(name) % 10000,
            workers=workers,
            out_dir=out_p,
            table_name=f"e1_ladder_{name}",
        )

    # --- E2: Main Round Robin (Omniverse Table) ---
    print("\n--- Running E2: Main Round Robin (Four Families, 168 games) ---")
    run_table_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=250"],
        seating_mode="perms",
        reps=reps_e2,
        max_turns=300,
        base_seed=42000,
        workers=workers,
        out_dir=out_p,
        table_name="e2_main_round_robin",
    )

    # --- E3: Family Comparison (2v2 Table) ---
    print("\n--- Running E3: Family Comparison (Paranoid vs MCTS 2v2, 168 games) ---")
    run_table_tournament(
        table_specs=[
            "paranoid:depth=2",
            "paranoid:depth=2",
            "mcts:iterations=250",
            "mcts:iterations=250",
        ],
        seating_mode="perms",
        reps=reps_e3,
        max_turns=300,
        base_seed=43000,
        workers=workers,
        out_dir=out_p,
        table_name="e3_family_comparison",
    )

    # --- Ablations A1, A4, A5, A6 ---
    print("\n--- Running Key Paired Ablations ---")
    # A1: Wall target (leader vs all)
    print("  A1: Wall target strategy (leader vs all baseline)...")
    run_table_tournament(
        table_specs=[
            "paranoid:depth=2,wall_target='all'",
            "paranoid:depth=2,wall_target='leader'",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=max(1, reps_e2 // 2),
        max_turns=300,
        base_seed=51000,
        workers=workers,
        out_dir=out_p,
        table_name="a1_wall_target_paired",
    )

    # A4: Evaluation function (leader vs mean)
    print("  A4: Evaluation function (leader vs mean baseline)...")
    run_table_tournament(
        table_specs=[
            "paranoid:depth=2,eval_mode='mean'",
            "paranoid:depth=2,eval_mode='leader'",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=max(1, reps_e2 // 2),
        max_turns=300,
        base_seed=54000,
        workers=workers,
        out_dir=out_p,
        table_name="a4_eval_mode_paired",
    )

    # A5: Wall inventory (3 walls vs 10 walls)
    print("  A5: Wall inventory variations (3 walls vs 10 walls)...")
    run_table_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=250"],
        seating_mode="perms",
        reps=reps_a5,
        max_turns=300,
        walls_per_player=3,
        base_seed=55003,
        workers=workers,
        out_dir=out_p,
        table_name="a5_walls_3",
    )
    run_table_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=250"],
        seating_mode="perms",
        reps=reps_a5,
        max_turns=300,
        walls_per_player=10,
        base_seed=55010,
        workers=workers,
        out_dir=out_p,
        table_name="a5_walls_10",
    )

    # A6: MCTS Rollout policy (path_biased vs random)
    print("  A6: MCTS rollout policy (path-biased vs pure random)...")
    run_table_tournament(
        table_specs=[
            "mcts:iterations=250,rollout_policy='path_biased'",
            "mcts:iterations=250,rollout_policy='random'",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=max(1, reps_e2 // 2),
        max_turns=300,
        base_seed=56000,
        workers=workers,
        out_dir=out_p,
        table_name="a6_mcts_rollout_paired",
    )

    print("\n=== Experiment Suite Completed Successfully! Results stored in", results_dir, "===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run four-player Quoridor experiment suite")
    parser.add_argument("--profile", type=str, default="full", choices=["quick", "full"])
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--out", type=str, default="results_n")
    args = parser.parse_args()

    run_all_experiments(results_dir=args.out, workers=args.workers, profile=args.profile)
