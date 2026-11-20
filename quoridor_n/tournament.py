"""Tournament harness and benchmark runner for dynamic Quoridor."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import os
from pathlib import Path
import random
import statistics
import time
from typing import Any, Sequence

from .agents import make_agent
from .config import GameConfig
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
    num_players: int,
) -> list[tuple[str, ...]]:
    """Generate the seating schedule based on player count, seating mode, and repetitions."""
    base_specs = list(specs)
    if len(base_specs) != num_players:
        raise ValueError(f"expected {num_players} agent specs for table, got {len(base_specs)}")

    if num_players == 2:
        if seating_mode == "fixed":
            base_schedule = [(base_specs[0], base_specs[1])]
        else:
            # perps/swapped seats
            base_schedule = [
                (base_specs[0], base_specs[1]),
                (base_specs[1], base_specs[0]),
            ]
    elif num_players == 4:
        if seating_mode == "fixed":
            base_schedule = [tuple(base_specs)]
        elif seating_mode == "rotations":
            base_schedule = [
                (base_specs[i], base_specs[(i + 1) % 4], base_specs[(i + 2) % 4], base_specs[(i + 3) % 4])
                for i in range(4)
            ]
        elif seating_mode == "perms":
            idx_perms = list(itertools.permutations([0, 1, 2, 3]))
            base_schedule = [
                tuple(base_specs[p[i]] for i in range(4))
                for p in idx_perms
            ]
        else:
            raise ValueError(f"unknown seating mode: {seating_mode!r}")
    else:
        raise ValueError(f"num_players must be 2 or 4, got {num_players}")

    schedule: list[tuple[str, ...]] = []
    for _ in range(reps):
        schedule.extend(base_schedule)

    return schedule


def play_tournament_game_worker(args: tuple[int, tuple[str, ...], int, int, int, int | None, int | None]) -> dict[str, Any]:
    """Execute a single game within a worker process."""
    game_idx, seat_specs, base_seed, board_size, num_players, walls_per_player, max_turns = args
    game_seed = base_seed + game_idx

    cfg = GameConfig(
        board_size=board_size,
        num_players=num_players,
        walls_per_player=walls_per_player,
        max_turns=max_turns,
    )

    # Map seat index to player ID
    agents = {}
    for seat_idx, pid in enumerate(cfg.players):
        spec = seat_specs[seat_idx]
        agents[pid] = make_agent(spec_with_seed(spec, game_seed * 10 + pid))

    res = play_game(agents=agents, config=cfg)

    seat_diagnostics: dict[str, Any] = {}
    for seat_idx, pid in enumerate(cfg.players):
        st = res.agent_stats[pid]
        seat_diagnostics[str(pid)] = {
            "spec": seat_specs[seat_idx],
            "moves_count": st["moves_count"],
            "total_nodes": st["total_nodes"],
            "total_time_s": st["total_time_s"],
            "mean_nodes_per_move": (st["total_nodes"] / max(1, st["moves_count"])),
            "mean_time_per_move": (st["total_time_s"] / max(1, st["moves_count"])),
            "tt_hits": st["tt_hits"],
            "cutoffs": st["cutoffs"],
            "iterations": st["iterations"],
        }

    return {
        "game_idx": game_idx,
        "seed": game_seed,
        "seating": list(seat_specs),
        "size": board_size,
        "players": num_players,
        "walls": cfg.walls_per_player,
        "winner": res.winner,
        "no_winner": res.no_winner,
        "ranks": {str(k): v for k, v in res.ranks.items()},
        "plies": res.plies,
        "pass_count": res.pass_count,
        "moves": res.move_strings,
        "seat_stats": seat_diagnostics,
    }


def run_tournament(
    table_specs: Sequence[str],
    seating_mode: str = "perms",
    reps: int = 1,
    board_size: int = 9,
    num_players: int = 4,
    walls_per_player: int | None = None,
    max_turns: int | None = None,
    base_seed: int = 0,
    workers: int | None = None,
    out_file: str | Path | None = None,
    profile: str = "full",
    force: bool = False,
) -> dict[str, Any]:
    """Execute a complete tournament over a specified table with resumability."""
    if workers is None:
        cores = os.cpu_count() or 4
        workers = max(1, cores - 2)

    schedule = generate_seating_schedule(table_specs, seating_mode, reps, num_players)
    total_games = len(schedule)

    out_path: Path | None = None
    existing_games: list[dict[str, Any]] = []

    if out_file is not None:
        out_path = Path(out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not force:
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if len(existing.get("games", [])) == total_games:
                    return existing
                existing_games = existing.get("games", [])
            except Exception:
                existing_games = []

    start_idx = len(existing_games)
    remaining_schedule = schedule[start_idx:]

    t0 = time.perf_counter()
    results: list[dict[str, Any]] = list(existing_games)

    if remaining_schedule:
        worker_args = [
            (
                start_idx + i,
                remaining_schedule[i],
                base_seed,
                board_size,
                num_players,
                walls_per_player,
                max_turns,
            )
            for i in range(len(remaining_schedule))
        ]

        if workers > 1 and len(worker_args) > 1:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                for game_res in executor.map(play_tournament_game_worker, worker_args):
                    results.append(game_res)
                    if out_path is not None and len(results) % 10 == 0:
                        _save_partial(results, table_specs, seating_mode, reps, total_games, base_seed, board_size, num_players, profile, out_path)
        else:
            for warg in worker_args:
                game_res = play_tournament_game_worker(warg)
                results.append(game_res)
                if out_path is not None and len(results) % 10 == 0:
                    _save_partial(results, table_specs, seating_mode, reps, total_games, base_seed, board_size, num_players, profile, out_path)

    elapsed = time.perf_counter() - t0

    # Aggregate statistics
    spec_summary: dict[str, Any] = {
        sp: {
            "games_played": 0,
            "wins": 0,
            "ranks": [],
            "total_nodes": 0,
            "total_time_s": 0.0,
            "total_moves": 0,
        }
        for sp in table_specs
    }

    cfg = GameConfig(board_size=board_size, num_players=num_players, walls_per_player=walls_per_player, max_turns=max_turns)
    total_passes = 0
    total_no_winners = 0

    for g in results:
        w = g["winner"]
        if g.get("no_winner", False):
            total_no_winners += 1
        total_passes += g.get("pass_count", 0)

        for pid_str, st in g["seat_stats"].items():
            sp = st["spec"]
            pid = int(pid_str)
            spec_summary[sp]["games_played"] += 1
            if w == pid:
                spec_summary[sp]["wins"] += 1
            spec_summary[sp]["ranks"].append(g["ranks"][pid_str])
            spec_summary[sp]["total_nodes"] += st["total_nodes"]
            spec_summary[sp]["total_time_s"] += st["total_time_s"]
            spec_summary[sp]["total_moves"] += st["moves_count"]

    for sp, data in spec_summary.items():
        n = data["games_played"]
        data["win_rate"] = (data["wins"] / n) if n > 0 else 0.0
        data["mean_rank"] = (sum(data["ranks"]) / n) if n > 0 else 0.0
        m = data["total_moves"]
        data["mean_nodes_per_move"] = (data["total_nodes"] / m) if m > 0 else 0.0
        data["mean_time_per_move"] = (data["total_time_s"] / m) if m > 0 else 0.0

    payload = {
        "profile": profile,
        "games_planned": total_games,
        "games_played": len(results),
        "table": list(table_specs),
        "seating_mode": seating_mode,
        "reps": reps,
        "board_size": board_size,
        "num_players": num_players,
        "walls_per_player": cfg.walls_per_player,
        "max_turns": cfg.max_turns,
        "base_seed": base_seed,
        "elapsed_s": elapsed,
        "total_passes": total_passes,
        "total_no_winners": total_no_winners,
        "summary": spec_summary,
        "games": results,
    }

    if out_path is not None:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


def _save_partial(results: list[dict], table_specs: Sequence[str], seating_mode: str, reps: int, total_games: int, base_seed: int, board_size: int, num_players: int, profile: str, out_path: Path):
    payload = {
        "profile": profile,
        "games_planned": total_games,
        "games_played": len(results),
        "table": list(table_specs),
        "seating_mode": seating_mode,
        "reps": reps,
        "board_size": board_size,
        "num_players": num_players,
        "base_seed": base_seed,
        "games": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_timing_benchmark(
    specs: Sequence[str],
    board_size: int = 9,
    num_players: int = 4,
    repeats: int = 3,
) -> dict[str, Any]:
    """Execute timing benchmark strictly sequentially (1 process) on fixed positions."""
    from .moves import candidate_moves
    cfg = GameConfig(board_size=board_size, num_players=num_players)
    base_state = GameState.initial(cfg)
    positions: list[GameState] = [base_state]

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
    parser = argparse.ArgumentParser(description="Dynamic Quoridor tournament harness")
    parser.add_argument("--table", type=str, required=True, help="Comma-separated specs for seats")
    parser.add_argument("--seating", type=str, default="perms", choices=["perms", "rotations", "fixed"])
    parser.add_argument("--reps", type=int, default=1, help="Repetitions of the seating schedule")
    parser.add_argument("--size", type=int, default=9, help="Board size (7..12)")
    parser.add_argument("--players", type=int, default=4, choices=[2, 4], help="Player count (2 or 4)")
    parser.add_argument("--walls", type=int, default=None, help="Walls per player")
    parser.add_argument("--max-turns", type=int, default=None, help="Maximum plies before draw cap")
    parser.add_argument("--seed", type=int, default=42, help="Base seed")
    parser.add_argument("--workers", type=int, default=None, help="Process pool worker count")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    parser.add_argument("--profile", type=str, default="full", choices=["quick", "full"], help="Profile")
    parser.add_argument("--force", action="store_true", help="Force redo existing results")
    parser.add_argument("--timing", action="store_true", help="Run sequential timing benchmark")

    args = parser.parse_args()
    specs = [s.strip() for s in args.table.split(",") if s.strip()]

    if args.timing:
        res = run_timing_benchmark(specs, board_size=args.size, num_players=args.players)
        print(json.dumps(res, indent=2))
        return

    res = run_tournament(
        table_specs=specs,
        seating_mode=args.seating,
        reps=args.reps,
        board_size=args.size,
        num_players=args.players,
        walls_per_player=args.walls,
        max_turns=args.max_turns,
        base_seed=args.seed,
        workers=args.workers,
        out_file=args.out,
        profile=args.profile,
        force=args.force,
    )
    print(f"Finished tournament: {res['games_played']}/{res['games_planned']} games in {res['elapsed_s']:.2f}s")
    for sp, data in res["summary"].items():
        print(f"  {sp}: win_rate={data['win_rate']*100:.1f}% ({data['wins']}/{data['games_played']}), mean_rank={data['mean_rank']:.2f}")


if __name__ == "__main__":
    main()
