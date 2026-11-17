"""Interactive terminal visualizer to watch a four-player Quoridor match."""
from __future__ import annotations

import argparse
import time

from .agents import make_agent
from .runner import play_game
from .state import GameState
from .tournament import spec_with_seed
from .types import move_to_str


def watch_game(
    table_specs: list[str],
    seed: int = 42,
    delay: float = 0.3,
    max_turns: int = 400,
) -> None:
    """Watch a four-player Quoridor game turn by turn in the terminal."""
    if len(table_specs) != 4:
        raise ValueError("table must have exactly 4 agent specs")

    state = GameState.initial(num_players=4)
    agents = [
        make_agent(spec_with_seed(spec, seed * 10 + idx))
        for idx, spec in enumerate(table_specs)
    ]

    print("=" * 60)
    print("FOUR-PLAYER QUORIDOR TERMINAL PLAY")
    print("=" * 60)
    for i, sp in enumerate(table_specs):
        print(f"  Seat {i}: {sp}")
    print("-" * 60)
    print(state.render())
    print("-" * 60)

    while not state.is_terminal() and state.turn_count < max_turns:
        curr = state.current
        agent = agents[curr]

        t0 = time.perf_counter()
        move = agent.choose_move(state)
        elapsed = time.perf_counter() - t0

        print(f"\nPly {state.turn_count + 1} | Player {curr} ({agent.name}) plays: {move_to_str(move)} [{elapsed*1000:.1f}ms]")
        state = state.apply(move)
        print(state.render())

        if delay > 0:
            time.sleep(delay)

    winner = state.winner()
    print("\n" + "=" * 60)
    if winner is not None:
        print(f"GAME OVER: Player {winner} ({table_specs[winner]}) WINS in {state.turn_count} plies!")
    else:
        print(f"GAME OVER: Reached turn cap ({max_turns} plies). No winner.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch a four-player Quoridor game in terminal")
    parser.add_argument("--table", type=str, default="greedy,paranoid:depth=2,greedy,greedy")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds to pause between moves")
    parser.add_argument("--max-turns", type=int, default=400)
    args = parser.parse_args()

    specs = [s.strip() for s in args.table.split(",") if s.strip()]
    watch_game(table_specs=specs, seed=args.seed, delay=args.delay, max_turns=args.max_turns)


if __name__ == "__main__":
    main()
