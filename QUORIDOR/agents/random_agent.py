"""Random baseline agent (owner: Siddhesh)."""
from __future__ import annotations

from ..state import GameState
from ..types import Move
from .base import Agent


class RandomAgent(Agent):
    """Picks random moves, placing a wall with probability ``wall_prob``."""

    def __init__(self, seed=None, wall_prob=0.2):
        super().__init__("random")
        self.seed = seed
        self.wall_prob = wall_prob

    def choose_move(self, state: GameState) -> Move:
        raise NotImplementedError("owner: Siddhesh")
