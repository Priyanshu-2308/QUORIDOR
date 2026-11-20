"""quoridor_n: Generalized Quoridor engine for dynamic board sizes and 2/4 players."""
from __future__ import annotations

from .config import GameConfig
from .constants import (
    DIRECTIONS,
    DOWN,
    H,
    LEFT,
    RIGHT,
    UP,
    V,
    default_walls_per_player,
    goal_cells,
    goal_reached,
    start_cell,
)
from .state import GameState
from .types import Cell, Move, PawnMove, WallMove, PassMove

__all__ = [
    "GameConfig",
    "GameState",
    "Cell",
    "Move",
    "PawnMove",
    "WallMove",
    "PassMove",
    "H",
    "V",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "DIRECTIONS",
    "default_walls_per_player",
    "start_cell",
    "goal_reached",
    "goal_cells",
]
