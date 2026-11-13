"""Greedy baseline agent."""
from __future__ import annotations

import random as _random
import time

from .. import moves as _moves
from .. import pathfinding, rules
from ..state import GameState
from ..types import Move, PawnMove, WallMove
from .base import Agent


class GreedyAgent(Agent):
    """Greedily follows its shortest path, optionally placing walls."""

    def __init__(self, seed=None, wall_prob: float = 0.0):
        super().__init__("greedy")
        self.wall_prob = wall_prob
        self._rng = _random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        player = state.current
        opp = 1 - player

        pawn_moves = rules.legal_pawn_moves(state)
        nodes = len(pawn_moves)

        def _pawn_score(pm: PawnMove) -> int:
            ns = state.apply(pm)
            d = pathfinding.shortest_path_length(ns, player)
            return d if d is not None else 99

        shuffled = list(pawn_moves)
        self._rng.shuffle(shuffled)
        best_pawn: PawnMove = min(shuffled, key=_pawn_score)
        best_pawn_score = _pawn_score(best_pawn)

        chosen: Move = best_pawn
        chosen_eval: float | None = float(best_pawn_score)

        if (self.wall_prob > 0
                and state.walls_left[player] > 0
                and self._rng.random() < self.wall_prob):

            opp_dist_now = pathfinding.shortest_path_length(state, opp)
            if opp_dist_now is None:
                opp_dist_now = 99

            best_pawn_net = opp_dist_now - best_pawn_score

            wall_candidates = _moves.candidate_walls(state)
            nodes += len(wall_candidates)

            best_wall: WallMove | None = None
            best_wall_net = best_pawn_net  # Wall placement must strictly yield greater net distance gain than pawn advance

            for w in wall_candidates:
                ns = state.apply(w)
                d_me = pathfinding.shortest_path_length(ns, player)
                d_opp = pathfinding.shortest_path_length(ns, opp)
                if d_me is None:
                    d_me = 99
                if d_opp is None:
                    d_opp = 99
                net = d_opp - d_me
                if net > best_wall_net:
                    best_wall_net = net
                    best_wall = w

            if best_wall is not None:
                chosen = best_wall
                chosen_eval = float(best_wall_net)

        self.last_stats = {
            "nodes": nodes,
            "time_s": time.perf_counter() - t0,
            "eval": chosen_eval,
            "depth": None,
            "iterations": None,
        }
        return chosen