"""Static evaluation."""
from __future__ import annotations

from .pathfinding import distances
from .state import GameState

WIN_SCORE = 10_000.0
W_PATH = 1.0
W_WALLS = 0.25

_UNREACHABLE = 99


def evaluate(state: GameState, player: int) -> float:
    """Score the position from ``player``'s point of view (higher = better)."""
    w = state.winner()
    if w is not None:
        return WIN_SCORE if w == player else -WIN_SCORE

    opp = 1 - player
    d0, d1 = distances(state)
    d = [d0, d1]
    d_me = d[player] if d[player] is not None else _UNREACHABLE
    d_opp = d[opp] if d[opp] is not None else _UNREACHABLE

    walls_me = state.walls_left[player]
    walls_opp = state.walls_left[opp]

    return W_PATH * (d_opp - d_me) + W_WALLS * (walls_me - walls_opp)