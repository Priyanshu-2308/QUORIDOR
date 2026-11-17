"""Pruned move and wall generation for four-player and two-player search agents."""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import pathfinding, rules
from .types import Move, WallMove

if TYPE_CHECKING:
    from .state import GameState


def candidate_walls(state: GameState, target: str = "all") -> list[WallMove]:
    """Generate candidate legal walls targeted at opponents' shortest paths.
    
    Target strategies:
        - "all": Union over all opponents' shortest paths (default baseline).
        - "leader": Opponent with shortest distance to goal (ties broken by turn order).
        - "next": Opponent who moves next in turn order.
        - "none": No pruning; returns all legal wall placements.
    """
    curr = state.current
    if state.walls(curr) <= 0:
        return []

    if target == "none":
        return rules.legal_wall_moves(state)

    curr_idx = state.player_index(curr)
    opponents = [p for p in state.players if p != curr]

    if target == "all":
        target_players = opponents
    elif target == "next":
        next_player = state.players[(curr_idx + 1) % state.num_players]
        target_players = [next_player]
    elif target == "leader":
        def leader_key(p: int) -> tuple[int, int]:
            d = pathfinding.shortest_path_length(state, p)
            dist = 99 if d is None else d
            turn_dist = (state.player_index(p) - curr_idx) % state.num_players
            return (dist, turn_dist)

        target_players = [min(opponents, key=leader_key)]
    else:
        raise ValueError(f"unknown wall_target strategy: {target!r}")

    seen: set[WallMove] = set()
    result: list[WallMove] = []

    for opp in target_players:
        path = pathfinding.shortest_path(state, opp)
        if path is None or len(path) < 2:
            continue

        for i in range(len(path) - 1):
            (r1, c1), (r2, c2) = path[i], path[i + 1]

            if c1 == c2:
                # Vertical step between (r1, c1) and (r2, c1)
                r = min(r1, r2)
                c = c1
                candidates = [WallMove(r, c, "H"), WallMove(r, c - 1, "H")]
            else:
                # Horizontal step between (r1, c1) and (r1, c2)
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


def candidate_moves(state: GameState, target: str = "all") -> list[Move]:
    """Legal pawn moves followed by candidate wall placements."""
    pawn_moves = rules.legal_pawn_moves(state)
    wall_moves = candidate_walls(state, target=target)
    return list(pawn_moves) + list(wall_moves)
