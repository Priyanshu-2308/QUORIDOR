"""Agent base class (owner: Shubham)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..state import GameState
from ..types import Move


def _default_stats() -> dict:
    return {"nodes": 0, "time_s": 0.0, "eval": None, "depth": None, "iterations": None}


class Agent(ABC):
    """Base class for all Quoridor agents."""

    name: str
    last_stats: dict

    def __init__(self, name: str):
        self.name = name
        self.last_stats = _default_stats()

    def reset_stats(self) -> None:
        """Restore ``last_stats`` to its defaults."""
        self.last_stats = _default_stats()

    @abstractmethod
    def choose_move(self, state: GameState) -> Move:
        """Pick a move for ``state.current``; must set ``self.last_stats``."""
        raise NotImplementedError
