"""Tournament harness, seating permutations, and benchmark runner for four-player Quoridor."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import itertools
import json
import math
import os
from pathlib import Path
import random
import statistics
import time
from typing import Any, Sequence

from .agents import make_agent
from .runner import play_game
from .state import GameState
from .types import move_to_str


def spec_with_seed(spec: str, seed: int) -> str:
    """Inject or override the seed parameter in an agent specification string."""
    if ":" in spec:
        name, params = spec.split(":", 1)
        pairs = [p.strip() for p in params.split(",") if p.strip()]
        filtered = [p for p in pairs if not p.startswith("seed=")]
        filtered.append(f"seed={seed}")
        return f"{name}:{','.join(filtered)}"
    return f"{spec}:seed={seed}"


def generate_seating_schedule(
    specs: Sequence[str],
    seating_mode: str,
    reps: int,
) -> list[tuple[str, str, str, str]]:
    """Generate the full seating schedule based on mode and repetitions."""
    base_specs = list(specs)
    if len(base_specs) != 4:
        raise ValueError(f"expected 4 agent specs for table, got {len(base_specs)}")

    if seating_mode == "fixed":
        base_schedule = [tuple(base_specs)]
    elif seating_mode == "rotations":
        base_schedule = [
            (base_specs[i], base_specs[(i + 1) % 4], base_specs[(i + 2) % 4], base_specs[(i + 3) % 4])
            for i in range(4)
        ]
    elif seating_mode == "perms":
        # All 24 seat index permutations
        idx_perms = list(itertools.permutations([0, 1, 2, 3]))
        base_schedule = [
            (base_specs[p[0]], base_specs[p[1]], base_specs[p[2]], base_specs[p[3]])
            for p in idx_perms
        ]
    else:
        raise ValueError(f"unknown seating mode: {seating_mode!r}")

    schedule: list[tuple[str, str, str, str]] = []
    for _ in range(reps):
        schedule.extend(base_schedule)

    return schedule


def play_tournament_game_worker(args: tuple[int, tuple[str, str, str, str], int, int, int]) -> dict[str, Any]:
    """Execute a single game within a tournament worker process."""
    game_idx, seat_specs, base_seed, max_turns, walls_per_player = args
    game_seed = base_seed + game_idx

    # Instantiate agents with deterministic game seeds
    agents = [
        make_agent(spec_with_seed(spec, game_seed * 10 + seat))
        for seat, spec in enumerate(seat_specs)
    ]

    res = play_game(
        agents=agents,
        max_turns=max_turns,
        num_players=4,
        walls_per_player=walls_per_player,
    )

    seat_diagnostics: dict[str, Any] = {}
    for seat in range(4):
        p_stats = res.agent_stats[seat]
        times = p_stats["per_move_times"]
        nodes = p_stats["per_move_nodes"]
        seat_diagnostics[str(seat)] = {
            "spec": seat_specs[seat],
            "moves_played": p_stats["moves_played"],
            "total_nodes": p_stats["total_nodes"],
            "total_time_s": p_stats["total_time_s"],
            "median_time_per_move": statistics.median(times) if times else 0.0,
            "mean_nodes_per_move": (p_stats["total_nodes"] / len(nodes)) if nodes else 0.0,
        }

    return {
        "game_idx": game_idx,
        "seed": game_seed,
        "seating": list(seat_specs),
        "winner": res.winner,
        "no_winner": res.no_winner,
        "ranks": {str(k): v for k, v in res.ranks.items()},
        "plies": res.plies,
        "moves": [move_to_str(m) for m in res.moves],
        "seat_stats": seat_diagnostics,
    }


def run_table_tournament(
    table_specs: Sequence[str],
    seating_mode: str = "perms",
    reps: int = 1,
    max_turns: int = 400,
    walls_per_player: int = 5,
    base_seed: int = 0,
    workers: int | None = None,
    out_dir: str | Path | None = None,
    table_name: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Execute a complete tournament over a specified 4-player table."""
    if workers is None:
        workers = min(8, os.cpu_count() or 4)

    schedule = generate_seating_schedule(table_specs, seating_mode, reps)
    total_games = len(schedule)

    out_path: Path | None = None
    if out_dir is not None:
        out_p = Path(out_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        tname = table_name or f"table_{'_'.join(s.split(':')[0] for s in table_specs)}"
        out_path = out_p / f"{tname}.json"

        # Resumable execution
        if out_path.exists() and not force:
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if len(existing.get("games", [])) == total_games:
                    return existing
            except Exception:
                pass

    tasks = [
        (i, schedule[i], base_seed, max_turns, walls_per_player)
        for i in range(total_games)
    ]

    t0 = time.perf_counter()
    if workers <= 1:
        results = [play_tournament_game_worker(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(play_tournament_game_worker, tasks))

    elapsed = time.perf_counter() - t0
    results.sort(key=lambda r: r["game_idx"])

    # Aggregate tournament summary
    unique_specs = sorted(list(set(table_specs)))
    spec_summary: dict[str, Any] = {}
    for spec in unique_specs:
        spec_summary[spec] = {
            "games_played": 0,
            "wins": 0,
            "ranks": [],
            "total_nodes": 0,
            "total_time_s": 0.0,
            "total_moves": 0,
        }

    for g in results:
        w = g["winner"]
        for seat_str, st in g["seat_stats"].items():
            sp = st["spec"]
            seat_int = int(seat_str)
            spec_summary[sp]["games_played"] += 1
            if w == seat_int:
                spec_summary[sp]["wins"] += 1
            spec_summary[sp]["ranks"].append(g["ranks"][seat_str])
            spec_summary[sp]["total_nodes"] += st["total_nodes"]
            spec_summary[sp]["total_time_s"] += st["total_time_s"]
            spec_summary[sp]["total_moves"] += st["moves_played"]

    for sp, data in spec_summary.items():
        n = data["games_played"]
        data["win_rate"] = data["wins"] / n if n > 0 else 0.0
        data["mean_rank"] = sum(data["ranks"]) / n if n > 0 else 0.0
        m = data["total_moves"]
        data["mean_nodes_per_move"] = data["total_nodes"] / m if m > 0 else 0.0
        data["mean_time_per_move"] = data["total_time_s"] / m if m > 0 else 0.0

    payload = {
        "table": list(table_specs),
        "seating_mode": seating_mode,
        "reps": reps,
        "total_games": total_games,
        "base_seed": base_seed,
        "elapsed_s": elapsed,
        "summary": spec_summary,
        "games": results,
    }

    if out_path is not None:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


def run_timing_benchmark(specs: Sequence[str], repeats: int = 3) -> dict[str, Any]:
    """Execute timing benchmark strictly sequentially (1 process) on fixed positions."""
    # Fixed benchmark positions reached by known seeds
    from .moves import candidate_moves
    positions: list[GameState] = []
    base_state = GameState.initial(num_players=4)
    positions.append(base_state)

    # Generate 5 diverse mid-game positions fast
    rng = random.Random(12345)
    for _ in range(5):
        s = base_state
        for _ in range(8):
            avail = candidate_moves(s, target="all")
            if not avail:
                break
            s = s.apply(rng.choice(avail))
        positions.append(s)

    benchmark_results: dict[str, Any] = {}

    for spec in specs:
        times_per_move: list[float] = []
        nodes_per_move: list[int] = []

        agent = make_agent(spec_with_seed(spec, 42))

        for rep in range(repeats):
            for pos in positions:
                t0 = time.perf_counter()
                _ = agent.choose_move(pos)
                elapsed = time.perf_counter() - t0
                stats = agent.last_stats

                times_per_move.append(elapsed)
                nodes_per_move.append(stats.get("nodes", 1))

        med_time = statistics.median(times_per_move) if times_per_move else 0.0
        mean_nodes = sum(nodes_per_move) / len(nodes_per_move) if nodes_per_move else 0.0

        benchmark_results[spec] = {
            "median_time_per_move": med_time,
            "mean_nodes_per_move": mean_nodes,
            "samples": len(times_per_move),
        }

    return benchmark_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Four-player Quoridor tournament harness")
    parser.add_argument("--table", type=str, required=True, help="Comma-separated specs for 4 seats")
    parser.add_argument("--seating", type=str, default="perms", choices=["perms", "rotations", "fixed"])
    parser.add_argument("--reps", type=int, default=1, help="Repetitions of the seating schedule")
    parser.add_argument("--max-turns", type=int, default=400, help="Maximum plies before draw cap")
    parser.add_argument("--walls", type=int, default=5, help="Walls per player")
    parser.add_argument("--seed", type=int, default=42, help="Base seed")
    parser.add_argument("--workers", type=int, default=None, help="Process pool worker count")
    parser.add_argument("--out", type=str, default="results_n", help="Output directory")
    parser.add_argument("--table-name", type=str, default=None, help="Name of the output JSON file")
    parser.add_argument("--force", action="store_true", help="Force redo existing results")
    parser.add_argument("--timing", action="store_true", help="Run sequential timing benchmark")

    args = parser.parse_args()
    specs = [s.strip() for s in args.table.split(",") if s.strip()]

    if args.timing:
        res = run_timing_benchmark(specs)
        print(json.dumps(res, indent=2))
        return

    res = run_table_tournament(
        table_specs=specs,
        seating_mode=args.seating,
        reps=args.reps,
        max_turns=args.max_turns,
        walls_per_player=args.walls,
        base_seed=args.seed,
        workers=args.workers,
        out_dir=args.out,
        table_name=args.table_name,
        force=args.force,
    )
    print(f"Finished tournament: {res['total_games']} games in {res['elapsed_s']:.2f}s")
    for sp, data in res["summary"].items():
        print(f"  {sp}: win_rate={data['win_rate']*100:.1f}% ({data['wins']}/{data['games_played']}), mean_rank={data['mean_rank']:.2f}")


if __name__ == "__main__":
    main()
