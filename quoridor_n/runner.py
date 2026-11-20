"""Match execution and runner for dynamic Quoridor."""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .config import GameConfig
from .pathfinding import shortest_path_length
from .rules import is_legal, legal_moves
from .state import GameState
from .types import Move, PassMove, move_to_str


@dataclass
class GameResult:
    """Outcome of a played game."""
    config: GameConfig
    winner: int | None
    no_winner: bool
    ranks: dict[int, float]
    plies: int
    moves: list[Move]
    move_strings: list[str]
    pass_count: int
    agent_names: dict[int, str]
    agent_stats: dict[int, dict[str, Any]]
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "board_size": self.config.board_size,
            "num_players": self.config.num_players,
            "walls_per_player": self.config.walls_per_player,
            "max_turns": self.config.max_turns,
            "winner": self.winner,
            "no_winner": self.no_winner,
            "ranks": self.ranks,
            "plies": self.plies,
            "moves": self.move_strings,
            "pass_count": self.pass_count,
            "agent_names": self.agent_names,
            "agent_stats": self.agent_stats,
            "duration_s": self.duration_s,
        }


def compute_ranks(state: GameState) -> dict[int, float]:
    """Compute player ranks (1-based, lower is better; ties share average rank)."""
    players = state.config.players
    w = state.winner()

    if w is not None:
        ranks: dict[int, float] = {w: 1.0}
        remaining = [p for p in players if p != w]
        if not remaining:
            return ranks

        # Sort remaining by remaining path distance ascending
        scored = []
        for p in remaining:
            d = shortest_path_length(state, p)
            dist = 999 if d is None else d
            scored.append((dist, p))
        scored.sort(key=lambda item: item[0])

        # Assign ranks with ties averaged starting from position 2
        pos = 2
        i = 0
        while i < len(scored):
            j = i
            while j < len(scored) and scored[j][0] == scored[i][0]:
                j += 1
            # positions are pos, pos+1, ..., pos + (j - i) - 1
            avg_rank = (pos + pos + (j - i) - 1) / 2.0
            for k in range(i, j):
                ranks[scored[k][1]] = avg_rank
            pos += (j - i)
            i = j
        return ranks

    # No winner (e.g. max_turns reached)
    scored = []
    for p in players:
        d = shortest_path_length(state, p)
        dist = 999 if d is None else d
        scored.append((dist, p))
    scored.sort(key=lambda item: item[0])

    ranks = {}
    pos = 1
    i = 0
    while i < len(scored):
        j = i
        while j < len(scored) and scored[j][0] == scored[i][0]:
            j += 1
        avg_rank = (pos + pos + (j - i) - 1) / 2.0
        for k in range(i, j):
            ranks[scored[k][1]] = avg_rank
        pos += (j - i)
        i = j
    return ranks


def play_game(
    agents: dict[int, Any],
    config: GameConfig | None = None,
    initial_state: GameState | None = None,
) -> GameResult:
    """Play a complete game between specified agents."""
    t0 = time.perf_counter()
    if initial_state is not None:
        state = initial_state
        config = state.config
    else:
        if config is None:
            config = GameConfig()
        state = GameState.initial(config)

    for p in config.players:
        if p not in agents:
            raise ValueError(f"missing agent for player {p}")

    moves: list[Move] = []
    move_strings: list[str] = []
    agent_names = {p: getattr(agents[p], "name", agents[p].__class__.__name__) for p in config.players}
    agent_stats: dict[int, dict[str, Any]] = {
        p: {
            "moves_count": 0,
            "total_nodes": 0,
            "total_time_s": 0.0,
            "tt_hits": 0,
            "cutoffs": 0,
            "iterations": 0,
        }
        for p in config.players
    }

    while not state.is_terminal():
        curr = state.current
        agent = agents[curr]

        move = agent.choose_move(state)
        if not is_legal(state, move):
            # Fallback if agent returned illegal move
            valid = legal_moves(state)
            move = valid[0]

        moves.append(move)
        move_strings.append(move_to_str(move))

        # Accumulate search stats if provided by agent
        stats = getattr(agent, "last_stats", None)
        if isinstance(stats, dict):
            st = agent_stats[curr]
            st["moves_count"] += 1
            st["total_nodes"] += stats.get("nodes", 0)
            st["total_time_s"] += stats.get("time_s", 0.0)
            st["tt_hits"] += stats.get("tt_hits", 0)
            st["cutoffs"] += stats.get("cutoffs", 0)
            st["iterations"] += stats.get("iterations", 0)

        state = state.apply(move)

    w = state.winner()
    no_winner = w is None
    ranks = compute_ranks(state)
    duration = time.perf_counter() - t0

    return GameResult(
        config=config,
        winner=w,
        no_winner=no_winner,
        ranks=ranks,
        plies=state.turn_count,
        moves=moves,
        move_strings=move_strings,
        pass_count=state.pass_count,
        agent_names=agent_names,
        agent_stats=agent_stats,
        duration_s=duration,
    )
