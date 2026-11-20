"""ASCII text rendering for dynamic Quoridor boards."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import H, V

if TYPE_CHECKING:
    from .state import GameState

PLAYER_SYMBOLS = {0: "0", 1: "1", 2: "2", 3: "3"}


def render_board(state: GameState) -> str:
    """Render the board state as an ASCII grid."""
    n = state.config.board_size
    pawn_map = {state.pawn(p): PLAYER_SYMBOLS[p] for p in state.config.players}

    lines: list[str] = []
    # Header with column indices
    col_hdr = "   " + " ".join(f"{c:2d}" for c in range(n))
    lines.append(col_hdr)
    lines.append("   " + "---" * n)

    for r in range(n):
        # Row of cells and vertical walls
        row_str = f"{r:2d}|"
        for c in range(n):
            sym = pawn_map.get((r, c), " ·")
            if len(sym) == 1:
                sym = f" {sym}"
            row_str += sym

            # Right boundary / vertical wall
            if c < n - 1:
                if (r, c) in state.v_walls or (r - 1, c) in state.v_walls:
                    row_str += "|"
                else:
                    row_str += " "
            else:
                row_str += "|"
        lines.append(row_str)

        # Row of horizontal walls below cell row r
        if r < n - 1:
            h_str = "   "
            for c in range(n):
                if (r, c) in state.h_walls or (r, c - 1) in state.h_walls:
                    h_str += "---"
                else:
                    h_str += "   "
            lines.append(h_str)

    lines.append("   " + "---" * n)
    # Status line
    p_info = [f"P{p}: {state.pawn(p)} (walls: {state.walls(p)})" for p in state.config.players]
    lines.append(" | ".join(p_info))
    lines.append(f"Turn: {state.turn_count} | Current: P{state.current}")
    return "\n".join(lines)
