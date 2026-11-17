"""Paranoid Alpha-Beta adversarial search agent for four-player Quoridor."""
from __future__ import annotations

import random
import time
from typing import Any

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..eval import WIN_SCORE, evaluate
from ..state import GameState
from ..types import Move, PawnMove, WallMove

EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2


class ParanoidAgent(Agent):
    """Alpha-beta search under the paranoid assumption:

    On the agent's turn, it maximizes its own score.
    On all opponents' turns, they are assumed to act in coalition to minimize the agent's score.
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
        super().__init__(name="paranoid")
        self.depth = depth
        self.use_move_ordering = use_move_ordering
        self.use_wall_pruning = use_wall_pruning
        self.use_tt = use_tt
        self.wall_cap = wall_cap
        self.eval_mode = eval_mode
        self.wall_target = wall_target
        self.rng = random.Random(seed)

        self.tt: dict[tuple, tuple[int, int, float, Move]] = {}
        self.node_count = 0
        self.tt_hits = 0
        self.cutoff_count = 0

    def order_moves(self, state: GameState, moves: list[Move], tt_move: Move | None) -> list[Move]:
        """Order moves for maximum alpha-beta cutoff efficiency."""
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

        combined = ordered_pawns + ordered_walls

        if tt_move is not None and tt_move in combined:
            combined.remove(tt_move)
            combined.insert(0, tt_move)

        return combined

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        self.node_count = 0
        self.tt_hits = 0
        self.cutoff_count = 0
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

        best_score, best_move = self._search(
            state=state,
            depth=self.depth,
            alpha=-float("inf"),
            beta=float("inf"),
            root_player=root_player,
        )

        if best_move is None:
            best_move = self.rng.choice(rules.legal_moves(state))

        self.last_stats = default_stats()
        self.last_stats["nodes"] = self.node_count
        self.last_stats["time_s"] = time.perf_counter() - t0
        self.last_stats["eval"] = best_score
        self.last_stats["depth"] = self.depth
        self.last_stats["tt_hits"] = self.tt_hits
        self.last_stats["cutoffs"] = self.cutoff_count
        return best_move

    def _search(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        root_player: int,
    ) -> tuple[float, Move | None]:
        self.node_count += 1

        if state.is_terminal() or depth == 0:
            score = evaluate(state, root_player, mode=self.eval_mode)
            return score, None

        state_key = state.key()
        tt_move: Move | None = None

        if self.use_tt and state_key in self.tt:
            tt_depth, tt_flag, tt_val, tt_m = self.tt[state_key]
            tt_move = tt_m
            if tt_depth >= depth:
                self.tt_hits += 1
                if tt_flag == EXACT:
                    return tt_val, tt_m
                if tt_flag == LOWERBOUND:
                    alpha = max(alpha, tt_val)
                elif tt_flag == UPPERBOUND:
                    beta = min(beta, tt_val)
                if alpha >= beta:
                    return tt_val, tt_m

        # Move generation
        if self.use_wall_pruning:
            raw_moves = move_gen.candidate_moves(state, target=self.wall_target)
        else:
            raw_moves = rules.legal_moves(state)

        if not raw_moves:
            raw_moves = rules.legal_moves(state)

        ordered = self.order_moves(state, raw_moves, tt_move)
        orig_alpha = alpha
        best_move: Move | None = ordered[0] if ordered else None

        if state.current == root_player:
            # Maximizer node
            value = -float("inf")
            for m in ordered:
                nxt = state.apply(m)
                child_val, _ = self._search(nxt, depth - 1, alpha, beta, root_player)
                if child_val > value:
                    value = child_val
                    best_move = m
                alpha = max(alpha, value)
                if alpha >= beta:
                    self.cutoff_count += 1
                    break
        else:
            # Minimizer node (paranoid assumption: opponents minimize root player's score)
            value = float("inf")
            for m in ordered:
                nxt = state.apply(m)
                child_val, _ = self._search(nxt, depth - 1, alpha, beta, root_player)
                if child_val < value:
                    value = child_val
                    best_move = m
                beta = min(beta, value)
                if beta <= alpha:
                    self.cutoff_count += 1
                    break

        if self.use_tt and best_move is not None:
            if value <= orig_alpha:
                flag = UPPERBOUND
            elif value >= beta:
                flag = LOWERBOUND
            else:
                flag = EXACT
            self.tt[state_key] = (depth, flag, value, best_move)

        return value, best_move
