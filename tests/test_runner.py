"""Tests for quoridor/runner.py."""
from __future__ import annotations

import pytest

from quoridor.agents.greedy_agent import GreedyAgent
from quoridor.agents.random_agent import RandomAgent
from quoridor.runner import GameResult, play_game
from quoridor.state import GameState


def _initial() -> GameState:
    return GameState.initial()


class TestRunnerTermination:
    def test_game_terminates(self):
        result = play_game(RandomAgent(seed=42), GreedyAgent(seed=42))
        assert isinstance(result, GameResult)
        assert result.winner in (0, 1, None)
        assert result.turns > 0
        assert len(result.moves) == result.turns

    def test_max_turns_draw(self):
        result = play_game(RandomAgent(seed=1), RandomAgent(seed=2), max_turns=2)
        assert result.winner is None
        assert result.turns == 2

    def test_on_move_called_once_per_ply(self):
        calls = []
        def _cb(state_before, move, stats, player):
            calls.append((move, player))
        result = play_game(RandomAgent(seed=7), RandomAgent(seed=8),
                           max_turns=10, on_move=_cb)
        assert len(calls) == result.turns


class TestGreedyWinRate:
    def test_greedy_wins_majority_as_p0(self):
        wins = sum(
            1 for seed in range(10)
            if play_game(GreedyAgent(seed=seed), RandomAgent(seed=seed)).winner == 0
        )
        assert wins >= 8

    def test_greedy_wins_majority_as_p1(self):
        wins = sum(
            1 for seed in range(10)
            if play_game(RandomAgent(seed=seed), GreedyAgent(seed=seed)).winner == 1
        )
        assert wins >= 8


class TestIllegalMoveRaises:
    def test_illegal_move_raises_value_error(self):
        class BadAgent(RandomAgent):
            def choose_move(self, state):
                from quoridor.types import PawnMove
                return PawnMove(to=(99, 99))
        with pytest.raises(ValueError, match="illegal move"):
            play_game(BadAgent(seed=0), RandomAgent(seed=0))


class TestAgentStats:
    def test_agent_stats_keys_present(self):
        result = play_game(RandomAgent(seed=3), GreedyAgent(seed=4), max_turns=20)
        for s in result.agent_stats:
            assert "name" in s
            assert "moves" in s
            assert "total_nodes" in s
            assert "total_time_s" in s

    def test_agent_stats_moves_sum_to_turns(self):
        result = play_game(RandomAgent(seed=5), RandomAgent(seed=6), max_turns=20)
        assert sum(s["moves"] for s in result.agent_stats) == result.turns