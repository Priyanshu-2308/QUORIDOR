"""Game runner."""
from __future__ import annotations

from dataclasses import dataclass

from . import rules
from .agents.base import Agent
from .state import GameState
from .types import Move


@dataclass
class GameResult:
    """Outcome of one game."""
    winner: int | None            # 0, 1, or None for a draw (max_turns reached)
    turns: int                    # plies played
    moves: list[Move]
    agent_stats: list[dict]       # per seat: {"name", "moves", "total_nodes", "total_time_s"}


def play_game(
    agent0: Agent,
    agent1: Agent,
    max_turns: int = 200,
    initial_state: GameState | None = None,
    on_move=None,
) -> GameResult:
    """Play a full game; agent0 is Player 0 (moves first).

    ``on_move(state_before, move, stats, player)`` is called after every ply if provided.
    Raises ``ValueError`` if an agent returns an illegal move.
    """
    agents = [agent0, agent1]
    state = initial_state if initial_state is not None else GameState.initial()

    move_log: list[Move] = []
    seat_moves = [0, 0]
    seat_nodes = [0, 0]
    seat_time = [0.0, 0.0]

    while not state.is_terminal() and state.turn_count < max_turns:
        player = state.current
        agent = agents[player]

        move = agent.choose_move(state)

        if not rules.is_legal(state, move):
            raise ValueError(
                f"Agent {agent.name!r} (player {player}) returned illegal move: {move!r}"
            )

        state_before = state
        state = state.apply(move)
        move_log.append(move)

        stats = agent.last_stats
        seat_moves[player] += 1
        seat_nodes[player] += stats.get("nodes") or 0
        seat_time[player] += stats.get("time_s") or 0.0

        if on_move is not None:
            on_move(state_before, move, stats, player)

    winner = state.winner()

    agent_stats = [
        {
            "name": agents[i].name,
            "moves": seat_moves[i],
            "total_nodes": seat_nodes[i],
            "total_time_s": seat_time[i],
        }
        for i in range(2)
    ]

    return GameResult(
        winner=winner,
        turns=state.turn_count,
        moves=move_log,
        agent_stats=agent_stats,
    )