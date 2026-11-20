"""Monte Carlo Tree Search (UCT) agent for dynamic Quoridor."""
from __future__ import annotations

import math
import random
import time
from typing import TYPE_CHECKING

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..types import Move, PawnMove, WallMove

if TYPE_CHECKING:
    from ..state import GameState


class _MCTSNode:
    """A node in the MCTS tree."""
    __slots__ = (
        "state",
        "parent",
        "move",
        "mover",
        "untried_moves",
        "children",
        "visits",
        "total_value",
    )

    def __init__(
        self,
        state: GameState,
        parent: _MCTSNode | None = None,
        move: Move | None = None,
    ):
        self.state = state
        self.parent = parent
        self.move = move
        self.mover = parent.state.current if parent is not None else None
        self.untried_moves: list[Move] | None = None
        self.children: list[_MCTSNode] = []
        self.visits: int = 0
        # per-player payoff sum
        self.total_value: dict[int, float] = {p: 0.0 for p in state.config.players}


class MCTSAgent(Agent):
    """UCT Monte Carlo Tree Search for 2 or 4 players on dynamic boards."""

    def __init__(
        self,
        iterations: int = 1000,
        time_limit_s: float | None = None,
        c: float = 1.4,
        rollout_depth: int | None = None,
        rollout_policy: str = "path_biased",
        rollout_greedy_share: float = 0.95,
        cutoff_scoring: str = "vs_mean",
        use_wall_pruning: bool = True,
        wall_target: str = "all",
        seed: int | None = None,
    ):
        super().__init__(name="mcts")
        self.iterations = iterations
        self.time_limit_s = time_limit_s
        self.c = c
        self.rollout_depth = rollout_depth
        self.rollout_policy = rollout_policy
        self.rollout_greedy_share = rollout_greedy_share
        self.cutoff_scoring = cutoff_scoring
        self.use_wall_pruning = use_wall_pruning
        self.wall_target = wall_target
        self.rng = random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        if state.is_terminal():
            raise ValueError("Game is already in a terminal state")

        root_player = state.current
        # 1. Immediate Win Check
        for pm in rules.legal_pawn_moves(state):
            nxt = state.apply(pm)
            if nxt.winner() == root_player:
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                self.last_stats["eval"] = 1.0
                self.last_stats["depth"] = 1
                self.last_stats["iterations"] = 0
                return pm

        # Candidate move generation for root
        if self.use_wall_pruning:
            candidates = move_gen.candidate_moves(state, target=self.wall_target)
        else:
            candidates = rules.legal_moves(state)

        if not candidates:
            candidates = rules.legal_moves(state)

        if len(candidates) == 1:
            self.last_stats = default_stats()
            self.last_stats["nodes"] = 1
            self.last_stats["time_s"] = time.perf_counter() - t0
            self.last_stats["eval"] = 0.5
            self.last_stats["depth"] = 1
            self.last_stats["iterations"] = 0
            return candidates[0]

        root = _MCTSNode(state)
        shuffled = list(candidates)
        self.rng.shuffle(shuffled)
        root.untried_moves = shuffled

        total_nodes = 1
        max_depth = 0
        actual_iterations = 0
        max_rollout_depth = self.rollout_depth or (2 * state.config.board_size + 20)

        for it in range(self.iterations):
            if self.time_limit_s is not None and (time.perf_counter() - t0) >= self.time_limit_s:
                break

            actual_iterations += 1
            node = root
            depth = 0

            # 1. Select
            while not node.state.is_terminal() and (node.untried_moves is not None and len(node.untried_moves) == 0):
                depth += 1
                node = self._select_child(node)

            # 2. Expand
            if not node.state.is_terminal():
                if node.untried_moves is None:
                    if self.use_wall_pruning:
                        raw = move_gen.candidate_moves(node.state, target=self.wall_target)
                    else:
                        raw = rules.legal_moves(node.state)
                    if not raw:
                        raw = rules.legal_moves(node.state)
                    self.rng.shuffle(raw)
                    node.untried_moves = raw

                if node.untried_moves:
                    depth += 1
                    move = node.untried_moves.pop()
                    next_state = node.state.apply(move)
                    child = _MCTSNode(next_state, parent=node, move=move)
                    node.children.append(child)
                    node = child
                    total_nodes += 1

            if depth > max_depth:
                max_depth = depth

            # 3. Simulate (Rollout with wall-respecting shortest paths)
            scores = self._simulate(node.state, max_rollout_depth)

            # 4. Backpropagate
            curr: _MCTSNode | None = node
            while curr is not None:
                curr.visits += 1
                for p, val in scores.items():
                    curr.total_value[p] += val
                curr = curr.parent

        # Select child with highest visit count
        best_child = max(root.children, key=lambda c: c.visits)
        chosen_move = best_child.move
        assert chosen_move is not None

        root_win_rate = best_child.total_value[root_player] / max(1, best_child.visits)

        self.last_stats = default_stats()
        self.last_stats["nodes"] = total_nodes
        self.last_stats["time_s"] = time.perf_counter() - t0
        self.last_stats["eval"] = root_win_rate
        self.last_stats["depth"] = max_depth
        self.last_stats["iterations"] = actual_iterations
        return chosen_move

    def _select_child(self, node: _MCTSNode) -> _MCTSNode:
        """Select child according to UCT from the perspective of the node's current player."""
        mover = node.state.current
        log_parent = math.log(max(1, node.visits))
        best_score = -float("inf")
        best_child = node.children[0]

        for child in node.children:
            q = child.total_value[mover] / max(1, child.visits)
            u = self.c * math.sqrt(log_parent / child.visits)
            score = q + u
            if score > best_score:
                best_score = score
                best_child = child

        return best_child

    def _simulate(self, state: GameState, max_depth: int) -> dict[int, float]:
        """Perform simulation using wall-respecting BFS rollouts."""
        sim = state
        players = sim.config.players
        bs = sim.config.board_size

        dist_tables: dict[int, list[int | None]] = {}

        for _ in range(max_depth):
            if sim.is_terminal():
                break

            curr = sim.current

            if curr not in dist_tables:
                dist_tables[curr] = pathfinding.multi_source_distances(sim, curr)
            d_curr = dist_tables[curr]

            step: Move | None = None
            if self.rollout_policy == "path_biased":
                if self.rng.random() < self.rollout_greedy_share:
                    p_moves = rules.legal_pawn_moves(sim)
                    if p_moves:
                        best_d = 999
                        best_pm: list[PawnMove] = []
                        for pm in p_moves:
                            d = d_curr[pm.to[0] * bs + pm.to[1]]
                            if d is None:
                                d = 99
                            if d < best_d:
                                best_d = d
                                best_pm = [pm]
                            elif d == best_d:
                                best_pm.append(pm)
                        step = self.rng.choice(best_pm)
                    else:
                        c_moves = move_gen.candidate_moves(sim, target=self.wall_target)
                        step = self.rng.choice(c_moves) if c_moves else None
                else:
                    c_moves = move_gen.candidate_moves(sim, target=self.wall_target)
                    step = self.rng.choice(c_moves) if c_moves else None
            elif self.rollout_policy == "random":
                c_moves = move_gen.candidate_moves(sim, target=self.wall_target)
                step = self.rng.choice(c_moves) if c_moves else None
            else:
                raise ValueError(f"unknown rollout policy: {self.rollout_policy!r}")

            if step is None:
                break

            if isinstance(step, WallMove):
                dist_tables.clear()

            sim = sim.apply(step)

        w = sim.winner()
        if w is not None:
            return {p: (1.0 if p == w else 0.0) for p in players}

        # Cutoff heuristic scoring
        scores: dict[int, float] = {}
        d_dict: dict[int, int] = {}
        for p in players:
            if p not in dist_tables:
                dist_tables[p] = pathfinding.multi_source_distances(sim, p)
            cell = sim.pawn(p)
            d = dist_tables[p][cell[0] * bs + cell[1]]
            d_dict[p] = 99 if d is None else d

        for p in players:
            own_d = d_dict[p]
            opponents = [o for o in players if o != p]
            if self.cutoff_scoring == "vs_leader":
                opp_d = min(d_dict[o] for o in opponents)
            else:  # vs_mean
                opp_d = sum(d_dict[o] for o in opponents) / len(opponents)
            scores[p] = 0.5 + 0.5 * math.tanh((opp_d - own_d) / 4.0)

        return scores
