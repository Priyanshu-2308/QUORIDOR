"""Agent base class for four-player and two-player Quoridor."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..state import GameState
from ..types import Move


def default_stats() -> dict[str, Any]:
    """Default search diagnostics dictionary."""
    return {
        "nodes": 0,
        "time_s": 0.0,
        "eval": None,
        "depth": None,
        "iterations": None,
        "tt_hits": 0,
        "cutoffs": 0,
    }


class Agent(ABC):
    """Abstract base class for all Quoridor agents."""

    name: str
    last_stats: dict[str, Any]

    def __init__(self, name: str):
        self.name = name
        self.last_stats = default_stats()

    def reset_stats(self) -> None:
        """Reset search statistics to defaults."""
        self.last_stats = default_stats()

    @abstractmethod
    def choose_move(self, state: GameState) -> Move:
        """Choose a legal move for state.current and populate self.last_stats."""
        raise NotImplementedError
