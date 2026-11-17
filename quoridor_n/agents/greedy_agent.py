"""Greedy shortest-path baseline agent."""
from __future__ import annotations

import random
import time
from typing import Any

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..state import GameState
from ..types import Move, PawnMove, WallMove


class GreedyAgent(Agent):
    """Steps along its shortest path to goal, with optional defensive wall placement."""

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
        curr = state.current
        pawn_moves = rules.legal_pawn_moves(state)

        # 1. Attempt wall placement if enabled and walls available
        if self.wall_prob > 0.0 and state.walls(curr) > 0 and self.rng.random() < self.wall_prob:
            cand_walls = move_gen.candidate_walls(state, target=self.wall_target)
            curr_own_d = pathfinding.shortest_path_length(state, curr) or 99

            curr_idx = state.player_index(curr)
            opponents = [p for p in state.players if p != curr]

            best_wall: WallMove | None = None
            best_gain = 0

            for w in cand_walls:
                nxt = state.apply(w)
                nxt_own_d = pathfinding.shortest_path_length(nxt, curr) or 99
                own_penalty = nxt_own_d - curr_own_d

                # Compute target opponent delay
                if self.wall_target == "next":
                    targets = [state.players[(curr_idx + 1) % state.num_players]]
                elif self.wall_target == "leader":
                    leader = min(
                        opponents,
                        key=lambda p: (
                            pathfinding.shortest_path_length(state, p) or 99,
                            (state.player_index(p) - curr_idx) % state.num_players,
                        ),
                    )
                    targets = [leader]
                else:  # "all"
                    targets = opponents

                # Delay on the most delayed target
                max_opp_delay = 0
                for tgt in targets:
                    d_before = pathfinding.shortest_path_length(state, tgt) or 99
                    d_after = pathfinding.shortest_path_length(nxt, tgt) or 99
                    delay = d_after - d_before
                    if delay > max_opp_delay:
                        max_opp_delay = delay

                net_gain = max_opp_delay - own_penalty
                if net_gain > best_gain:
                    best_gain = net_gain
                    best_wall = w

            if best_wall is not None and best_gain > 0:
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                return best_wall

        # 2. Otherwise pick the pawn move that minimizes remaining path length
        best_pawn_move: Move | None = None
        min_dist = 999

        # Shuffle pawn moves with seeded rng for fair tie-breaking
        shuffled_pawn_moves = list(pawn_moves)
        self.rng.shuffle(shuffled_pawn_moves)

        for pm in shuffled_pawn_moves:
            nxt = state.apply(pm)
            d = pathfinding.shortest_path_length(nxt, curr)
            dist = 99 if d is None else d
            if dist < min_dist:
                min_dist = dist
                best_pawn_move = pm

        chosen = best_pawn_move if best_pawn_move is not None else self.rng.choice(rules.legal_moves(state))

        self.last_stats = default_stats()
        self.last_stats["nodes"] = len(pawn_moves)
        self.last_stats["time_s"] = time.perf_counter() - t0
        return chosen
