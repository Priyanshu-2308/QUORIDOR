"""Pruned move generation for search agents (owner: Siddhesh)."""
from __future__ import annotations

from .state import GameState
from .types import Move, WallMove


def candidate_walls(state: GameState) -> list[WallMove]:
    """Pruned list of promising legal walls."""
    raise NotImplementedError("owner: Siddhesh")


def candidate_moves(state: GameState) -> list[Move]:
    """Legal pawn moves plus candidate walls (walls only if the current player has some left)."""
    raise NotImplementedError("owner: Siddhesh")
