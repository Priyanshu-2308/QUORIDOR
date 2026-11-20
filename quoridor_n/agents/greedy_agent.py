"""Greedy shortest-path baseline agent for dynamic Quoridor."""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..types import Move, PawnMove, PassMove

if TYPE_CHECKING:
    from ..state import GameState


class GreedyAgent(Agent):
    """Greedy agent that moves along its shortest path to its goal side."""

    def __init__(
        self,
        wall_prob: float = 0.0,
        wall_target: str = "all",
        seed: int | None = None,
    ):
        super().__init__(name="greedy")
        self.wall_prob = wall_prob
        self.wall_target = wall_target
        self.rng = random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        if state.is_terminal():
            raise ValueError("Game is already in a terminal state")

        curr = state.current
        # Optional wall placement
        if self.wall_prob > 0.0 and state.walls(curr) > 0 and self.rng.random() < self.wall_prob:
            candidates = move_gen.candidate_walls(state, target=self.wall_target)
            if candidates:
                move: Move = self.rng.choice(candidates)
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                return move

        # Primary: step along shortest path
        path = pathfinding.shortest_path(state, curr)
        legal_pawns = rules.legal_pawn_moves(state)

        if path and len(path) >= 2:
            next_cell = path[1]
            desired_move = PawnMove(to=next_cell)
            if desired_move in legal_pawns:
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                return desired_move

        # If direct path step is blocked by another pawn, choose the legal pawn move
        # that minimizes remaining shortest-path distance to goal
        if legal_pawns:
            scored = []
            for pm in legal_pawns:
                nxt = state.apply(pm)
                d = pathfinding.shortest_path_length(nxt, curr)
                dist = 999 if d is None else d
                scored.append((dist, pm))
            scored.sort(key=lambda item: item[0])
            best_dist = scored[0][0]
            best_moves = [pm for dist, pm in scored if dist == best_dist]
            move = self.rng.choice(best_moves)
        else:
            walls = rules.legal_wall_moves(state)
            if walls:
                move = self.rng.choice(walls)
            else:
                move = PassMove()

        self.last_stats = default_stats()
        self.last_stats["nodes"] = 1
        self.last_stats["time_s"] = time.perf_counter() - t0
        return move
