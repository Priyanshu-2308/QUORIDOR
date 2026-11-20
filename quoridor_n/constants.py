"""Constants and geometric helpers for dynamic-board Quoridor."""
from __future__ import annotations

import math

UP, DOWN, LEFT, RIGHT = (-1, 0), (1, 0), (0, -1), (0, 1)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
H = "H"
V = "V"

OPPOSITE_PAIRS = ((0, 2), (1, 3))
UNREACHABLE_DIST = 99


def default_walls_per_player(board_size: int, num_players: int) -> int:
    """Default wall inventory: N + 1 for 2 players, ceil((N + 1) / 2) for 4 players."""
    if num_players == 2:
        return board_size + 1
    if num_players == 4:
        return math.ceil((board_size + 1) / 2)
    raise ValueError(f"num_players must be 2 or 4, got {num_players!r}")


def start_cell(player: int, board_size: int) -> tuple[int, int]:
    """Start cell for player in 0..3 on an N x N board.
    
    c0 = (N - 1) // 2
    Seat 0 (Bottom): (N - 1, c0)
    Quarter-turn clockwise: (r, c) -> (c, N - 1 - r)
    Seat 1 (Left): (c0, 0)
    Seat 2 (Top): (0, N - 1 - c0)
    Seat 3 (Right): (N - 1 - c0, N - 1)
    """
    c0 = (board_size - 1) // 2
    if player == 0:
        return (board_size - 1, c0)
    if player == 1:
        return (c0, 0)
    if player == 2:
        return (0, board_size - 1 - c0)
    if player == 3:
        return (board_size - 1 - c0, board_size - 1)
    raise ValueError(f"invalid player id: {player!r}")


def goal_reached(player: int, cell: tuple[int, int], board_size: int) -> bool:
    """True if cell is on player's designated goal side."""
    r, c = cell
    if player == 0:
        return r == 0
    if player == 1:
        return c == board_size - 1
    if player == 2:
        return r == board_size - 1
    if player == 3:
        return c == 0
    raise ValueError(f"invalid player id: {player!r}")


def goal_cells(player: int, board_size: int) -> list[tuple[int, int]]:
    """Return all cells along the target goal side for player."""
    if player == 0:
        return [(0, c) for c in range(board_size)]
    if player == 1:
        return [(r, board_size - 1) for r in range(board_size)]
    if player == 2:
        return [(board_size - 1, c) for c in range(board_size)]
    if player == 3:
        return [(r, 0) for r in range(board_size)]
    raise ValueError(f"invalid player id: {player!r}")
