"""Pruned move generation for search agents."""
from __future__ import annotations

from . import pathfinding, rules
from .state import GameState
from .types import Move, WallMove


def candidate_walls(state: GameState) -> list[WallMove]:
    """Pruned list of promising legal walls for state.current."""
    curr = state.current
    opp = 1 - curr

    if state.walls_left[curr] <= 0:
        return []

    path = pathfinding.shortest_path(state, opp)
    if path is None or len(path) < 2:
        return []

    seen: set[WallMove] = set()
    result: list[WallMove] = []

    # Prune search space: generate wall candidates that intersect opponent's current shortest path
    for i in range(len(path) - 1):
        (r1, c1), (r2, c2) = path[i], path[i + 1]

        if c1 == c2:
            r = min(r1, r2)
            c = c1
            candidates = [WallMove(r, c, "H"), WallMove(r, c - 1, "H")]
        else:
            r = r1
            c = min(c1, c2)
            candidates = [WallMove(r, c, "V"), WallMove(r - 1, c, "V")]

        for w in candidates:
            if w in seen:
                continue
            if not (0 <= w.r <= 7 and 0 <= w.c <= 7):
                continue
            if rules.is_wall_legal(state, w):
                seen.add(w)
                result.append(w)

    return result


def candidate_moves(state: GameState) -> list[Move]:
    """Legal pawn moves followed by candidate walls."""
    pawn_moves: list[Move] = list(rules.legal_pawn_moves(state))
    wall_moves: list[Move] = list(candidate_walls(state))
    return pawn_moves + wall_moves