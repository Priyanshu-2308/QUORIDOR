"""Random baseline agent."""
from __future__ import annotations

import random
import time
from typing import Any

from .base import Agent, default_stats
from ..rules import legal_moves, legal_pawn_moves, legal_wall_moves
from ..state import GameState
from ..types import Move


class RandomAgent(Agent):
    """Selects legal moves uniformly at random, with configurable wall placement probability."""

    def __init__(self, wall_prob: float = 0.2, seed: int | None = None):
        super().__init__(name="random")
        self.wall_prob = wall_prob
        self.rng = random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        pawn_moves = legal_pawn_moves(state)
        walls = legal_wall_moves(state) if state.walls(state.current) > 0 else []

        # Attempt wall move with probability wall_prob if walls are available
        if walls and self.rng.random() < self.wall_prob:
            chosen = self.rng.choice(walls)
        elif pawn_moves:
            chosen = self.rng.choice(pawn_moves)
        else:
            all_legal = legal_moves(state)
            chosen = self.rng.choice(all_legal)

        self.last_stats = default_stats()
        self.last_stats["nodes"] = 1
        self.last_stats["time_s"] = time.perf_counter() - t0
        return chosen
