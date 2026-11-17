"""Heuristic static evaluation for four-player and two-player positions."""
from __future__ import annotations

from typing import TYPE_CHECKING
from . import pathfinding

if TYPE_CHECKING:
    from .state import GameState

WIN_SCORE = 1000.0


def evaluate(
    state: GameState,
    player: int,
    mode: str = "mean",
    w_path: float = 1.0,
    w_walls: float = 0.25,
) -> float:
    """Static heuristic evaluation from the perspective of ``player``.
    
    Modes:
        - "mean": w_path * (mean(opp_dist) - own_dist) + w_walls * (own_walls - mean(opp_walls))
        - "leader": w_path * (min(opp_dist) - own_dist) + w_walls * (own_walls - mean(opp_walls))
        - "own": -own_dist (ignores walls and opponents)
    """
    w = state.winner()
    if w == player:
        return WIN_SCORE - state.turn_count
    if w is not None:
        return -(WIN_SCORE - state.turn_count)

    d_p = pathfinding.shortest_path_length(state, player)
    own_dist = 99 if d_p is None else d_p

    if mode == "own":
        return -float(own_dist)

    opponents = [p for p in state.players if p != player]
    opp_dists: list[int] = []
    for opp in opponents:
        d = pathfinding.shortest_path_length(state, opp)
        opp_dists.append(99 if d is None else d)

    opp_walls = [state.walls(opp) for opp in opponents]
    mean_opp_walls = sum(opp_walls) / len(opp_walls)
    own_walls = state.walls(player)

    if mode == "mean":
        mean_opp_dist = sum(opp_dists) / len(opp_dists)
        return w_path * (mean_opp_dist - own_dist) + w_walls * (own_walls - mean_opp_walls)

    if mode == "leader":
        min_opp_dist = min(opp_dists)
        return w_path * (min_opp_dist - own_dist) + w_walls * (own_walls - mean_opp_walls)

    raise ValueError(f"unknown eval mode: {mode!r}")
