"""Tournament CLI and experiment harness (owner: Priyanshu)."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import math
import os
from pathlib import Path
import time
from typing import Any

from .agents import make_agent
from .agents.alphabeta_agent import AlphaBetaAgent
from .agents.greedy_agent import GreedyAgent
from .agents.random_agent import RandomAgent
from .runner import play_game
from .state import GameState


def _spec_with_seed(spec: str, seed: int) -> str:
    """Inject or override the seed parameter in an agent spec string."""
    if ":" in spec:
        name, params = spec.split(":", 1)
        pairs = [p.strip() for p in params.split(",") if p.strip()]
        filtered = [p for p in pairs if not p.startswith("seed=")]
        filtered.append(f"seed={seed}")
        return f"{name}:{','.join(filtered)}"
    return f"{spec}:seed={seed}"


def _play_single_game_worker(args: tuple[int, str, str, int, int]) -> dict[str, Any]:
    """Top-level worker function executing one tournament game."""
    game_idx, spec_a, spec_b, base_seed, max_turns = args
    seed = base_seed + game_idx
    spec_a_seeded = _spec_with_seed(spec_a, seed)
    spec_b_seeded = _spec_with_seed(spec_b, seed)
    a_is_p0 = (game_idx % 2 == 0)

    agent_p0 = make_agent(spec_a_seeded if a_is_p0 else spec_b_seeded)
    agent_p1 = make_agent(spec_b_seeded if a_is_p0 else spec_a_seeded)

    result = play_game(agent_p0, agent_p1, max_turns=max_turns)

    if result.winner is None:
        winner_label = "draw"
    elif (result.winner == 0 and a_is_p0) or (result.winner == 1 and not a_is_p0):
        winner_label = "A"
    else:
        winner_label = "B"

    stats_a = result.agent_stats[0 if a_is_p0 else 1]
    stats_b = result.agent_stats[1 if a_is_p0 else 0]

    return {
        "game_idx": game_idx,
        "a_player": 0 if a_is_p0 else 1,
        "winner": winner_label,
        "plies": result.turns,
        "stats_a": stats_a,
        "stats_b": stats_b,
    }


def run_match(
    spec_a: str,
    spec_b: str,
    games: int = 20,
    max_turns: int = 200,
    seed: int = 0,
    workers: int | None = None,
) -> dict[str, Any]:
    """Run a match between two agent specs with alternating seats."""
    if workers is None:
        workers = min(8, os.cpu_count() or 4)

    tasks = [(i, spec_a, spec_b, seed, max_turns) for i in range(games)]

    if workers <= 1:
        game_results = [_play_single_game_worker(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            game_results = list(executor.map(_play_single_game_worker, tasks))

    game_results.sort(key=lambda r: r["game_idx"])

    wins_a = sum(1 for g in game_results if g["winner"] == "A")
    wins_b = sum(1 for g in game_results if g["winner"] == "B")
    draws = sum(1 for g in game_results if g["winner"] == "draw")
    win_rate_a = wins_a / games if games > 0 else 0.0
    mean_plies = sum(g["plies"] for g in game_results) / games if games > 0 else 0.0

    total_moves_a = sum(g["stats_a"]["moves"] for g in game_results)
    total_nodes_a = sum(g["stats_a"]["total_nodes"] for g in game_results)
    total_time_a = sum(g["stats_a"]["total_time_s"] for g in game_results)

    total_moves_b = sum(g["stats_b"]["moves"] for g in game_results)
    total_nodes_b = sum(g["stats_b"]["total_nodes"] for g in game_results)
    total_time_b = sum(g["stats_b"]["total_time_s"] for g in game_results)

    nodes_per_move_a = total_nodes_a / total_moves_a if total_moves_a else 0.0
    ms_per_move_a = (total_time_a * 1000.0) / total_moves_a if total_moves_a else 0.0

    nodes_per_move_b = total_nodes_b / total_moves_b if total_moves_b else 0.0
    ms_per_move_b = (total_time_b * 1000.0) / total_moves_b if total_moves_b else 0.0

    summary = {
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "win_rate_a": win_rate_a,
        "mean_plies": mean_plies,
        "mean_nodes_per_move_a": nodes_per_move_a,
        "mean_ms_per_move_a": ms_per_move_a,
        "mean_nodes_per_move_b": nodes_per_move_b,
        "mean_ms_per_move_b": ms_per_move_b,
    }

    return {
        "spec_a": spec_a,
        "spec_b": spec_b,
        "games_count": games,
        "seed": seed,
        "summary": summary,
        "games": game_results,
    }


def print_match_table(match_data: dict[str, Any]) -> None:
    """Print a clean one-screen summary table of the match to stdout."""
    s = match_data["summary"]
    a = match_data["spec_a"]
    b = match_data["spec_b"]
    total = match_data["games_count"]

    header = f"{'TOURNAMENT MATCH RESULTS':^70}"
    div = "=" * 70
    subdiv = "-" * 70

    print(f"\n{div}\n{header}\n{div}")
    print(f"Agent A: {a}")
    print(f"Agent B: {b}")
    print(f"Games: {total} (swapping seats every game, base seed: {match_data.get('seed', 0)})")
    print(subdiv)
    print(f"{'Outcome':<20} | {'Count':<10} | {'Rate':<15}")
    print(subdiv)
    print(f"{'Wins A':<20} | {s['wins_a']:<10} | {s['win_rate_a'] * 100:>6.1f}%")
    print(f"{'Wins B':<20} | {s['wins_b']:<10} | {(s['wins_b'] / total) * 100:>6.1f}%")
    print(f"{'Draws':<20} | {s['draws']:<10} | {(s['draws'] / total) * 100:>6.1f}%")
    print(subdiv)
    print(f"Mean plies per game: {s['mean_plies']:.1f}")
    print(f"Agent A performance: {s['mean_nodes_per_move_a']:.1f} nodes/move, {s['mean_ms_per_move_a']:.1f} ms/move")
    print(f"Agent B performance: {s['mean_nodes_per_move_b']:.1f} nodes/move, {s['mean_ms_per_move_b']:.1f} ms/move")
    print(f"{div}\n")


SUITE_PAIRS = [
    ("greedy", "random", "greedy_vs_random.json", "Greedy vs Random"),
    ("alphabeta:depth=2", "greedy", "ab2_vs_greedy.json", "AlphaBeta(d=2) vs Greedy"),
    ("alphabeta:depth=3", "greedy", "ab3_vs_greedy.json", "AlphaBeta(d=3) vs Greedy"),
    ("mcts:iterations=500", "greedy", "mcts500_vs_greedy.json", "MCTS(500) vs Greedy"),
    ("mcts:iterations=1000", "greedy", "mcts1000_vs_greedy.json", "MCTS(1000) vs Greedy"),
    ("alphabeta:depth=3", "mcts:iterations=1000", "ab3_vs_mcts1000.json", "AlphaBeta(d=3) vs MCTS(1000)"),
    ("alphabeta:depth=2", "alphabeta:depth=3", "ab2_vs_ab3.json", "AlphaBeta(d=2) vs AlphaBeta(d=3)"),
]


def run_suite(
    games_per_pair: int = 20,
    max_turns: int = 200,
    seed: int = 0,
    workers: int | None = None,
    force: bool = False,
    results_dir: str = "results",
) -> None:
    """Run the complete standard evaluation matrix and write results."""
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []

    for spec_a, spec_b, filename, label in SUITE_PAIRS:
        filepath = out_dir / filename
        if filepath.exists() and not force:
            print(f"[SUITE] Skipping {label} (already exists: {filename})")
            with open(filepath, "r", encoding="utf-8") as f:
                match_data = json.load(f)
        else:
            print(f"\n[SUITE] Running {label}: {spec_a} vs {spec_b} ({games_per_pair} games)...")
            match_data = run_match(
                spec_a=spec_a,
                spec_b=spec_b,
                games=games_per_pair,
                max_turns=max_turns,
                seed=seed,
                workers=workers,
            )
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(match_data, f, indent=2)
            print_match_table(match_data)

        s = match_data["summary"]
        summary_rows.append({
            "pair": label,
            "agent_a": spec_a,
            "agent_b": spec_b,
            "games": match_data["games_count"],
            "wins_a": s["wins_a"],
            "wins_b": s["wins_b"],
            "draws": s["draws"],
            "win_rate_a": round(s["win_rate_a"], 4),
            "mean_plies": round(s["mean_plies"], 2),
            "nodes_per_move_a": round(s["mean_nodes_per_move_a"], 1),
            "ms_per_move_a": round(s["mean_ms_per_move_a"], 1),
            "nodes_per_move_b": round(s["mean_nodes_per_move_b"], 1),
            "ms_per_move_b": round(s["mean_ms_per_move_b"], 1),
        })

    csv_path = out_dir / "summary.csv"
    fieldnames = [
        "pair", "agent_a", "agent_b", "games", "wins_a", "wins_b", "draws",
        "win_rate_a", "mean_plies", "nodes_per_move_a", "ms_per_move_a",
        "nodes_per_move_b", "ms_per_move_b",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\n[SUITE] Wrote tournament summary to {csv_path}")


def _generate_ablation_positions() -> list[GameState]:
    """Generate 15 fixed non-terminal positions by playing seeded greedy vs random games."""
    positions: list[GameState] = []
    seed = 0
    while len(positions) < 15:
        state = GameState.initial()
        g0 = GreedyAgent(seed=seed, wall_prob=0.3)
        r1 = RandomAgent(seed=seed, wall_prob=0.3)
        agents = [g0, r1]

        for ply in range(1, 50):
            if state.is_terminal():
                break
            move = agents[state.current].choose_move(state)
            state = state.apply(move)
            if ply in (4, 8, 12, 16) and not state.is_terminal():
                positions.append(state)
                if len(positions) == 15:
                    break
        seed += 1
    return positions


def run_ablation(
    force: bool = False,
    results_dir: str = "results",
) -> None:
    """Run position-based ablation study for AlphaBeta search configurations."""
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ablation.csv"

    if csv_path.exists() and not force:
        print(f"[ABLATION] Skipping (already exists: {csv_path})")
        return

    positions = _generate_ablation_positions()
    print(f"[ABLATION] Generated {len(positions)} test positions for evaluation.")

    configs = [
        # (config_label, depth, use_wall_pruning, use_move_ordering, use_tt)
        ("all_on", 3, True, True, True),
        ("no_tt", 3, True, True, False),
        ("no_ordering", 3, True, False, True),
        ("no_ordering_no_tt", 3, True, False, False),
        ("no_pruning", 3, False, False, False),
        ("all_on", 4, True, True, True),
        ("no_tt", 4, True, True, False),
        ("no_ordering", 4, True, False, True),
        ("no_ordering_no_tt", 4, True, False, False),
    ]

    all_on_moves: dict[int, list[Any]] = {3: [], 4: []}
    for pos in positions:
        ab3 = AlphaBetaAgent(depth=3, use_wall_pruning=True, use_move_ordering=True, use_tt=True, seed=0)
        all_on_moves[3].append(ab3.choose_move(pos))
        ab4 = AlphaBetaAgent(depth=4, use_wall_pruning=True, use_move_ordering=True, use_tt=True, seed=0)
        all_on_moves[4].append(ab4.choose_move(pos))

    rows = []
    print("\nRunning ablation configurations across 15 positions:")
    for label, depth, wall_pruning, ordering, tt in configs:
        print(f"  Testing {label} (depth={depth})...", end="", flush=True)
        nodes_list = []
        ms_list = []
        tt_hits_list = []
        cutoffs_list = []
        matches = 0

        for i, pos in enumerate(positions):
            agent = AlphaBetaAgent(
                depth=depth,
                use_wall_pruning=wall_pruning,
                use_move_ordering=ordering,
                use_tt=tt,
                seed=0,
            )
            move = agent.choose_move(pos)
            stats = agent.last_stats
            nodes_list.append(stats.get("nodes", 0))
            ms_list.append(stats.get("time_s", 0.0) * 1000.0)
            tt_hits_list.append(stats.get("tt_hits", 0))
            cutoffs_list.append(stats.get("cutoffs", 0))

            if move == all_on_moves[depth][i]:
                matches += 1

        mean_nodes = sum(nodes_list) / len(nodes_list)
        mean_ms = sum(ms_list) / len(ms_list)
        mean_tt_hits = sum(tt_hits_list) / len(tt_hits_list)
        mean_cutoffs = sum(cutoffs_list) / len(cutoffs_list)
        match_rate = matches / len(positions)

        print(f" done: {mean_nodes:.1f} nodes, {mean_ms:.1f} ms, matches {match_rate * 100:.0f}%")

        rows.append({
            "config": label,
            "depth": depth,
            "mean_nodes": round(mean_nodes, 1),
            "mean_ms": round(mean_ms, 1),
            "mean_tt_hits": round(mean_tt_hits, 1),
            "mean_cutoffs": round(mean_cutoffs, 1),
            "move_match_rate": round(match_rate, 3),
        })

    fieldnames = [
        "config", "depth", "mean_nodes", "mean_ms", "mean_tt_hits", "mean_cutoffs", "move_match_rate",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ABLATION] Wrote ablation results to {csv_path}")


def generate_charts(results_dir: str = "results") -> None:
    """Generate matplotlib charts for tournament suite and ablation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = out_dir / "summary.csv"
    if summary_csv.exists():
        pairs = []
        win_rates = []
        with open(summary_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pairs.append(row["pair"])
                win_rates.append(float(row["win_rate_a"]) * 100.0)

        plt.figure(figsize=(10, 5))
        bars = plt.barh(pairs, win_rates, color="#2441D6", edgecolor="#121212")
        plt.xlabel("Agent A Win Rate (%)", fontsize=11, fontweight="bold")
        plt.title("Tournament Suite: Agent A Win Rate by Matchup", fontsize=13, fontweight="bold")
        plt.xlim(0, 100)
        plt.gca().invert_yaxis()
        plt.axvline(50, color="#E8452C", linestyle="--", linewidth=1.5, label="50% baseline")
        for bar in bars:
            w = bar.get_width()
            plt.text(w + 1.5, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%", va="center", fontsize=9)
        plt.legend(loc="lower right")
        plt.tight_layout()
        chart1_path = out_dir / "win_rates.png"
        plt.savefig(chart1_path, dpi=200)
        plt.close()
        print(f"[CHARTS] Saved {chart1_path}")

    ablation_csv = out_dir / "ablation.csv"
    if ablation_csv.exists():
        configs_d3, nodes_d3, ms_d3 = [], [], []
        configs_d4, nodes_d4, ms_d4 = [], [], []
        with open(ablation_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = int(row["depth"])
                cfg = row["config"]
                n = float(row["mean_nodes"])
                t = float(row["mean_ms"])
                if d == 3:
                    configs_d3.append(cfg)
                    nodes_d3.append(n)
                    ms_d3.append(t)
                else:
                    configs_d4.append(cfg)
                    nodes_d4.append(n)
                    ms_d4.append(t)

        plt.figure(figsize=(10, 5))
        plt.bar(configs_d3, nodes_d3, color="#D9A441", edgecolor="#121212")
        plt.yscale("log")
        plt.ylabel("Mean Nodes Searched (Log Scale)", fontsize=11, fontweight="bold")
        plt.title("AlphaBeta Search Ablation: Nodes Visited per Move (Depth 3, Log Scale)", fontsize=13, fontweight="bold")
        plt.grid(axis="y", linestyle="--", alpha=0.6)
        for i, v in enumerate(nodes_d3):
            plt.text(i, v * 1.15, f"{int(v)}", ha="center", fontsize=9, fontweight="bold")
        plt.tight_layout()
        chart2_path = out_dir / "ablation_nodes.png"
        plt.savefig(chart2_path, dpi=200)
        plt.close()
        print(f"[CHARTS] Saved {chart2_path}")

        plt.figure(figsize=(10, 5))
        x_indices = range(len(configs_d3))
        plt.bar(x_indices, ms_d3, color="#2441D6", edgecolor="#121212", width=0.5)
        plt.xticks(x_indices, configs_d3)
        plt.ylabel("Mean Execution Time (ms)", fontsize=11, fontweight="bold")
        plt.title("AlphaBeta Search Ablation: Execution Time per Move (Depth 3)", fontsize=13, fontweight="bold")
        plt.grid(axis="y", linestyle="--", alpha=0.6)
        for i, v in enumerate(ms_d3):
            plt.text(i, v + 2.0, f"{v:.1f}ms", ha="center", fontsize=9, fontweight="bold")
        plt.tight_layout()
        chart3_path = out_dir / "ablation_ms.png"
        plt.savefig(chart3_path, dpi=200)
        plt.close()
        print(f"[CHARTS] Saved {chart3_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quoridor Tournament and Experiment Harness")
    parser.add_argument("--a", type=str, default="greedy", help="Agent A spec string")
    parser.add_argument("--b", type=str, default="random", help="Agent B spec string")
    parser.add_argument("--games", type=int, default=20, help="Number of games to play")
    parser.add_argument("--max-turns", type=int, default=200, help="Maximum plies before draw")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed")
    parser.add_argument("--workers", type=int, default=None, help="Worker count for multiprocessing")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path for match")
    parser.add_argument("--suite", action="store_true", help="Run standard tournament suite")
    parser.add_argument("--ablation", action="store_true", help="Run AlphaBeta ablation study")
    parser.add_argument("--charts", action="store_true", help="Generate summary charts from results")
    parser.add_argument("--force", action="store_true", help="Force recomputation of existing results")

    args = parser.parse_args()

    if args.suite:
        run_suite(
            games_per_pair=args.games,
            max_turns=args.max_turns,
            seed=args.seed,
            workers=args.workers,
            force=args.force,
        )
        generate_charts()
        return

    if args.ablation:
        run_ablation(force=args.force)
        generate_charts()
        return

    if args.charts:
        generate_charts()
        return

    print(f"\nRunning single match: {args.a} vs {args.b} ({args.games} games)...")
    match_data = run_match(
        spec_a=args.a,
        spec_b=args.b,
        games=args.games,
        max_turns=args.max_turns,
        seed=args.seed,
        workers=args.workers,
    )
    print_match_table(match_data)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(match_data, f, indent=2)
        print(f"Results written to {args.out}")


if __name__ == "__main__":
    main()
