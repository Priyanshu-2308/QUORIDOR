"""Experiment runner for dynamic-board Quoridor.

Executes pre-registered experiments E0-E5 and ablations A1-A6.
Outputs raw results to results_n/raw/ with progress logging.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import time
from typing import Any

from .config import GameConfig
from .runner import play_game
from .state import GameState
from .tournament import run_tournament
from .moves import candidate_moves, candidate_walls
from .pathfinding import shortest_path_length
from .agents import make_agent


def run_e0(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E0: Seat Bias ===")
    reps_4p = 25 if profile == "full" else 1 # 25 * 4 = 100 games
    reps_2p = 50 if profile == "full" else 1 # 50 * 2 = 100 games

    # E0 4P Greedy
    print("  E0: 4P Greedy (100 games)...")
    run_tournament(
        table_specs=["greedy", "greedy", "greedy", "greedy"],
        seating_mode="fixed",
        reps=100 if profile == "full" else 4,
        board_size=9,
        num_players=4,
        base_seed=10000,
        workers=workers,
        out_file=out_dir / "e0_seat_bias_4p_greedy.json",
        profile=profile,
        force=force,
    )

    # E0 4P Paranoid
    print("  E0: 4P Paranoid (100 games)...")
    run_tournament(
        table_specs=["paranoid:depth=2", "paranoid:depth=2", "paranoid:depth=2", "paranoid:depth=2"],
        seating_mode="fixed",
        reps=100 if profile == "full" else 4,
        board_size=9,
        num_players=4,
        base_seed=11000,
        workers=workers,
        out_file=out_dir / "e0_seat_bias_4p_paranoid.json",
        profile=profile,
        force=force,
    )

    # E0 2P Greedy
    print("  E0: 2P Greedy (100 games)...")
    run_tournament(
        table_specs=["greedy", "greedy"],
        seating_mode="perms",
        reps=reps_2p,
        board_size=9,
        num_players=2,
        base_seed=12000,
        workers=workers,
        out_file=out_dir / "e0_seat_bias_2p_greedy.json",
        profile=profile,
        force=force,
    )

    # E0 2P Paranoid
    print("  E0: 2P Paranoid (100 games)...")
    run_tournament(
        table_specs=["paranoid:depth=2", "paranoid:depth=2"],
        seating_mode="perms",
        reps=reps_2p,
        board_size=9,
        num_players=2,
        base_seed=13000,
        workers=workers,
        out_file=out_dir / "e0_seat_bias_2p_paranoid.json",
        profile=profile,
        force=force,
    )


def run_e1(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E1: Skill Ladder ===")
    reps_4p = 40 if profile == "full" else 1 # 40 * 4 rotations = 160 games
    reps_2p = 50 if profile == "full" else 1 # 50 * 2 = 100 games

    # 4P Ladder
    for name, spec in [
        ("paranoid", "paranoid:depth=2"),
        ("maxn", "maxn:depth=2"),
        ("mcts", "mcts:iterations=35"),
    ]:
        print(f"  E1 4P: {name} vs 3 Greedy ({reps_4p * 4} games)...")
        run_tournament(
            table_specs=[spec, "greedy", "greedy", "greedy"],
            seating_mode="rotations",
            reps=reps_4p,
            board_size=9,
            num_players=4,
            base_seed=20000 + (len(name) * 100),
            workers=workers,
            out_file=out_dir / f"e1_ladder_4p_{name}.json",
            profile=profile,
            force=force,
        )

    # 2P Ladder
    for name, spec in [
        ("paranoid", "paranoid:depth=2"),
        ("mcts", "mcts:iterations=35"),
    ]:
        print(f"  E1 2P: {name} vs Greedy ({reps_2p * 2} games)...")
        run_tournament(
            table_specs=[spec, "greedy"],
            seating_mode="perms",
            reps=reps_2p,
            board_size=9,
            num_players=2,
            base_seed=25000 + (len(name) * 100),
            workers=workers,
            out_file=out_dir / f"e1_ladder_2p_{name}.json",
            profile=profile,
            force=force,
        )


def run_e2(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E2: Main Round Robin (4P, 9x9, 168 games) ===")
    reps = 7 if profile == "full" else 1 # 7 * 24 perms = 168 games
    run_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=35"],
        seating_mode="perms",
        reps=reps,
        board_size=9,
        num_players=4,
        base_seed=30000,
        workers=workers,
        out_file=out_dir / "e2_main_round_robin.json",
        profile=profile,
        force=force,
    )


def run_e3(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E3: Family Comparison (2 Paranoid vs 2 MCTS, 168 games) ===")
    reps = 7 if profile == "full" else 1 # 7 * 24 perms = 168 games
    run_tournament(
        table_specs=[
            "paranoid:depth=2",
            "paranoid:depth=2",
            "mcts:iterations=35",
            "mcts:iterations=35",
        ],
        seating_mode="perms",
        reps=reps,
        board_size=9,
        num_players=4,
        base_seed=40000,
        workers=workers,
        out_file=out_dir / "e3_family_comparison.json",
        profile=profile,
        force=force,
    )


def run_e3b(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E3b: Two-Player Alpha-Beta vs MCTS (200 games) ===")
    reps = 100 if profile == "full" else 2 # 100 * 2 = 200 games
    run_tournament(
        table_specs=["paranoid:depth=2", "mcts:iterations=35"],
        seating_mode="perms",
        reps=reps,
        board_size=9,
        num_players=2,
        base_seed=45000,
        workers=workers,
        out_file=out_dir / "e3b_two_player_match.json",
        profile=profile,
        force=force,
    )


def run_e4(out_dir: Path) -> None:
    print("\n=== Running E4: Wall Targeting Behavioral Analysis from Logs ===")
    # Reads e2_main_round_robin.json and computes leader delay rate vs placebo
    e2_file = out_dir / "e2_main_round_robin.json"
    if not e2_file.exists():
        print("  Skipping E4: E2 results not found.")
        return

    with open(e2_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    games = data.get("games", [])
    records: list[dict[str, Any]] = []

    for g in games:
        cfg = GameConfig(board_size=g["size"], num_players=g["players"], walls_per_player=g["walls"])
        state = GameState.initial(cfg)
        game_walls = 0
        leader_delayed_count = 0
        leader_only_count = 0
        placebo_delayed_count = 0
        total_placebo_candidates = 0

        for m_str in g["moves"]:
            from .types import move_from_str, WallMove
            move = move_from_str(m_str)
            curr = state.current

            if isinstance(move, WallMove):
                game_walls += 1
                # Find current leader (opponent with smallest distance)
                opponents = [p for p in cfg.players if p != curr]
                dist_before = {p: (shortest_path_length(state, p) or 99) for p in opponents}
                min_d = min(dist_before.values())
                leaders = [p for p in opponents if dist_before[p] == min_d]

                # State after move
                next_state = state.apply(move)
                dist_after = {p: (shortest_path_length(next_state, p) or 99) for p in opponents}

                # Did this wall lengthen leader's path?
                leader_hit = any(dist_after[l] > dist_before[l] for l in leaders)
                if leader_hit:
                    leader_delayed_count += 1
                    # Was leader the ONLY opponent affected?
                    non_leaders = [p for p in opponents if p not in leaders]
                    if all(dist_after[nl] == dist_before[nl] for nl in non_leaders):
                        leader_only_count += 1

                # Placebo baseline: fraction of candidate walls that would hit leader
                c_walls = candidate_walls(state, target="all")
                if c_walls:
                    c_hits = 0
                    for cw in c_walls:
                        st_cw = state.apply(cw)
                        if any((shortest_path_length(st_cw, l) or 99) > dist_before[l] for l in leaders):
                            c_hits += 1
                    placebo_delayed_count += c_hits
                    total_placebo_candidates += len(c_walls)

            state = state.apply(move)

        if game_walls > 0:
            records.append({
                "game_idx": g["game_idx"],
                "total_walls": game_walls,
                "leader_delayed": leader_delayed_count,
                "leader_only": leader_only_count,
                "placebo_hits": placebo_delayed_count,
                "placebo_candidates": total_placebo_candidates,
            })

    out_payload = {
        "games_analyzed": len(records),
        "total_walls": sum(r["total_walls"] for r in records),
        "total_leader_delayed": sum(r["leader_delayed"] for r in records),
        "total_leader_only": sum(r["leader_only"] for r in records),
        "total_placebo_hits": sum(r["placebo_hits"] for r in records),
        "total_placebo_candidates": sum(r["placebo_candidates"] for r in records),
        "game_records": records,
    }

    with open(out_dir / "e4_targeting.json", "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2)

    print(f"  E4 completed: {out_payload['total_walls']} walls analyzed across {len(records)} games.")


def run_e5(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running E5: Board Size Scaling (N in 7..12) ===")
    reps_2p = 50 if profile == "full" else 1 # 100 games per size
    reps_4p = 2 if profile == "full" else 1  # 48 games per size

    e5_2p_results: dict[str, Any] = {}
    e5_4p_results: dict[str, Any] = {}

    for n in range(7, 13):
        print(f"  E5: Size N={n} (2P, {reps_2p * 2} games)...")
        res_2p = run_tournament(
            table_specs=["paranoid:depth=2", "mcts:iterations=35"],
            seating_mode="perms",
            reps=reps_2p,
            board_size=n,
            num_players=2,
            base_seed=50000 + n * 100,
            workers=workers,
            out_file=out_dir / f"e5_size_{n}_2p.json",
            profile=profile,
            force=force,
        )
        e5_2p_results[str(n)] = res_2p

        print(f"  E5: Size N={n} (4P, {reps_4p * 24} games)...")
        res_4p = run_tournament(
            table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=35"],
            seating_mode="perms",
            reps=reps_4p,
            board_size=n,
            num_players=4,
            base_seed=55000 + n * 100,
            workers=workers,
            out_file=out_dir / f"e5_size_{n}_4p.json",
            profile=profile,
            force=force,
        )
        e5_4p_results[str(n)] = res_4p


def run_ablations(out_dir: Path, workers: int, profile: str, force: bool = False) -> None:
    print("\n=== Running Ablations A1-A6 ===")
    reps_paired = 7 if profile == "full" else 1 # 168 games

    # A1: Wall Target
    print("  A1: Wall Target (leader vs all)...")
    run_tournament(
        table_specs=[
            "paranoid:depth=2,wall_target=all",
            "paranoid:depth=2,wall_target=leader",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=reps_paired,
        board_size=9,
        num_players=4,
        base_seed=61000,
        workers=workers,
        out_file=out_dir / "a1_wall_target_paired.json",
        profile=profile,
        force=force,
    )

    # A2: Search Paradigm (Paranoid vs Maxn)
    print("  A2: Search Paradigm (Paranoid vs Maxn)...")
    run_tournament(
        table_specs=[
            "paranoid:depth=2",
            "maxn:depth=2",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=reps_paired,
        board_size=9,
        num_players=4,
        base_seed=62000,
        workers=workers,
        out_file=out_dir / "a2_paradigm_paired.json",
        profile=profile,
        force=force,
    )

    # A3: Enhancements Benchmark (60 positions)
    print("  A3: Position Benchmark (Ordering, TT, Wall Cap)...")
    _run_a3_position_benchmark(out_dir)

    # A4: Evaluation Mode (Leader vs Mean)
    print("  A4: Evaluation Mode (Leader vs Mean)...")
    run_tournament(
        table_specs=[
            "paranoid:depth=2,eval_mode=mean",
            "paranoid:depth=2,eval_mode=leader",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=reps_paired,
        board_size=9,
        num_players=4,
        base_seed=64000,
        workers=workers,
        out_file=out_dir / "a4_eval_mode_paired.json",
        profile=profile,
        force=force,
    )

    # A5: Wall Budget (3 walls vs 10 walls)
    print("  A5: Wall Budget (3 walls vs 10 walls)...")
    run_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=35"],
        seating_mode="perms",
        reps=reps_paired,
        walls_per_player=3,
        board_size=9,
        num_players=4,
        base_seed=65003,
        workers=workers,
        out_file=out_dir / "a5_walls_3.json",
        profile=profile,
        force=force,
    )
    run_tournament(
        table_specs=["greedy", "paranoid:depth=2", "maxn:depth=2", "mcts:iterations=35"],
        seating_mode="perms",
        reps=reps_paired,
        walls_per_player=10,
        board_size=9,
        num_players=4,
        base_seed=65010,
        workers=workers,
        out_file=out_dir / "a5_walls_10.json",
        profile=profile,
        force=force,
    )

    # A6: MCTS Rollout Policy (path_biased vs random)
    print("  A6: MCTS Rollout Policy (path_biased vs random)...")
    run_tournament(
        table_specs=[
            "mcts:iterations=35,rollout_policy=path_biased",
            "mcts:iterations=35,rollout_policy=random",
            "greedy",
            "greedy",
        ],
        seating_mode="perms",
        reps=reps_paired,
        board_size=9,
        num_players=4,
        base_seed=66000,
        workers=workers,
        out_file=out_dir / "a6_mcts_rollout_paired.json",
        profile=profile,
        force=force,
    )


def _run_a3_position_benchmark(out_dir: Path) -> None:
    """Generate 60 positions from seeded games and compare switches."""
    cfg = GameConfig(board_size=9, num_players=4)
    positions: list[GameState] = []

    rng = random.Random(777)
    for g_idx in range(30):
        s = GameState.initial(cfg)
        for ply in range(12):
            moves = candidate_moves(s, target="all")
            if not moves:
                break
            s = s.apply(rng.choice(moves))
            if ply in (4, 8) and len(positions) < 60:
                positions.append(s)

    specs = {
        "baseline": "paranoid:depth=2,use_move_ordering=True,use_tt=True,wall_cap=12",
        "no_ordering": "paranoid:depth=2,use_move_ordering=False,use_tt=True,wall_cap=12",
        "no_tt": "paranoid:depth=2,use_move_ordering=True,use_tt=False,wall_cap=12",
        "wall_cap_4": "paranoid:depth=2,use_move_ordering=True,use_tt=True,wall_cap=4",
        "wall_cap_8": "paranoid:depth=2,use_move_ordering=True,use_tt=True,wall_cap=8",
        "wall_cap_none": "paranoid:depth=2,use_move_ordering=True,use_tt=True,wall_cap=None",
    }

    benchmark_data: dict[str, Any] = {}
    base_moves = []
    base_agent = make_agent(specs["baseline"])
    for pos in positions:
        m = base_agent.choose_move(pos)
        base_moves.append(m)

    for k, spec in specs.items():
        agent = make_agent(spec)
        nodes_list = []
        times_list = []
        agreements = 0

        for idx, pos in enumerate(positions):
            t0 = time.perf_counter()
            chosen = agent.choose_move(pos)
            elapsed = time.perf_counter() - t0
            nodes_list.append(agent.last_stats.get("nodes", 1))
            times_list.append(elapsed)
            if chosen == base_moves[idx]:
                agreements += 1

        benchmark_data[k] = {
            "mean_nodes": sum(nodes_list) / len(nodes_list),
            "median_time_s": sorted(times_list)[len(times_list) // 2],
            "agreement_rate": agreements / len(positions),
            "positions_tested": len(positions),
        }

    with open(out_dir / "a3_position_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quoridor experiment suite runner")
    parser.add_argument("--profile", type=str, default="full", choices=["quick", "full"])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=str, default="results_n/raw")
    parser.add_argument("--step", type=str, default="all", choices=["all", "e0", "e1", "e2", "e3", "e3b", "e4", "e5", "ablations"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out_p = Path(args.out)
    out_p.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    if args.step in ("all", "e0"):
        run_e0(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "e1"):
        run_e1(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "e2"):
        run_e2(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "e3"):
        run_e3(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "e3b"):
        run_e3b(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "e4"):
        run_e4(out_p)
    if args.step in ("all", "e5"):
        run_e5(out_p, args.workers, args.profile, args.force)
    if args.step in ("all", "ablations"):
        run_ablations(out_p, args.workers, args.profile, args.force)

    total_time = time.perf_counter() - t0
    print(f"\n==========================================")
    print(f"All experiments finished in {total_time:.2f}s ({total_time/60:.2f}m)")
    print(f"==========================================")


if __name__ == "__main__":
    main()
