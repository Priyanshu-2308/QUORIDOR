"""Monte Carlo tree search agent."""
from __future__ import annotations

from collections import deque
import math
import random as _random
import time

from .. import moves as _moves
from .. import pathfinding, rules
from ..constants import BOARD_SIZE, DIRECTIONS, GOAL_ROW
from ..state import GameState
from ..types import Move, PawnMove, WallMove
from .base import Agent


def _compute_goal_dist(state: GameState, player: int) -> list[int]:
    """BFS shortest distance from every cell to player's goal row (ignoring other pawn)."""
    goal_row = GOAL_ROW[player]
    dist = [-1] * (BOARD_SIZE * BOARD_SIZE)
    queue = deque()
    for c in range(BOARD_SIZE):
        idx = goal_row * BOARD_SIZE + c
        dist[idx] = 0
        queue.append((goal_row, c))

    while queue:
        r, c = queue.popleft()
        d = dist[r * BOARD_SIZE + c]
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nidx = nr * BOARD_SIZE + nc
                if dist[nidx] == -1 and not state.is_blocked((r, c), (nr, nc)):
                    dist[nidx] = d + 1
                    queue.append((nr, nc))
    return dist


class _MCTSNode:
    __slots__ = (
        "state",
        "parent",
        "move",
        "mover",
        "untried_moves",
        "children",
        "visits",
        "value",
    )

    def __init__(self, state: GameState, parent: _MCTSNode | None = None, move: Move | None = None):
        self.state = state
        self.parent = parent
        self.move = move
        self.mover = parent.state.current if parent is not None else None
        self.untried_moves: list[Move] | None = None
        self.children: list[_MCTSNode] = []
        self.visits: int = 0
        self.value: float = 0.0


class MCTSAgent(Agent):
    """UCT-based Monte Carlo tree search."""

    def __init__(
        self,
        iterations: int = 1000,
        time_limit_s: float | None = None,
        c: float = 1.4,
        rollout_depth: int = 60,
        rollout_policy: str = "path_biased",
        use_wall_pruning: bool = True,
        seed: int | None = None,
    ):
        super().__init__("mcts")
        self.iterations = iterations
        self.time_limit_s = time_limit_s
        self.c = c
        self.rollout_depth = rollout_depth
        self.rollout_policy = rollout_policy
        self.use_wall_pruning = use_wall_pruning
        self.seed = seed
        self._rng = _random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        if state.is_terminal():
            raise ValueError("Game is already won")

        if self.use_wall_pruning:
            candidates = _moves.candidate_moves(state)
        else:
            candidates = rules.legal_moves(state)

        if not candidates:
            raise ValueError("No legal moves available")

        if len(candidates) == 1:
            self.last_stats = {
                "nodes": 1,
                "time_s": time.perf_counter() - t0,
                "eval": 1.0,
                "depth": 1,
                "iterations": 0,
            }
            return candidates[0]

        root = _MCTSNode(state)
        root_player = state.current
        shuffled = list(candidates)
        self._rng.shuffle(shuffled)
        root.untried_moves = shuffled

        total_nodes = 1
        max_depth = 0
        actual_iterations = 0

        for it in range(self.iterations):
            if self.time_limit_s is not None and (time.perf_counter() - t0) >= self.time_limit_s:
                break
            actual_iterations += 1

            # 1. Selection
            curr = root
            depth = 0
            while not curr.state.is_terminal():
                if curr.untried_moves is None:
                    cands = (
                        _moves.candidate_moves(curr.state)
                        if self.use_wall_pruning
                        else rules.legal_moves(curr.state)
                    )
                    self._rng.shuffle(cands)
                    curr.untried_moves = cands

                if curr.untried_moves:
                    break
                if not curr.children:
                    break

                log_parent = math.log(curr.visits) if curr.visits > 0 else 0.0
                best_score = -float("inf")
                best_children: list[_MCTSNode] = []
                for child in curr.children:
                    if child.visits == 0:
                        score = float("inf")
                    else:
                        q = child.value / child.visits
                        u = self.c * math.sqrt(log_parent / child.visits)
                        score = q + u
                    if score > best_score:
                        best_score = score
                        best_children = [child]
                    elif score == best_score:
                        best_children.append(child)

                curr = self._rng.choice(best_children)
                depth += 1
                if depth > max_depth:
                    max_depth = depth

            if curr.untried_moves is None:
                cands = (
                    _moves.candidate_moves(curr.state)
                    if self.use_wall_pruning
                    else rules.legal_moves(curr.state)
                )
                self._rng.shuffle(cands)
                curr.untried_moves = cands

            # 2. Expansion
            if not curr.state.is_terminal() and curr.untried_moves:
                move = curr.untried_moves.pop()
                next_state = curr.state.apply(move)
                child = _MCTSNode(next_state, parent=curr, move=move)
                curr.children.append(child)
                total_nodes += 1
                curr = child
                depth += 1
                if depth > max_depth:
                    max_depth = depth

            # 3. Simulation (Rollout)
            sim_state = curr.state
            ply = 0
            d0: list[int] | None = None
            d1: list[int] | None = None

            while not sim_state.is_terminal() and ply < self.rollout_depth:
                ply += 1
                curr_p = sim_state.current

                if d0 is None or d1 is None:
                    d0 = _compute_goal_dist(sim_state, 0)
                    d1 = _compute_goal_dist(sim_state, 1)
                d_curr = d0 if curr_p == 0 else d1

                if self.rollout_policy == "path_biased":
                    # 0.95 chosen by trial against the greedy agent
                    if self._rng.random() < 0.95:
                        p_moves = rules.legal_pawn_moves(sim_state)
                        if p_moves:
                            best_d = 999
                            best_pm: list[PawnMove] = []
                            for pm in p_moves:
                                d = d_curr[pm.to[0] * BOARD_SIZE + pm.to[1]]
                                if d == -1:
                                    d = 99
                                if d < best_d:
                                    best_d = d
                                    best_pm = [pm]
                                elif d == best_d:
                                    best_pm.append(pm)
                            step: Move | None = self._rng.choice(best_pm)
                        else:
                            c_moves = _moves.candidate_moves(sim_state)
                            step = self._rng.choice(c_moves) if c_moves else None
                    else:
                        c_moves = _moves.candidate_moves(sim_state)
                        step = self._rng.choice(c_moves) if c_moves else None
                else:  # "random"
                    c_moves = _moves.candidate_moves(sim_state)
                    step = self._rng.choice(c_moves) if c_moves else None

                if step is None:
                    break
                if isinstance(step, WallMove):
                    d0 = None
                    d1 = None
                sim_state = sim_state.apply(step)

            # Rollout result
            if sim_state.is_terminal():
                result_root = 1.0 if sim_state.winner() == root_player else 0.0
            else:
                if d0 is None or d1 is None:
                    d0 = _compute_goal_dist(sim_state, 0)
                    d1 = _compute_goal_dist(sim_state, 1)
                dist0 = d0[sim_state.pawns[0][0] * BOARD_SIZE + sim_state.pawns[0][1]]
                dist1 = d1[sim_state.pawns[1][0] * BOARD_SIZE + sim_state.pawns[1][1]]
                if dist0 == -1:
                    dist0 = 99
                if dist1 == -1:
                    dist1 = 99
                d_me = dist0 if root_player == 0 else dist1
                d_opp = dist1 if root_player == 0 else dist0
                result_root = 0.5 + 0.5 * math.tanh((d_opp - d_me) / 4.0)

            # 4. Back-propagation
            node: _MCTSNode | None = curr
            while node is not None:
                node.visits += 1
                if node.parent is not None:
                    if node.mover == root_player:
                        node.value += result_root
                    else:
                        node.value += (1.0 - result_root)
                node = node.parent

        # If an immediate winning move exists among root children, prioritize it
        immediate_win = None
        for child in root.children:
            if child.state.is_terminal() and child.state.winner() == root_player:
                immediate_win = child
                break

        if immediate_win is not None:
            best_child = immediate_win
            chosen = best_child.move  # type: ignore[assignment]
            eval_val = 1.0
        elif not root.children:
            chosen = self._rng.choice(candidates)
            eval_val = 0.5
        else:
            max_visits = -1
            best_children: list[_MCTSNode] = []
            for child in root.children:
                if child.visits > max_visits:
                    max_visits = child.visits
                    best_children = [child]
                elif child.visits == max_visits:
                    best_children.append(child)

            best_child = self._rng.choice(best_children)
            chosen = best_child.move  # type: ignore[assignment]
            eval_val = (best_child.value / best_child.visits) if best_child.visits > 0 else 0.5

        self.last_stats = {
            "nodes": total_nodes,
            "time_s": time.perf_counter() - t0,
            "eval": float(eval_val) if eval_val is not None else None,
            "depth": max_depth,
            "iterations": actual_iterations,
        }
        return chosen
