"""Alpha-beta search agent (owner: Shivam)."""
from __future__ import annotations

from ..state import GameState
from ..types import Move
from .base import Agent


class AlphaBetaAgent(Agent):
    """Minimax with alpha-beta pruning."""

    def __init__(self, depth=3, time_limit_s=None, use_move_ordering=True,
                 use_wall_pruning=True, use_tt=True, iterative_deepening=False, seed=None):
        super().__init__("alphabeta")
        self.depth = depth
        self.time_limit_s = time_limit_s
        self.use_move_ordering = use_move_ordering
        self.use_wall_pruning = use_wall_pruning
        self.use_tt = use_tt
        self.iterative_deepening = iterative_deepening
        self.seed = seed

    def choose_move(self, state: GameState) -> Move:
        raise NotImplementedError("owner: Shivam")
