"""Move legality and validation for four-player and two-player Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import (
    BOARD_SIZE,
    DIRECTIONS,
    DOWN,
    H,
    LEFT,
    RIGHT,
    UP,
    V,
)
from .pathfinding import has_path
from .types import Move, PawnMove, WallMove

if TYPE_CHECKING:
    from .state import GameState


def legal_pawn_moves(state: GameState) -> list[PawnMove]:
    """All legal pawn steps, jumps, and diagonal jumps for state.current."""
    if state.is_terminal():
        return []

    curr = state.current
    my_pos = state.pawn(curr)
    occupied = {state.pawn(p) for p in state.players if p != curr}
    moves: list[PawnMove] = []

    for dr, dc in DIRECTIONS:
        adj = (my_pos[0] + dr, my_pos[1] + dc)
        if state.is_blocked(my_pos, adj):
            continue

        if adj not in occupied:
            moves.append(PawnMove(to=adj))
        else:
            # Adjacent cell has an opponent pawn: attempt straight jump first
            straight = (adj[0] + dr, adj[1] + dc)
            can_jump_straight = (
                0 <= straight[0] < BOARD_SIZE
                and 0 <= straight[1] < BOARD_SIZE
                and not state.is_blocked(adj, straight)
                and straight not in occupied
            )

            if can_jump_straight:
                moves.append(PawnMove(to=straight))
            else:
                # Straight jump is blocked by wall, board edge, or another pawn behind
                perps = (LEFT, RIGHT) if (dr, dc) in (UP, DOWN) else (UP, DOWN)
                for pdr, pdc in perps:
                    diag = (adj[0] + pdr, adj[1] + pdc)
                    if 0 <= diag[0] < BOARD_SIZE and 0 <= diag[1] < BOARD_SIZE:
                        if not state.is_blocked(adj, diag) and diag not in occupied:
                            moves.append(PawnMove(to=diag))

    return moves


def is_wall_legal(state: GameState, wall: WallMove) -> bool:
    """Validate wall legality including bounds, overlap, crossing, and path existence for all players."""
    if state.is_terminal():
        return False
    if not isinstance(wall, WallMove):
        return False

    r, c, o = wall.r, wall.c, wall.o
    if not (0 <= r <= 7 and 0 <= c <= 7 and o in (H, V)):
        return False

    if state.walls(state.current) <= 0:
        return False

    # Overlap and crossing checks
    if o == H:
        if (r, c) in state.v_walls:
            return False
        if (r, c) in state.h_walls or (r, c - 1) in state.h_walls or (r, c + 1) in state.h_walls:
            return False
    else:
        if (r, c) in state.h_walls:
            return False
        if (r, c) in state.v_walls or (r - 1, c) in state.v_walls or (r + 1, c) in state.v_walls:
            return False

    # Fair-play invariant: ensure every active player still has a path to their goal side
    nxt = state.apply(wall)
    for p in state.players:
        if not has_path(nxt, p):
            return False

    return True


def legal_wall_moves(state: GameState) -> list[WallMove]:
    """Return all legal wall placements for state.current."""
    if state.is_terminal() or state.walls(state.current) <= 0:
        return []

    walls: list[WallMove] = []
    for o in (H, V):
        for r in range(8):
            for c in range(8):
                wall = WallMove(r, c, o)
                if is_wall_legal(state, wall):
                    walls.append(wall)

    return walls


def legal_moves(state: GameState) -> list[Move]:
    """Pawn moves first, then legal wall placements in deterministic order."""
    if state.is_terminal():
        return []
    return list(legal_pawn_moves(state)) + list(legal_wall_moves(state))


def is_legal(state: GameState, move: Move) -> bool:
    """True if move is legal in the current position."""
    if state.is_terminal():
        return False
    if isinstance(move, PawnMove):
        return move in legal_pawn_moves(state)
    if isinstance(move, WallMove):
        return is_wall_legal(state, move)
    return False
