"""Move legality and rules for dynamic Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import DIRECTIONS, DOWN, H, LEFT, RIGHT, UP, V
from .pathfinding import has_path
from .types import Cell, Move, PawnMove, WallMove, PassMove

if TYPE_CHECKING:
    from .state import GameState


def legal_pawn_moves(state: GameState) -> list[PawnMove]:
    """Return all legal pawn moves for state.current, including jumps and diagonals."""
    if state.is_terminal():
        return []

    curr = state.current
    my_pos = state.pawn(curr)
    occupied = set(state.pawns)
    bs = state.config.board_size
    moves: list[PawnMove] = []

    for dr, dc in DIRECTIONS:
        adj = (my_pos[0] + dr, my_pos[1] + dc)
        if state.is_blocked(my_pos, adj):
            continue

        if adj not in occupied:
            moves.append(PawnMove(to=adj))
        else:
            # Adjacent cell holds a pawn: attempt straight jump first
            straight = (adj[0] + dr, adj[1] + dc)
            can_jump_straight = (
                0 <= straight[0] < bs
                and 0 <= straight[1] < bs
                and not state.is_blocked(adj, straight)
                and straight not in occupied
            )

            if can_jump_straight:
                moves.append(PawnMove(to=straight))
            else:
                # Straight jump is blocked by wall, board edge, or another pawn
                perps = (LEFT, RIGHT) if (dr, dc) in (UP, DOWN) else (UP, DOWN)
                for pdr, pdc in perps:
                    diag = (adj[0] + pdr, adj[1] + pdc)
                    if 0 <= diag[0] < bs and 0 <= diag[1] < bs:
                        if not state.is_blocked(adj, diag) and diag not in occupied:
                            moves.append(PawnMove(to=diag))

    return moves


def wall_blocks_edge(wall: WallMove, a: Cell, b: Cell) -> bool:
    """True if wall directly intersects the physical step between adjacent cells a and b."""
    r, c, o = wall.r, wall.c, wall.o
    ar, ac = a
    br, bc = b
    if o == H:
        if ac == bc and (ac == c or ac == c + 1):
            if (ar == r and br == r + 1) or (ar == r + 1 and br == r):
                return True
    else:  # V
        if ar == br and (ar == r or ar == r + 1):
            if (ac == c and bc == c + 1) or (ac == c + 1 and bc == c):
                return True
    return False


def is_wall_legal(
    state: GameState,
    wall: WallMove,
    known_paths: dict[int, list[Cell]] | None = None,
) -> bool:
    """Validate wall legality (bounds, overlaps, crossings, and path existence for all active players)."""
    if state.is_terminal():
        return False
    if not isinstance(wall, WallMove):
        return False

    r, c, o = wall.r, wall.c, wall.o
    bs = state.config.board_size
    if not (0 <= r <= bs - 2 and 0 <= c <= bs - 2 and o in (H, V)):
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

    # Fast path: on a board with no existing walls, a single wall cannot disconnect any player
    if not state.h_walls and not state.v_walls:
        return True

    # Fair-play invariant: ensure every active player retains at least one unblocked path to their goal side
    nxt = state.apply(wall)
    for p in state.config.players:
        if known_paths is not None and p in known_paths:
            path = known_paths[p]
            if path and len(path) >= 2:
                path_intact = True
                for i in range(len(path) - 1):
                    if wall_blocks_edge(wall, path[i], path[i + 1]):
                        path_intact = False
                        break
                if path_intact:
                    continue  # Known path is completely unblocked by this wall

        if not has_path(nxt, p):
            return False

    return True


def legal_wall_moves(state: GameState) -> list[WallMove]:
    """Return all legal wall placements for state.current."""
    if state.is_terminal() or state.walls(state.current) <= 0:
        return []

    walls: list[WallMove] = []
    bs = state.config.board_size
    for o in (H, V):
        for r in range(bs - 1):
            for c in range(bs - 1):
                wall = WallMove(r, c, o)
                if is_wall_legal(state, wall):
                    walls.append(wall)

    return walls


def legal_moves(state: GameState) -> list[Move]:
    """Pawn moves first, then legal wall placements in deterministic order."""
    if state.is_terminal():
        return []
    pawn_moves: list[Move] = list(legal_pawn_moves(state))
    wall_moves: list[Move] = list(legal_wall_moves(state))
    moves = pawn_moves + wall_moves
    if not moves:
        return [PassMove()]
    return moves


def is_legal(state: GameState, move: Move) -> bool:
    """True if move is legal in the current position."""
    if state.is_terminal():
        return False
    if isinstance(move, PassMove):
        return len(legal_pawn_moves(state)) == 0 and len(legal_wall_moves(state)) == 0
    if isinstance(move, PawnMove):
        return move in legal_pawn_moves(state)
    if isinstance(move, WallMove):
        return is_wall_legal(state, move)
    return False
