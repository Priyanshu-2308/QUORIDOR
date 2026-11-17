"""Max^n multi-agent search for four-player Quoridor."""
from __future__ import annotations

import random
import time
from typing import Any

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..eval import WIN_SCORE, evaluate
from ..state import GameState
from ..types import Move, PawnMove, WallMove


class MaxnAgent(Agent):
    """Max^n search: each player chooses the move maximizing their own component of an N-player payoff vector.

    
    Note: Standard alpha-beta cutoffs cannot be applied in general non-zero-sum games
    without strict monotonic bounding. Thus max^n is evaluated without cutoffs, relying
    on transposition table lookups and candidate move ordering.
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

        self.tt: dict[tuple, tuple[int, dict[int, float], Move]] = {}
        self.node_count = 0
        self.tt_hits = 0

    def order_moves(self, state: GameState, moves: list[Move], tt_move: Move | None) -> list[Move]:
        """Order moves to explore high-payoff choices first."""
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
        # Sort pawn moves by remaining shortest-path distance ascending
        pawn_scored: list[tuple[int, PawnMove]] = []
        for pm in pawn_moves:
            nxt = state.apply(pm)
            d = pathfinding.shortest_path_length(nxt, curr)
            dist = 99 if d is None else d
            pawn_scored.append((dist, pm))
        pawn_scored.sort(key=lambda item: item[0])
        ordered_pawns = [pm for _, pm in pawn_scored]

        # Score candidate walls by target path delay
        if wall_moves:
            curr_idx = state.player_index(curr)
            opponents = [p for p in state.players if p != curr]
            leader = min(
                opponents,
                key=lambda p: (
                    pathfinding.shortest_path_length(state, p) or 99,
                    (state.player_index(p) - curr_idx) % state.num_players,
                ),
            )
            target_opp = leader

            d_before = pathfinding.shortest_path_length(state, target_opp) or 99
            wall_scored: list[tuple[int, WallMove]] = []
            for wm in wall_moves:
                nxt = state.apply(wm)
                d_after = pathfinding.shortest_path_length(nxt, target_opp) or 99
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

        self.last_stats = default_stats()
        self.last_stats["nodes"] = self.node_count
        self.last_stats["time_s"] = time.perf_counter() - t0
        self.last_stats["eval"] = best_vec[root_player] if best_vec else 0.0
        self.last_stats["depth"] = self.depth
        self.last_stats["tt_hits"] = self.tt_hits
        return best_move

    def _terminal_or_eval_vector(self, state: GameState) -> dict[int, float]:
        """Compute the payoff vector for all active players."""
        w = state.winner()
        if w is not None:
            vec: dict[int, float] = {}
            win_val = WIN_SCORE - state.turn_count
            loss_val = -win_val / (state.num_players - 1)
            for p in state.players:
                vec[p] = win_val if p == w else loss_val
            return vec

        # Leaf heuristic evaluation
        return {p: evaluate(state, p, mode=self.eval_mode) for p in state.players}

    def _search(self, state: GameState, depth: int) -> tuple[dict[int, float], Move | None]:
        self.node_count += 1

        if state.is_terminal() or depth == 0:
            return self._terminal_or_eval_vector(state), None

        state_key = state.key()
        tt_move: Move | None = None

        if self.use_tt and state_key in self.tt:
            tt_depth, tt_vec, tt_m = self.tt[state_key]
            if tt_depth >= depth:
                self.tt_hits += 1
                return tt_vec, tt_m
            tt_move = tt_m

        # Move generation
        if self.use_wall_pruning:
            raw_moves = move_gen.candidate_moves(state, target=self.wall_target)
        else:
            raw_moves = rules.legal_moves(state)

        if not raw_moves:
            raw_moves = rules.legal_moves(state)

        ordered = self.order_moves(state, raw_moves, tt_move)

        curr = state.current
        best_val_for_curr = -float("inf")
        best_vector: dict[int, float] = {}
        best_move: Move | None = ordered[0] if ordered else None

        for m in ordered:
            nxt = state.apply(m)
            child_vec, _ = self._search(nxt, depth - 1)
            val = child_vec[curr]

            if val > best_val_for_curr:
                best_val_for_curr = val
                best_vector = child_vec
                best_move = m

        if self.use_tt and best_move is not None:
            self.tt[state_key] = (depth, best_vector, best_move)

        return best_vector, best_move
