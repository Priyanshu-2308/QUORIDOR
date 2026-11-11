"""Alpha-beta search agent."""
from __future__ import annotations

import random as _random
import time

from .. import eval as _eval
from .. import moves as _moves
from .. import pathfinding, rules
from ..state import GameState
from ..types import Move, PawnMove, WallMove
from .base import Agent


class AlphaBetaAgent(Agent):
    """Minimax with alpha-beta pruning."""

    def __init__(
        self,
        depth: int = 3,
        time_limit_s: float | None = None,
        use_move_ordering: bool = True,
        use_wall_pruning: bool = True,
        use_tt: bool = True,
        iterative_deepening: bool = False,
        seed: int | None = None,
    ):
        super().__init__("alphabeta")
        self.depth = depth
        self.time_limit_s = time_limit_s
        self.use_move_ordering = use_move_ordering
        self.use_wall_pruning = use_wall_pruning
        self.use_tt = use_tt
        self.iterative_deepening = iterative_deepening
        self.seed = seed

        self.tt: dict[tuple, tuple[int, float, str, Move | None]] = {}
        self.nodes: int = 0
        self.tt_hits: int = 0
        self.cutoffs: int = 0

    def _order_moves(
        self,
        state: GameState,
        raw_moves: list[Move],
        tt_best_move: Move | None,
    ) -> list[Move]:
        if not self.use_move_ordering:
            return list(raw_moves)

        curr = state.current
        pawns: list[PawnMove] = []
        walls: list[WallMove] = []
        for m in raw_moves:
            if isinstance(m, PawnMove):
                pawns.append(m)
            elif isinstance(m, WallMove):
                walls.append(m)

        # Sort pawn moves ascending by own distance to goal after move
        def _pawn_dist(pm: PawnMove) -> int:
            ns = state.apply(pm)
            d = pathfinding.shortest_path_length(ns, curr)
            return d if d is not None else 99

        pawns.sort(key=_pawn_dist)

        # Sort walls descending by (opponent_distance_after - own_distance_after)
        def _wall_net(wm: WallMove) -> int:
            ns = state.apply(wm)
            d0, d1 = pathfinding.distances(ns)
            d_me = d0 if curr == 0 else d1
            d_opp = d1 if curr == 0 else d0
            if d_me is None:
                d_me = 99
            if d_opp is None:
                d_opp = 99
            return d_opp - d_me

        walls.sort(key=_wall_net, reverse=True)
        walls = walls[:12]

        ordered: list[Move] = list(pawns) + list(walls)

        if tt_best_move is not None:
            if tt_best_move in ordered:
                ordered.remove(tt_best_move)
                ordered.insert(0, tt_best_move)
            elif tt_best_move in raw_moves:
                ordered.insert(0, tt_best_move)

        return ordered

    def _negamax(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        ply: int,
        t0: float,
    ) -> float:
        self.nodes += 1

        if self.iterative_deepening and self.time_limit_s is not None:
            if (self.nodes & 31 == 0) and (time.perf_counter() - t0 >= self.time_limit_s):
                raise TimeoutError

        if state.is_terminal():
            if state.winner() == state.current:
                return _eval.WIN_SCORE - ply
            else:
                return -_eval.WIN_SCORE + ply

        if depth <= 0:
            return _eval.evaluate(state, state.current)

        alpha_orig = alpha
        state_key = state.key()
        tt_best_move = None

        if self.use_tt and state_key in self.tt:
            self.tt_hits += 1
            tt_depth, tt_val, tt_flag, tt_best_move = self.tt[state_key]
            if tt_depth >= depth:
                if tt_flag == "EXACT":
                    return tt_val
                elif tt_flag == "LOWER":
                    alpha = max(alpha, tt_val)
                elif tt_flag == "UPPER":
                    beta = min(beta, tt_val)
                if alpha >= beta:
                    self.cutoffs += 1
                    return tt_val

        if self.use_wall_pruning:
            raw_moves = _moves.candidate_moves(state)
        else:
            raw_moves = rules.legal_moves(state)

        if not raw_moves:
            return _eval.evaluate(state, state.current)

        ordered_moves = self._order_moves(state, raw_moves, tt_best_move)

        best_val = -float("inf")
        best_move: Move | None = None

        for move in ordered_moves:
            next_state = state.apply(move)
            val = -self._negamax(next_state, depth - 1, -beta, -alpha, ply + 1, t0)

            if val > best_val:
                best_val = val
                best_move = move

            alpha = max(alpha, val)
            if alpha >= beta:
                self.cutoffs += 1
                break

        if self.use_tt:
            if best_val <= alpha_orig:
                flag = "UPPER"
            elif best_val >= beta:
                flag = "LOWER"
            else:
                flag = "EXACT"
            self.tt[state_key] = (depth, best_val, flag, best_move)

        return best_val

    def _search_root(
        self,
        state: GameState,
        raw_moves: list[Move],
        depth: int,
        t0: float,
        rng: _random.Random,
    ) -> tuple[Move, float]:
        tt_best_move = None
        if self.use_tt and state.key() in self.tt:
            tt_best_move = self.tt[state.key()][3]

        ordered_moves = self._order_moves(state, raw_moves, tt_best_move)
        alpha = -float("inf")
        beta = float("inf")
        best_val = -float("inf")
        best_moves: list[Move] = []

        for move in ordered_moves:
            if self.iterative_deepening and self.time_limit_s is not None:
                if time.perf_counter() - t0 >= self.time_limit_s:
                    raise TimeoutError

            next_state = state.apply(move)
            val = -self._negamax(next_state, depth - 1, -beta, -alpha, ply=1, t0=t0)

            if val > best_val:
                best_val = val
                best_moves = [move]
            elif val == best_val:
                best_moves.append(move)

            alpha = max(alpha, val)

        chosen = rng.choice(best_moves)
        if self.use_tt:
            self.tt[state.key()] = (depth, best_val, "EXACT", chosen)

        return chosen, best_val

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        if state.is_terminal():
            raise ValueError("Game is already won")

        if self.use_wall_pruning:
            raw_moves = _moves.candidate_moves(state)
        else:
            raw_moves = rules.legal_moves(state)

        if not raw_moves:
            raise ValueError("No legal moves available")

        if self.use_tt:
            self.tt.clear()
        self.nodes = 0
        self.tt_hits = 0
        self.cutoffs = 0

        rng = _random.Random(self.seed)

        if self.iterative_deepening:
            chosen_move: Move = raw_moves[0]
            best_eval: float | None = None
            completed_depth = 0
            for d in range(1, self.depth + 1):
                if self.time_limit_s is not None and (time.perf_counter() - t0) >= self.time_limit_s:
                    break
                try:
                    depth_move, depth_eval = self._search_root(
                        state, raw_moves, d, t0, rng
                    )
                    chosen_move = depth_move
                    best_eval = depth_eval
                    completed_depth = d
                except TimeoutError:
                    break
        else:
            chosen_move, best_eval = self._search_root(
                state, raw_moves, self.depth, t0, rng
            )
            completed_depth = self.depth

        self.last_stats = {
            "nodes": self.nodes,
            "time_s": time.perf_counter() - t0,
            "eval": float(best_eval) if best_eval is not None else None,
            "depth": completed_depth,
            "iterations": None,
            "tt_hits": self.tt_hits,
            "cutoffs": self.cutoffs,
        }
        return chosen_move
