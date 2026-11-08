"""Random baseline agent (owner: Siddhesh)."""
from __future__ import annotations

import random as _random
import time

from .. import rules
from ..state import GameState
from ..types import Move
from .base import Agent


class RandomAgent(Agent):
    """Picks random moves, placing a wall with probability ``wall_prob``."""

    def __init__(self, seed=None, wall_prob: float = 0.2):
        super().__init__("random")
        self.wall_prob = wall_prob
        self._rng = _random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        """Return a random legal move; walls chosen with probability wall_prob."""
        t0 = time.perf_counter()

        pawn_moves = rules.legal_pawn_moves(state)
        wall_moves: list[Move] = []

        if (self.wall_prob > 0
                and state.walls_left[state.current] > 0
                and self._rng.random() < self.wall_prob):
            wall_moves = rules.legal_wall_moves(state)

        nodes = len(pawn_moves) + len(wall_moves)

        if wall_moves:
            move = self._rng.choice(wall_moves)
        else:
            move = self._rng.choice(pawn_moves)

        self.last_stats = {
            "nodes": nodes,
            "time_s": time.perf_counter() - t0,
            "eval": None,
            "depth": None,
            "iterations": None,
        }
        return move