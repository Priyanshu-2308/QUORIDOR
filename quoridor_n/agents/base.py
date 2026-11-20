"""Base agent interface for dynamic Quoridor."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..types import Move

if TYPE_CHECKING:
    from ..state import GameState


def default_stats() -> dict[str, Any]:
    """Default search statistics structure."""
    return {
        "nodes": 0,
        "time_s": 0.0,
        "eval": 0.0,
        "depth": 0,
        "iterations": 0,
        "tt_hits": 0,
        "cutoffs": 0,
    }


class Agent:
    """Abstract base class for all Quoridor search and heuristic agents."""

    def __init__(self, name: str):
        self.name = name
        self.last_stats: dict[str, Any] = default_stats()

    def choose_move(self, state: GameState) -> Move:
        """Select a legal move for state.current."""
        raise NotImplementedError
