"""ASCII board rendering for four-player and two-player Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING
from .constants import BOARD_SIZE

if TYPE_CHECKING:
    from .state import GameState


def render_board(state: GameState) -> str:
    """Render the Quoridor board in ASCII format."""
    size = 2 * BOARD_SIZE - 1
    grid = [[" "] * size for _ in range(size)]

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            grid[2 * r][2 * c] = "."

    for p in state.players:
        pr, pc = state.pawn(p)
        grid[2 * pr][2 * pc] = str(p)

    # Render horizontal walls
    for r, c in state.h_walls:
        for k in range(3):
            grid[2 * r + 1][2 * c + k] = "-"

    # Render vertical walls
    for r, c in state.v_walls:
        for k in range(3):
            grid[2 * r + k][2 * c + 1] = "|"

    header = "  " + " ".join(str(c) for c in range(BOARD_SIZE))
    lines = [header]
    for i, row in enumerate(grid):
        label = str(i // 2) if i % 2 == 0 else " "
        lines.append(f"{label} " + "".join(row))

    walls_str = " ".join(f"P{p}={state.walls(p)}" for p in state.players)
    lines.append(f"walls left: {walls_str}  to move: P{state.current}  turn: {state.turn_count}")

    return "\n".join(lines)
