"""Game execution runner for four-player and two-player matches."""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Mapping, Sequence

from .pathfinding import shortest_path_length
from .rules import is_legal
from .state import GameState
from .types import Move


@dataclass
class GameResult:
    """Outcome and diagnostics of a finished match."""
    winner: int | None
    ranks: dict[int, float]
    plies: int
    moves: list[Move]
    no_winner: bool
    agent_stats: dict[int, dict[str, Any]]
    final_state: GameState


def compute_ranks(state: GameState, winner: int | None) -> dict[int, float]:
    """Rank players: winner is rank 1; others ranked by remaining path distance.
    
    Ties share the average of the ranks covered.
    """
    ranks: dict[int, float] = {}

    if winner is not None:
        ranks[winner] = 1.0
        remaining = [p for p in state.players if p != winner]
        dist_clean = {
            p: 99 if shortest_path_length(state, p) is None else shortest_path_length(state, p)  # type: ignore
            for p in remaining
        }
        sorted_players = sorted(remaining, key=lambda p: dist_clean[p])

        start_rank = 2
        i = 0
        while i < len(sorted_players):
            j = i
            while j < len(sorted_players) and dist_clean[sorted_players[j]] == dist_clean[sorted_players[i]]:
                j += 1
            avg_rank = sum(range(start_rank + i, start_rank + j)) / (j - i)
            for k in range(i, j):
                ranks[sorted_players[k]] = avg_rank
            i = j
    else:
        dist_clean = {
            p: 99 if shortest_path_length(state, p) is None else shortest_path_length(state, p)  # type: ignore
            for p in state.players
        }
        sorted_players = sorted(state.players, key=lambda p: dist_clean[p])

        start_rank = 1
        i = 0
        while i < len(sorted_players):
            j = i
            while j < len(sorted_players) and dist_clean[sorted_players[j]] == dist_clean[sorted_players[i]]:
                j += 1
            avg_rank = sum(range(start_rank + i, start_rank + j)) / (j - i)
            for k in range(i, j):
                ranks[sorted_players[k]] = avg_rank
            i = j

    return ranks


def play_game(
    agents: Mapping[int, Any] | Sequence[Any],
    max_turns: int = 400,
    num_players: int = 4,
    walls_per_player: int | None = None,
    initial_state: GameState | None = None,
) -> GameResult:
    """Execute a complete Quoridor game until victory or turn cap."""
    if initial_state is not None:
        state = initial_state
    else:
        state = GameState.initial(num_players=num_players, walls_per_player=walls_per_player)

    # Resolve agent mapping by player ID
    if isinstance(agents, Mapping):
        agent_map = dict(agents)
    else:
        agent_map = {p: agents[i] for i, p in enumerate(state.players)}

    moves: list[Move] = []
    agent_stats: dict[int, dict[str, Any]] = {
        p: {
            "moves_played": 0,
            "total_nodes": 0,
            "total_time_s": 0.0,
            "per_move_times": [],
            "per_move_nodes": [],
        }
        for p in state.players
    }

    while not state.is_terminal() and state.turn_count < max_turns:
        curr = state.current
        agent = agent_map[curr]

        t0 = time.perf_counter()
        move = agent.choose_move(state)
        elapsed = time.perf_counter() - t0

        if not is_legal(state, move):
            raise RuntimeError(f"agent for player {curr} chose illegal move {move!r} in position:\n{state.render()}")

        # Record agent statistics
        stats = getattr(agent, "last_stats", {})
        nodes = stats.get("nodes", 1)

        p_stats = agent_stats[curr]
        p_stats["moves_played"] += 1
        p_stats["total_nodes"] += nodes
        p_stats["total_time_s"] += elapsed
        p_stats["per_move_times"].append(elapsed)
        p_stats["per_move_nodes"].append(nodes)

        moves.append(move)
        state = state.apply(move)

    winner = state.winner()
    no_winner = winner is None
    ranks = compute_ranks(state, winner)

    return GameResult(
        winner=winner,
        ranks=ranks,
        plies=state.turn_count,
        moves=moves,
        no_winner=no_winner,
        agent_stats=agent_stats,
        final_state=state,
    )
