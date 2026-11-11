"""Tests for MCTSAgent (owner: Shivam / Priyanshu)."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import os
import pytest

from quoridor.agents.greedy_agent import GreedyAgent
from quoridor.agents.mcts_agent import MCTSAgent
from quoridor.agents.random_agent import RandomAgent
from quoridor.rules import is_legal
from quoridor.runner import play_game
from quoridor.state import GameState
from quoridor.types import PawnMove


def _initial() -> GameState:
    return GameState.initial()


def _run_one_random_game(i: int) -> bool:
    mcts = MCTSAgent(iterations=300, seed=i)
    rnd = RandomAgent(seed=i)
    if i % 2 == 0:
        res = play_game(mcts, rnd, max_turns=200)
        return res.winner == 0
    else:
        res = play_game(rnd, mcts, max_turns=200)
        return res.winner == 1


def _run_one_greedy_game(i: int) -> bool:
    mcts = MCTSAgent(iterations=300, seed=i)
    greedy = GreedyAgent(seed=i)
    if i % 2 == 0:
        res = play_game(mcts, greedy, max_turns=200)
        return res.winner == 0
    else:
        res = play_game(greedy, mcts, max_turns=200)
        return res.winner == 1


class TestMCTSLegality:
    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 42])
    def test_always_returns_legal_move(self, seed: int):
        agent = MCTSAgent(iterations=50, seed=seed)
        state = _initial()
        for _ in range(5):
            if state.is_terminal():
                break
            move = agent.choose_move(state)
            assert is_legal(state, move)
            state = state.apply(move)


class TestMCTSImmediateWin:
    def test_takes_immediate_win_player_0(self):
        state = GameState(
            pawns=((1, 4), (0, 0)),
            walls_left=(10, 10),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=0,
            turn_count=10,
        )
        agent = MCTSAgent(iterations=200, seed=42)
        move = agent.choose_move(state)
        assert move == PawnMove(to=(0, 4))

    def test_takes_immediate_win_player_1(self):
        state = GameState(
            pawns=((8, 8), (7, 4)),
            walls_left=(10, 10),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=1,
            turn_count=11,
        )
        agent = MCTSAgent(iterations=200, seed=42)
        move = agent.choose_move(state)
        assert move == PawnMove(to=(8, 4))


class TestMCTSStats:
    def test_stats_keys_and_iterations_count(self):
        iterations = 100
        agent = MCTSAgent(iterations=iterations, seed=42)
        state = _initial()
        move = agent.choose_move(state)
        assert is_legal(state, move)

        stats = agent.last_stats
        required_keys = {"nodes", "time_s", "eval", "depth", "iterations"}
        assert required_keys.issubset(stats.keys())
        assert isinstance(stats["nodes"], int) and stats["nodes"] > 0
        assert isinstance(stats["time_s"], float) and stats["time_s"] >= 0.0
        assert isinstance(stats["eval"], float) and 0.0 <= stats["eval"] <= 1.0
        assert isinstance(stats["depth"], int) and stats["depth"] >= 1
        assert stats["iterations"] == iterations


class TestMCTSReproducibility:
    def test_reproducibility_same_seed(self):
        state = _initial()
        agent1 = MCTSAgent(iterations=100, seed=123)
        move1 = agent1.choose_move(state)
        stats1 = dict(agent1.last_stats)

        agent2 = MCTSAgent(iterations=100, seed=123)
        move2 = agent2.choose_move(state)
        stats2 = dict(agent2.last_stats)

        assert move1 == move2
        assert stats1["nodes"] == stats2["nodes"]
        assert stats1["eval"] == stats2["eval"]


class TestMCTSBeatsBaselines:
    def test_beats_random_at_least_9_of_10(self):
        workers = min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_run_one_random_game, range(10)))
        wins = sum(results)
        assert wins >= 9, f"MCTSAgent won {wins}/10 against RandomAgent"

    def test_beats_greedy_at_least_6_of_10(self):
        workers = min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_run_one_greedy_game, range(10)))
        wins = sum(results)
        assert wins >= 6, f"MCTSAgent won {wins}/10 against GreedyAgent"
