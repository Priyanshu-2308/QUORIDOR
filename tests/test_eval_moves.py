"""Tests for quoridor/eval.py and quoridor/moves.py (owner: Siddhesh)."""
from __future__ import annotations

import pytest

from quoridor.eval import WIN_SCORE, evaluate
from quoridor.moves import candidate_moves, candidate_walls
from quoridor.rules import is_wall_legal
from quoridor.state import GameState
from quoridor.types import PawnMove, WallMove


def _initial() -> GameState:
    return GameState.initial()


class TestEvaluate:
    def test_symmetric_initial(self):
        state = _initial()
        assert evaluate(state, 0) == 0.0
        assert evaluate(state, 1) == 0.0

    def test_symmetry_identity(self):
        state = _initial()
        assert evaluate(state, 0) == -evaluate(state, 1)

    def test_closer_player_scores_better(self):
        from dataclasses import replace
        state = _initial()
        state_p0_close = replace(state, pawns=((1, 4), (0, 4)))
        assert evaluate(state_p0_close, 0) > evaluate(state, 0)

    def test_win_terminal_positive(self):
        from dataclasses import replace
        state = replace(_initial(), pawns=((0, 4), (8, 4)))
        assert evaluate(state, 0) == WIN_SCORE
        assert evaluate(state, 1) == -WIN_SCORE

    def test_loss_terminal_negative(self):
        from dataclasses import replace
        state = replace(_initial(), pawns=((2, 4), (8, 4)))
        assert evaluate(state, 1) == WIN_SCORE
        assert evaluate(state, 0) == -WIN_SCORE


class TestCandidateWalls:
    def test_anchor_initial(self):
        walls = candidate_walls(_initial())
        assert len(walls) == 16, f"expected 16, got {len(walls)}"

    def test_empty_when_no_walls_left(self):
        from dataclasses import replace
        state = replace(_initial(), walls_left=(0, 10))
        assert candidate_walls(state) == []

    def test_all_returned_walls_are_legal(self):
        state = _initial()
        for w in candidate_walls(state):
            assert is_wall_legal(state, w)

    def test_deterministic(self):
        state = _initial()
        assert candidate_walls(state) == candidate_walls(state)

    def test_no_duplicates(self):
        walls = candidate_walls(_initial())
        assert len(walls) == len(set(walls))


class TestCandidateMoves:
    def test_anchor_initial(self):
        moves = candidate_moves(_initial())
        assert len(moves) == 19, f"expected 19, got {len(moves)}"

    def test_pawn_moves_first(self):
        moves = candidate_moves(_initial())
        seen_wall = False
        for m in moves:
            if isinstance(m, WallMove):
                seen_wall = True
            if seen_wall:
                assert isinstance(m, WallMove)