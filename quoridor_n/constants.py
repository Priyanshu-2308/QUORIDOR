"""Shared constants for four-player Quoridor."""
from __future__ import annotations

from typing import Tuple

BOARD_SIZE = 9
DEFAULT_WALLS_4P = 5
DEFAULT_WALLS_2P = 10

START: dict[int, tuple[int, int]] = {
    0: (8, 4),  # Bottom
    1: (4, 0),  # Left
    2: (0, 4),  # Top
    3: (4, 8),  # Right
}

UP, DOWN, LEFT, RIGHT = (-1, 0), (1, 0), (0, -1), (0, 1)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
H = "H"
V = "V"

OPPOSITE_PAIRS = ((0, 2), (1, 3))
UNREACHABLE_DIST = 99


def goal_reached(player: int, cell: tuple[int, int]) -> bool:
    """True if cell is on player's target goal side."""
    if player == 0:
        return cell[0] == 0
    if player == 1:
        return cell[1] == BOARD_SIZE - 1
    if player == 2:
        return cell[0] == BOARD_SIZE - 1
    if player == 3:
        return cell[1] == 0
    raise ValueError(f"invalid player id: {player!r}")


def goal_cells(player: int) -> list[tuple[int, int]]:
    """Return all cells on the goal side for the given player."""
    if player == 0:
        return [(0, c) for c in range(BOARD_SIZE)]
    if player == 1:
        return [(r, BOARD_SIZE - 1) for r in range(BOARD_SIZE)]
    if player == 2:
        return [(BOARD_SIZE - 1, c) for c in range(BOARD_SIZE)]
    if player == 3:
        return [(r, 0) for r in range(BOARD_SIZE)]
    raise ValueError(f"invalid player id: {player!r}")
