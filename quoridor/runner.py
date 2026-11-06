"""Game runner (owner: Siddhesh)."""
from __future__ import annotations

from dataclasses import dataclass

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


def play_game(agent0: Agent, agent1: Agent, max_turns: int = 200,
              initial_state: GameState | None = None, on_move=None) -> GameResult:
    """Play a game; agent0 is Player 0 (moves first).

    ``on_move(state_before, move, stats, player)`` is called after every ply if given.
    """
    raise NotImplementedError("owner: Siddhesh")
