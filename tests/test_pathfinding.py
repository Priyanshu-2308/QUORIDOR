"""Tests for quoridor.pathfinding."""
import pytest

from quoridor.constants import START
from quoridor.pathfinding import (distances, has_path, shortest_path,
                                  shortest_path_length)
from quoridor.state import GameState
from quoridor.types import WallMove


def test_initial_state_paths():
    """Initial state: both players have shortest path of length 8 in straight lines."""
    s = GameState.initial()

    expected_p0 = [(r, 4) for r in range(8, -1, -1)]
    assert shortest_path(s, 0) == expected_p0
    assert shortest_path_length(s, 0) == 8
    assert has_path(s, 0) is True

    expected_p1 = [(r, 4) for r in range(0, 9)]
    assert shortest_path(s, 1) == expected_p1
    assert shortest_path_length(s, 1) == 8
    assert has_path(s, 1) is True

    assert distances(s) == (8, 8)


def test_wall_lengthens_path():
    """A horizontal wall directly ahead of player 0 lengthens the path from 8 to 9."""
    s = GameState.initial()
    s_wall = s.apply(WallMove(6, 4, "H"))

    assert shortest_path_length(s_wall, 0) == 9
    path0 = shortest_path(s_wall, 0)
    assert path0 is not None
    assert len(path0) == 10
    assert path0[0] == (8, 4)
    assert path0[-1][0] == 0
    assert has_path(s_wall, 0) is True

    assert shortest_path_length(s_wall, 1) == 9


def test_pawn_already_on_goal_row():
    """Pawn already on its goal row returns length 0, [pawn], and has_path == True."""
    s0 = GameState(
        pawns=((0, 4), (5, 5)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert shortest_path(s0, 0) == [(0, 4)]
    assert shortest_path_length(s0, 0) == 0
    assert has_path(s0, 0) is True

    s1 = GameState(
        pawns=((4, 4), (8, 2)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=1,
    )
    assert shortest_path(s1, 1) == [(8, 2)]
    assert shortest_path_length(s1, 1) == 0
    assert has_path(s1, 1) is True


def test_unreachable_sealed_region():
    """A position with no path returns None for shortest_path and False for has_path."""
    s_sealed = GameState(
        pawns=((8, 0), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(7, 0)]),
        v_walls=frozenset([(7, 0)]),
        current=0,
    )
    assert shortest_path(s_sealed, 0) is None
    assert shortest_path_length(s_sealed, 0) is None
    assert has_path(s_sealed, 0) is False

    assert has_path(s_sealed, 1) is True
    assert shortest_path_length(s_sealed, 1) == 8
    assert distances(s_sealed) == (None, 8)


def test_opponent_pawn_does_not_affect_pathfinding():
    """Pathfinding ignores the opponent's pawn; only walls block paths."""
    s_opp_in_path = GameState(
        pawns=((8, 4), (7, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    expected_p0 = [(r, 4) for r in range(8, -1, -1)]
    assert shortest_path(s_opp_in_path, 0) == expected_p0
    assert shortest_path_length(s_opp_in_path, 0) == 8
    assert has_path(s_opp_in_path, 0) is True