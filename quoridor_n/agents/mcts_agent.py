"""Monte Carlo Tree Search (MCTS) for four-player and two-player Quoridor."""
from __future__ import annotations

import math
import random
import time
from typing import Any

from .base import Agent, default_stats
from .. import moves as move_gen, pathfinding, rules
from ..state import GameState
from ..types import Move, PawnMove


class MCTSNode:
    """A search tree node in the multi-player MCTS tree."""

    __slots__ = (
        "state",
        "parent",
        "move_from_parent",
        "mover",
        "player_to_move",
        "children",
        "unexpanded_moves",
        "visits",
        "total_rewards",
    )

    def __init__(
        self,
        state: GameState,
        parent: MCTSNode | None = None,
        move_from_parent: Move | None = None,
        mover: int | None = None,
        unexpanded_moves: list[Move] | None = None,
    ):
        self.state = state
        self.parent = parent
        self.move_from_parent = move_from_parent
        self.mover = mover
        self.player_to_move = state.current
        self.children: dict[Move, MCTSNode] = {}
        self.unexpanded_moves = unexpanded_moves if unexpanded_moves is not None else []
        self.visits = 0
        self.total_rewards: dict[int, float] = {p: 0.0 for p in state.players}

    def is_fully_expanded(self) -> bool:
        return len(self.unexpanded_moves) == 0

    def is_terminal(self) -> bool:
        return self.state.is_terminal()


class MCTSAgent(Agent):
    """Four-player MCTS with vector payoff backpropagation and UCT selection."""

    def __init__(
        self,
        iterations: int = 500,
        c: float = 1.4,
        rollout_depth: int = 60,
        rollout_policy: str = "path_biased",
        rollout_greedy_share: float = 0.95,
        cutoff_scoring: str = "vs_mean",
        use_wall_pruning: bool = True,
        wall_target: str = "all",
        seed: int | None = None,
    ):
        super().__init__(name="mcts")
        self.iterations = iterations
        self.c = c
        self.rollout_depth = rollout_depth
        self.rollout_policy = rollout_policy
        self.rollout_greedy_share = rollout_greedy_share
        self.cutoff_scoring = cutoff_scoring
        self.use_wall_pruning = use_wall_pruning
        self.wall_target = wall_target
        self.rng = random.Random(seed)

    def _get_candidate_moves(self, state: GameState) -> list[Move]:
        if self.use_wall_pruning:
            moves = move_gen.candidate_moves(state, target=self.wall_target)
            if not moves:
                moves = rules.legal_moves(state)
        else:
            moves = rules.legal_moves(state)
        return moves

    def choose_move(self, state: GameState) -> Move:
        t0 = time.perf_counter()
        root_player = state.current

        # 1. Immediate Win Check
        for m in rules.legal_pawn_moves(state):
            nxt = state.apply(m)
            if nxt.winner() == root_player:
                self.last_stats = default_stats()
                self.last_stats["nodes"] = 1
                self.last_stats["time_s"] = time.perf_counter() - t0
                self.last_stats["eval"] = 1.0
                self.last_stats["iterations"] = self.iterations
                self.last_stats["depth"] = 1
                return m

        root_moves = self._get_candidate_moves(state)
        self.rng.shuffle(root_moves)
        root = MCTSNode(state=state, unexpanded_moves=root_moves)

        max_depth_reached = 0

        for _ in range(self.iterations):
            node = root
            depth = 0

            # 1. Selection
            while node.is_fully_expanded() and not node.is_terminal():
                node = self._select_best_child(node)
                depth += 1

            if depth > max_depth_reached:
                max_depth_reached = depth

            # 2. Expansion
            if not node.is_terminal() and node.unexpanded_moves:
                move = node.unexpanded_moves.pop()
                next_state = node.state.apply(move)
                next_moves = self._get_candidate_moves(next_state)
                self.rng.shuffle(next_moves)
                child = MCTSNode(
                    state=next_state,
                    parent=node,
                    move_from_parent=move,
                    mover=node.player_to_move,
                    unexpanded_moves=next_moves,
                )
                node.children[move] = child
                node = child
                depth += 1
                if depth > max_depth_reached:
                    max_depth_reached = depth

            # 3. Simulation (Rollout)
            rewards = self._simulate(node.state)

            # 4. Backpropagation
            curr_node: MCTSNode | None = node
            while curr_node is not None:
                curr_node.visits += 1
                for p, val in rewards.items():
                    curr_node.total_rewards[p] += val
                curr_node = curr_node.parent

        if not root.children:
            chosen = self.rng.choice(rules.legal_moves(state))
            best_eval = 0.0
        else:
            # Pick the most-visited root child
            best_move, best_child = max(root.children.items(), key=lambda item: item[1].visits)
            chosen = best_move
            best_eval = (
                best_child.total_rewards[root_player] / best_child.visits
                if best_child.visits > 0
                else 0.0
            )

        self.last_stats = default_stats()
        self.last_stats["nodes"] = sum(child.visits for child in root.children.values())
        self.last_stats["time_s"] = time.perf_counter() - t0
        self.last_stats["eval"] = best_eval
        self.last_stats["iterations"] = self.iterations
        self.last_stats["depth"] = max_depth_reached
        return chosen

    def _select_best_child(self, parent: MCTSNode) -> MCTSNode:
        """Select child maximizing UCT from perspective of player_to_move at parent."""
        mover = parent.player_to_move
        log_parent = math.log(parent.visits) if parent.visits > 0 else 0.0

        best_score = -float("inf")
        best_child: MCTSNode | None = None

        for child in parent.children.values():
            if child.visits == 0:
                return child
            exploitation = child.total_rewards[mover] / child.visits
            exploration = self.c * math.sqrt(log_parent / child.visits)
            score = exploitation + exploration
            if score > best_score:
                best_score = score
                best_child = child

        assert best_child is not None
        return best_child

    def _simulate(self, state: GameState) -> dict[int, float]:
        """Fast rollout to terminal state or rollout depth limit."""
        sim_state = state
        steps = 0

        while not sim_state.is_terminal() and steps < self.rollout_depth:
            curr = sim_state.current

            if (
                self.rollout_policy == "path_biased"
                and self.rng.random() < self.rollout_greedy_share
            ):
                # Greedy path step
                path = pathfinding.shortest_path(sim_state, curr)
                step_done = False
                if path is not None and len(path) >= 2:
                    direct_step = PawnMove(to=path[1])
                    if rules.is_legal(sim_state, direct_step):
                        sim_state = sim_state.apply(direct_step)
                        step_done = True
                if not step_done:
                    # Pick legal pawn move minimizing distance
                    pawn_moves = rules.legal_pawn_moves(sim_state)
                    if pawn_moves:
                        best_pm = min(
                            pawn_moves,
                            key=lambda pm: (
                                pathfinding.shortest_path_length(sim_state.apply(pm), curr)
                                or 99
                            ),
                        )
                        sim_state = sim_state.apply(best_pm)
                        step_done = True

                if not step_done:
                    avail = rules.legal_moves(sim_state)
                    if not avail:
                        break
                    sim_state = sim_state.apply(self.rng.choice(avail))
            else:
                # Random rollout policy
                avail = rules.legal_moves(sim_state)
                if not avail:
                    break
                sim_state = sim_state.apply(self.rng.choice(avail))

            steps += 1

        # Evaluate outcome
        w = sim_state.winner()
        if w is not None:
            return {p: 1.0 if p == w else 0.0 for p in sim_state.players}

        # Non-terminal cutoff scoring
        dists = {p: pathfinding.shortest_path_length(sim_state, p) or 99 for p in sim_state.players}
        rewards: dict[int, float] = {}

        for p in sim_state.players:
            own_d = dists[p]
            opp_d = [dists[o] for o in sim_state.players if o != p]
            if self.cutoff_scoring == "vs_leader":
                benchmark_d = min(opp_d)
            else:  # "vs_mean"
                benchmark_d = sum(opp_d) / len(opp_d)

            # Map difference to [0.0, 1.0] using tanh
            diff = benchmark_d - own_d
            score = 0.5 + 0.5 * math.tanh(diff / 4.0)
            rewards[p] = max(0.0, min(1.0, score))

        return rewards
