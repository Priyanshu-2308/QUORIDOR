"""Max^n multi-player game tree search agent for four-player Quoridor."""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..eval import WIN_SCORE, evaluate
from ..types import Move, PawnMove, WallMove

if TYPE_CHECKING:
    from ..state import GameState


class MaxnAgent(Agent):
    """Max^n search for four-player Quoridor.

    Each node returns an evaluation vector (v0, v1, v2, v3).
    The player to move chooses the child that maximizes their own component.
    Not offered in two-player mode.
    """

    def __init__(
        self,
        depth: int = 2,
        use_move_ordering: bool = True,
        use_wall_pruning: bool = True,
        use_tt: bool = True,
        wall_cap: int | None = 12,
        eval_mode: str = "mean",
        wall_target: str = "all",
        seed: int | None = None,
    ):
        super().__init__(name="maxn")
        self.depth = depth
        self.use_move_ordering = use_move_ordering
        self.use_wall_pruning = use_wall_pruning
        self.use_tt = use_tt
        self.wall_cap = wall_cap
        self.eval_mode = eval_mode
        self.wall_target = wall_target
        self.rng = random.Random(seed)

        self.tt: dict[tuple, tuple[int, tuple[float, ...], Move]] = {}
        self.node_count = 0
        self.tt_hits = 0

    def order_moves(
        self,
        state: GameState,
        moves: list[Move],
        tt_move: Move | None,
    ) -> list[Move]:
        """Order moves for move selection efficiency."""
        if not self.use_move_ordering:
            return moves

        pawn_moves: list[PawnMove] = []
        wall_moves: list[WallMove] = []
        for m in moves:
            if isinstance(m, PawnMove):
                pawn_moves.append(m)
            elif isinstance(m, WallMove):
                wall_moves.append(m)

        curr = state.current
        pawn_scored: list[tuple[int, PawnMove]] = []
        for pm in pawn_moves:
            nxt = state.apply(pm)
            d = pathfinding.shortest_path_length(nxt, curr)
            dist = 999 if d is None else d
            pawn_scored.append((dist, pm))
        pawn_scored.sort(key=lambda item: item[0])
        ordered_pawns = [pm for _, pm in pawn_scored]

        if wall_moves:
            curr_idx = state.player_index(curr)
            opponents = [p for p in state.config.players if p != curr]
            leader = min(
                opponents,
                key=lambda p: (
                    pathfinding.shortest_path_length(state, p) or 999,
                    (state.player_index(p) - curr_idx) % state.config.num_players,
                ),
            )
            d_before = pathfinding.shortest_path_length(state, leader) or 999
            wall_scored: list[tuple[int, WallMove]] = []
            for wm in wall_moves:
                nxt = state.apply(wm)
                d_after = pathfinding.shortest_path_length(nxt, leader) or 999
                delay = d_after - d_before
                wall_scored.append((delay, wm))

            wall_scored.sort(key=lambda item: item[0], reverse=True)
            if self.wall_cap is not None:
                ordered_walls = [wm for _, wm in wall_scored[: self.wall_cap]]
            else:
                ordered_walls = [wm for _, wm in wall_scored]
        else:
            ordered_walls = []

        other_moves = [m for m in moves if not isinstance(m, (PawnMove, WallMove))]
        combined = ordered_pawns + ordered_walls + other_moves

        if tt_move is not None and tt_move in combined:
            combined.remove(tt_move)
            combined.insert(0, tt_move)

        return combined

    def choose_move(self, state: GameState) -> Move:
        if state.config.num_players != 4:
            raise ValueError("MaxnAgent is only offered for 4-player games")

        t0 = time.perf_counter()
        self.node_count = 0
        self.tt_hits = 0
        root_player = state.current

        # 1. Immediate Win Check
        for m in rules.legal_pawn_moves(state):
            nxt = state.apply(m)
            if nxt.winner() == root_player:
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                self.last_stats["eval"] = WIN_SCORE
                self.last_stats["depth"] = self.depth
                return m

        best_vec, best_move = self._search(state=state, depth=self.depth)

        if best_move is None:
            best_move = self.rng.choice(rules.legal_moves(state))

        curr_idx = state.player_index(root_player)
        eval_score = best_vec[curr_idx] if best_vec else 0.0

        self.last_stats = default_stats()
        self.last_stats["nodes"] = self.node_count
        self.last_stats["time_s"] = time.perf_counter() - t0
        self.last_stats["eval"] = eval_score
        self.last_stats["depth"] = self.depth
        self.last_stats["tt_hits"] = self.tt_hits
        self.last_stats["cutoffs"] = 0
        return best_move

    def _search(self, state: GameState, depth: int) -> tuple[tuple[float, ...], Move | None]:
        self.node_count += 1
        players = state.config.players

        if state.is_terminal():
            w = state.winner()
            vec = []
            for p in players:
                if w is not None:
                    vec.append(WIN_SCORE if p == w else -WIN_SCORE)
                else:
                    vec.append(0.0)
            return tuple(vec), None

        if depth == 0:
            vec = tuple(evaluate(state, p, mode=self.eval_mode) for p in players)
            return vec, None

        state_key = state.key()
        tt_move: Move | None = None

        if self.use_tt and state_key in self.tt:
            tt_depth, tt_vec, tt_m = self.tt[state_key]
            if tt_depth >= depth:
                self.tt_hits += 1
                return tt_vec, tt_m
            tt_move = tt_m

        if self.use_wall_pruning:
            raw_moves = move_gen.candidate_moves(state, target=self.wall_target)
        else:
            raw_moves = rules.legal_moves(state)

        if not raw_moves:
            raw_moves = rules.legal_moves(state)

        ordered = self.order_moves(state, raw_moves, tt_move)
        curr = state.current
        curr_idx = state.player_index(curr)

        best_val = -float("inf")
        best_vec: tuple[float, ...] = tuple(0.0 for _ in players)
        best_move: Move | None = ordered[0] if ordered else None

        for m in ordered:
            nxt = state.apply(m)
            child_vec, _ = self._search(nxt, depth - 1)
            mover_val = child_vec[curr_idx]
            if mover_val > best_val:
                best_val = mover_val
                best_vec = child_vec
                best_move = m

        if self.use_tt and best_move is not None:
            self.tt[state_key] = (depth, best_vec, best_move)

        return best_vec, best_move
