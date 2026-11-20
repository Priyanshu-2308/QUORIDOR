"""Random baseline agent for dynamic Quoridor."""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from .base import Agent, default_stats
from .. import rules
from ..types import Move, PassMove, WallMove

if TYPE_CHECKING:
    from ..state import GameState


class RandomAgent(Agent):
    """Uniform random pawn mover with occasional random wall placement."""

    def __init__(self, wall_prob: float = 0.2, seed: int | None = None):
        super().__init__(name="random")
        self.wall_prob = wall_prob
        self.rng = random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        if state.is_terminal():
            raise ValueError("Game is already in a terminal state")

        curr = state.current
        pawn_moves = rules.legal_pawn_moves(state)
        wall_moves: list[Move] = []

        if self.wall_prob > 0.0 and state.walls(curr) > 0 and self.rng.random() < self.wall_prob:
            # Uniformly select a random legal wall: in a uniform random permutation of all grooves,
            # the first legal wall encountered is uniformly distributed over all legal walls.
            bs = state.config.board_size
            grooves = [(r, c, o) for o in ("H", "V") for r in range(bs - 1) for c in range(bs - 1)]
            self.rng.shuffle(grooves)
            for r, c, o in grooves:
                w = WallMove(r, c, o)
                if rules.is_wall_legal(state, w):
                    wall_moves = [w]
                    break

        if wall_moves:
            move: Move = wall_moves[0]
        elif pawn_moves:
            move = self.rng.choice(pawn_moves)
        elif state.walls(curr) > 0:
            walls = rules.legal_wall_moves(state)
            move = self.rng.choice(walls) if walls else PassMove()
        else:
            move = PassMove()

        self.last_stats = default_stats()
        self.last_stats["nodes"] = 1
        self.last_stats["time_s"] = time.perf_counter() - t0
        return move
