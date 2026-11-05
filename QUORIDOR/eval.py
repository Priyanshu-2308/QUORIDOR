"""Static evaluation (owner: Siddhesh)."""
from __future__ import annotations

from .state import GameState

WIN_SCORE = 10_000.0
W_PATH = 1.0
W_WALLS = 0.25


def evaluate(state: GameState, player: int) -> float:
    """Score from ``player``'s point of view; higher is better."""
    raise NotImplementedError("owner: Siddhesh")
