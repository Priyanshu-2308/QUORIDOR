"""Greedy baseline agent (owner: Siddhesh)."""
from __future__ import annotations

from ..state import GameState
from ..types import Move
from .base import Agent


class GreedyAgent(Agent):
    """Greedily follows its shortest path, optionally placing walls."""

    def __init__(self, seed=None, wall_prob=0.0):
        super().__init__("greedy")
        self.seed = seed
        self.wall_prob = wall_prob

    def choose_move(self, state: GameState) -> Move:
        raise NotImplementedError("owner: Siddhesh")
