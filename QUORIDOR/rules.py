"""Move legality (owner: Rajnish)."""
from __future__ import annotations

from .state import GameState
from .types import Move, PawnMove, WallMove


def legal_pawn_moves(state: GameState) -> list[PawnMove]:
    """Legal pawn moves for state.current, including jumps and diagonals."""
    raise NotImplementedError("owner: Rajnish")


def is_wall_legal(state: GameState, wall: WallMove) -> bool:
    """Whether ``wall`` is legal for state.current."""
    raise NotImplementedError("owner: Rajnish")


def legal_wall_moves(state: GameState) -> list[WallMove]:
    """All legal walls; [] if the current player has none left."""
    raise NotImplementedError("owner: Rajnish")


def legal_moves(state: GameState) -> list[Move]:
    """Pawn moves first, then walls, in deterministic order."""
    raise NotImplementedError("owner: Rajnish")


def is_legal(state: GameState, move: Move) -> bool:
    """Whether ``move`` is legal in ``state``."""
    raise NotImplementedError("owner: Rajnish")
