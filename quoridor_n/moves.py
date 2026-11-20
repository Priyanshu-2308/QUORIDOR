"""Candidate move generation and wall pruning for dynamic Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import pathfinding, rules
from .types import Cell, Move, PawnMove, WallMove, PassMove

if TYPE_CHECKING:
    from .state import GameState


def select_target_opponents(state: GameState, target: str) -> list[int]:
    """Select target opponent IDs according to target strategy."""
    curr = state.current
    opponents = [p for p in state.config.players if p != curr]
    if not opponents:
        return []

    if target == "none":
        return []

    if target == "all":
        return opponents

    if target == "leader":
        curr_idx = state.player_index(curr)
        # Leader is opponent with smallest shortest path distance, tie-broken by clockwise turn proximity
        leader = min(
            opponents,
            key=lambda p: (
                pathfinding.shortest_path_length(state, p) or 999,
                (state.player_index(p) - curr_idx) % state.config.num_players,
            ),
        )
        return [leader]

    if target == "next":
        curr_idx = state.player_index(curr)
        next_opp = state.config.players[(curr_idx + 1) % state.config.num_players]
        return [next_opp]

    raise ValueError(f"unknown wall target strategy: {target!r}")


def candidate_walls(state: GameState, target: str = "all") -> list[WallMove]:
    """Pruned list of promising legal walls that impede target opponent paths."""
    curr = state.current
    if state.walls(curr) <= 0:
        return []

    targets = select_target_opponents(state, target)
    if not targets:
        return []

    bs = state.config.board_size
    known_paths: dict[int, list[Cell]] = {}
    for p in state.config.players:
        sp = pathfinding.shortest_path(state, p)
        if sp is not None:
            known_paths[p] = sp

    seen: set[WallMove] = set()
    result: list[WallMove] = []

    for opp in targets:
        path = known_paths.get(opp)
        if path is None or len(path) < 2:
            continue

        for i in range(len(path) - 1):
            (r1, c1), (r2, c2) = path[i], path[i + 1]

            if c1 == c2:
                # Vertical step between (r1, c1) and (r2, c2) -> horizontal walls
                r = min(r1, r2)
                c = c1
                candidates = [WallMove(r, c, "H"), WallMove(r, c - 1, "H")]
            else:
                # Horizontal step between (r1, c1) and (r2, c2) -> vertical walls
                r = r1
                c = min(c1, c2)
                candidates = [WallMove(r, c, "V"), WallMove(r - 1, c, "V")]

            for w in candidates:
                if w in seen:
                    continue
                if not (0 <= w.r <= bs - 2 and 0 <= w.c <= bs - 2):
                    continue
                if rules.is_wall_legal(state, w, known_paths=known_paths):
                    seen.add(w)
                    result.append(w)

    return result


def candidate_moves(state: GameState, target: str = "all") -> list[Move]:
    """Legal pawn moves followed by pruned candidate walls."""
    pawn_moves: list[Move] = list(rules.legal_pawn_moves(state))
    wall_moves: list[Move] = list(candidate_walls(state, target=target))
    moves = pawn_moves + wall_moves
    if not moves:
        return [PassMove()]
    return moves
