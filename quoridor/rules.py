"""Move legality (owner: Rajnish)."""
from __future__ import annotations

from .constants import DIRECTIONS, DOWN, H, LEFT, RIGHT, UP, V
from .pathfinding import has_path
from .state import GameState
from .types import Move, PawnMove, WallMove


def legal_pawn_moves(state: GameState) -> list[PawnMove]:
    """Legal pawn moves for state.current, including jumps and diagonals."""
    if state.is_terminal():
        return []
    curr = state.current
    opp = 1 - curr
    my_pos = state.pawns[curr]
    opp_pos = state.pawns[opp]
    moves: list[PawnMove] = []
    for dr, dc in DIRECTIONS:
        n = (my_pos[0] + dr, my_pos[1] + dc)
        if state.is_blocked(my_pos, n):
            continue
        if n != opp_pos:
            moves.append(PawnMove(to=n))
        else:
            j = (opp_pos[0] + dr, opp_pos[1] + dc)
            if not state.is_blocked(opp_pos, j):
                moves.append(PawnMove(to=j))
            else:
                perps = (LEFT, RIGHT) if (dr, dc) in (UP, DOWN) else (UP, DOWN)
                for pdr, pdc in perps:
                    s = (opp_pos[0] + pdr, opp_pos[1] + pdc)
                    if not state.is_blocked(opp_pos, s):
                        moves.append(PawnMove(to=s))
    return moves


def is_wall_legal(state: GameState, wall: WallMove) -> bool:
    """Whether ``wall`` is legal for state.current."""
    if state.is_terminal():
        return False
    if not isinstance(wall, WallMove):
        return False
    r, c, o = wall.r, wall.c, wall.o
    if not (0 <= r <= 7 and 0 <= c <= 7 and o in (H, V)):
        return False
    if state.walls_left[state.current] <= 0:
        return False
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
    nxt = state.apply(wall)
    return has_path(nxt, 0) and has_path(nxt, 1)


def legal_wall_moves(state: GameState) -> list[WallMove]:
    """All legal walls; [] if the current player has none left."""
    if state.is_terminal() or state.walls_left[state.current] <= 0:
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
    """Pawn moves first, then walls, in deterministic order."""
    if state.is_terminal():
        return []
    pawn_moves: list[Move] = list(legal_pawn_moves(state))
    wall_moves: list[Move] = list(legal_wall_moves(state))
    return pawn_moves + wall_moves


def is_legal(state: GameState, move: Move) -> bool:
    """Whether ``move`` is legal in ``state``."""
    if state.is_terminal():
        return False
    if isinstance(move, PawnMove):
        return move in legal_pawn_moves(state)
    if isinstance(move, WallMove):
        return is_wall_legal(state, move)
    return False
