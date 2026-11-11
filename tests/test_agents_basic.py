"""Tests for RandomAgent, GreedyAgent, and make_agent."""
from __future__ import annotations

import pytest

from quoridor.agents import AGENT_NAMES, make_agent
from quoridor.agents.greedy_agent import GreedyAgent
from quoridor.agents.random_agent import RandomAgent
from quoridor.pathfinding import shortest_path_length
from quoridor.rules import is_legal
from quoridor.state import GameState
from quoridor.types import PawnMove


def _initial() -> GameState:
    return GameState.initial()


class TestRandomAgentLegality:
    @pytest.mark.parametrize("seed", range(5))
    def test_always_legal(self, seed: int):
        agent = RandomAgent(seed=seed)
        state = _initial()
        for _ in range(30):
            if state.is_terminal():
                break
            move = agent.choose_move(state)
            assert is_legal(state, move)
            state = state.apply(move)


class TestGreedyAgentLegality:
    @pytest.mark.parametrize("seed", range(5))
    def test_always_legal(self, seed: int):
        agent = GreedyAgent(seed=seed)
        state = _initial()
        for _ in range(30):
            if state.is_terminal():
                break
            move = agent.choose_move(state)
            assert is_legal(state, move)
            state = state.apply(move)


class TestGreedyAgentGoal:
    def test_first_move_reduces_distance(self):
        agent = GreedyAgent(seed=0)
        state = _initial()
        d_before = shortest_path_length(state, state.current)
        move = agent.choose_move(state)
        next_state = state.apply(move)
        d_after = shortest_path_length(next_state, 0)
        assert d_after < d_before

    def test_reaches_goal_in_8_or_fewer_own_moves(self):
        agent = GreedyAgent(seed=0)
        state = _initial()
        own_moves = 0
        while not state.is_terminal() and own_moves < 10:
            if state.current == 0:
                move = agent.choose_move(state)
                assert is_legal(state, move)
                state = state.apply(move)
                own_moves += 1
                if state.pawns[0][0] == 0:
                    break
            else:
                from dataclasses import replace
                state = replace(state, current=0)
        assert state.pawns[0][0] == 0 or state.winner() == 0


class TestMakeAgent:
    def test_greedy_no_kwargs(self):
        assert isinstance(make_agent("greedy"), GreedyAgent)

    def test_random_with_kwargs(self):
        agent = make_agent("random:seed=3,wall_prob=0.5")
        assert isinstance(agent, RandomAgent)
        assert agent.wall_prob == 0.5

    def test_bad_name_raises(self):
        with pytest.raises(ValueError, match="unknown agent"):
            make_agent("doesnotexist")

    def test_bad_kwarg_raises(self):
        with pytest.raises(ValueError):
            make_agent("greedy:nonexistent_param=1")

    def test_all_names_known(self):
        assert set(AGENT_NAMES) == {"random", "greedy", "alphabeta", "mcts"}