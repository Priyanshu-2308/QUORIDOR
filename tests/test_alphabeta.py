"""Tests for AlphaBetaAgent."""
from __future__ import annotations

import pytest

from quoridor.agents.alphabeta_agent import AlphaBetaAgent
from quoridor.agents.greedy_agent import GreedyAgent
from quoridor.agents.random_agent import RandomAgent
from quoridor.runner import play_game
from quoridor.rules import is_legal
from quoridor.state import GameState
from quoridor.types import PawnMove


def _initial() -> GameState:
    return GameState.initial()


class TestAlphaBetaLegality:
    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 42])
    def test_always_returns_legal_move(self, seed: int):
        agent = AlphaBetaAgent(depth=2, seed=seed)
        state = _initial()
        # Test across successive plies
        for _ in range(10):
            if state.is_terminal():
                break
            move = agent.choose_move(state)
            assert is_legal(state, move)
            state = state.apply(move)


class TestAlphaBetaImmediateWin:
    def test_takes_immediate_win_player_0(self):
        # Player 0 at (1, 4), can step to (0, 4) to win immediately
        state = GameState(
            pawns=((1, 4), (0, 0)),
            walls_left=(10, 10),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=0,
            turn_count=10,
        )
        agent = AlphaBetaAgent(depth=2, seed=42)
        move = agent.choose_move(state)
        assert move == PawnMove(to=(0, 4))

    def test_takes_immediate_win_player_1(self):
        # Player 1 at (7, 4), can step to (8, 4) to win immediately
        state = GameState(
            pawns=((8, 8), (7, 4)),
            walls_left=(10, 10),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=1,
            turn_count=11,
        )
        agent = AlphaBetaAgent(depth=2, seed=42)
        move = agent.choose_move(state)
        assert move == PawnMove(to=(8, 4))


class TestAlphaBetaStats:
    @pytest.mark.parametrize("d", [1, 2])
    def test_depth_1_and_2_fill_all_stats(self, d: int):
        agent = AlphaBetaAgent(depth=d, seed=42)
        state = _initial()
        move = agent.choose_move(state)
        assert is_legal(state, move)

        stats = agent.last_stats
        required_keys = {"nodes", "time_s", "eval", "depth", "iterations", "tt_hits", "cutoffs"}
        assert required_keys.issubset(stats.keys())

        assert isinstance(stats["nodes"], int) and stats["nodes"] > 0
        assert isinstance(stats["time_s"], float) and stats["time_s"] >= 0.0
        assert isinstance(stats["eval"], float)
        assert stats["depth"] == d
        assert stats["iterations"] is None
        assert isinstance(stats["tt_hits"], int)
        assert isinstance(stats["cutoffs"], int)


class TestAlphaBetaOrderingAndTT:
    def test_ordering_and_tt_efficiency(self):
        state = _initial()
        ab_on = AlphaBetaAgent(depth=3, use_move_ordering=True, use_tt=True, seed=42)
        m_on = ab_on.choose_move(state)
        assert is_legal(state, m_on)

        ab_off = AlphaBetaAgent(depth=3, use_move_ordering=False, use_tt=False, seed=42)
        m_off = ab_off.choose_move(state)
        assert is_legal(state, m_off)

        # Node count with both optimizations ON must be <= node count with both OFF
        assert ab_on.last_stats["nodes"] <= ab_off.last_stats["nodes"]


class TestAlphaBetaReproducibility:
    def test_reproducibility_same_seed(self):
        state = _initial()
        agent1 = AlphaBetaAgent(depth=2, seed=123)
        move1 = agent1.choose_move(state)
        stats1 = dict(agent1.last_stats)

        agent2 = AlphaBetaAgent(depth=2, seed=123)
        move2 = agent2.choose_move(state)
        stats2 = dict(agent2.last_stats)

        assert move1 == move2
        assert stats1["eval"] == stats2["eval"]
        assert stats1["nodes"] == stats2["nodes"]


class TestAlphaBetaBeatsGreedy:
    def test_beats_greedy_at_least_8_of_10(self):
        ab_wins = 0
        for i in range(10):
            ab = AlphaBetaAgent(depth=2, seed=i)
            gr = GreedyAgent(seed=i)
            if i % 2 == 0:
                result = play_game(ab, gr, max_turns=200)
                if result.winner == 0:
                    ab_wins += 1
            else:
                result = play_game(gr, ab, max_turns=200)
                if result.winner == 1:
                    ab_wins += 1

        assert ab_wins >= 8, f"AlphaBeta only won {ab_wins}/10 games against GreedyAgent"


class TestAlphaBetaEdgeCases:
    def test_terminal_state_raises_value_error(self):
        # A state where player 0 has already won
        state = GameState(
            pawns=((0, 4), (5, 4)),
            walls_left=(10, 10),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=0,
            turn_count=16,
        )
        assert state.is_terminal()
        agent = AlphaBetaAgent(depth=2)
        with pytest.raises(ValueError, match="already won"):
            agent.choose_move(state)

    def test_iterative_deepening(self):
        agent = AlphaBetaAgent(depth=3, iterative_deepening=True, time_limit_s=1.0, seed=42)
        state = _initial()
        move = agent.choose_move(state)
        assert is_legal(state, move)
        assert agent.last_stats["depth"] >= 1
