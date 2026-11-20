"""Evaluation functions for dynamic Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import pathfinding

if TYPE_CHECKING:
    from .state import GameState

WIN_SCORE = 10_000.0
W_PATH = 1.0
W_WALLS = 0.25
_UNREACHABLE = 99


def evaluate(
    state: GameState,
    player: int,
    mode: str = "mean",
    w_path: float = W_PATH,
    w_walls: float = W_WALLS,
) -> float:
    """Score the position from player's point of view (higher = better)."""
    w = state.winner()
    if w is not None:
        return WIN_SCORE if w == player else -WIN_SCORE

    d_dict = pathfinding.distances(state)
    d_me = d_dict[player]
    if d_me is None:
        d_me = _UNREACHABLE
    walls_me = state.walls(player)

    if mode == "own":
        return -w_path * d_me + w_walls * walls_me

    opponents = [p for p in state.config.players if p != player]

    if mode == "leader":
        leader = min(opponents, key=lambda p: (d_dict[p] if d_dict[p] is not None else _UNREACHABLE))
        d_leader = d_dict[leader]
        if d_leader is None:
            d_leader = _UNREACHABLE
        walls_leader = state.walls(leader)
        return w_path * (d_leader - d_me) + w_walls * (walls_me - walls_leader)

    # mode == "mean" (default)
    opp_dists = [d_dict[p] if d_dict[p] is not None else _UNREACHABLE for p in opponents]
    opp_walls = [state.walls(p) for p in opponents]
    mean_opp_dist = sum(opp_dists) / len(opp_dists)
    mean_opp_walls = sum(opp_walls) / len(opp_walls)

    return w_path * (mean_opp_dist - d_me) + w_walls * (walls_me - mean_opp_walls)
