"""Monte Carlo tree search agent (owner: Shivam)."""
from __future__ import annotations

from ..state import GameState
from ..types import Move
from .base import Agent


class MCTSAgent(Agent):
    """UCT-based Monte Carlo tree search."""

    def __init__(self, iterations=1000, time_limit_s=None, c=1.4, rollout_depth=60,
                 rollout_policy="path_biased", use_wall_pruning=True, seed=None):
        super().__init__("mcts")
        self.iterations = iterations
        self.time_limit_s = time_limit_s
        self.c = c
        self.rollout_depth = rollout_depth
        self.rollout_policy = rollout_policy
        self.use_wall_pruning = use_wall_pruning
        self.seed = seed

    def choose_move(self, state: GameState) -> Move:
        raise NotImplementedError("owner: Shivam")
