"""BFS path utilities over cells; walls only, the other pawn is ignored. (owner: Rajnish)"""
from __future__ import annotations

from .state import GameState
from .types import Cell


def shortest_path(state: GameState, player: int) -> list[Cell] | None:
    """Shortest path incl. start and goal cell; [pawn] if already on goal row; None if unreachable."""
    raise NotImplementedError("owner: Rajnish")


def shortest_path_length(state: GameState, player: int) -> int | None:
    """Number of steps; 0 if on goal row; None if unreachable."""
    raise NotImplementedError("owner: Rajnish")


def has_path(state: GameState, player: int) -> bool:
    """True if ``player`` can reach its goal row."""
    raise NotImplementedError("owner: Rajnish")


def distances(state: GameState) -> tuple[int | None, int | None]:
    """(path length for player 0, path length for player 1)."""
    raise NotImplementedError("owner: Rajnish")
