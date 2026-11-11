"""Tests for quoridor.types and quoridor.state."""
import pytest

from quoridor.state import GameState
from quoridor.types import (PawnMove, WallMove, move_from_dict, move_to_dict,
                            move_to_str)


def state_with(**kw):
    base = GameState.initial()
    d = dict(pawns=base.pawns, walls_left=base.walls_left, h_walls=base.h_walls,
             v_walls=base.v_walls, current=base.current, turn_count=base.turn_count)
    d.update(kw)
    return GameState(**d)


def test_initial_state():
    s = GameState.initial()
    assert s.pawns == ((8, 4), (0, 4))
    assert s.walls_left == (10, 10)
    assert s.h_walls == frozenset() and s.v_walls == frozenset()
    assert s.current == 0 and s.turn_count == 0
    assert s.winner() is None and not s.is_terminal()


def test_apply_pawn_move():
    s = GameState.initial()
    t = s.apply(PawnMove((7, 4)))
    assert t.pawns == ((7, 4), (0, 4))
    assert t.current == 1 and t.turn_count == 1
    assert t.walls_left == (10, 10)
    assert s.pawns == ((8, 4), (0, 4)) and s.current == 0 and s.turn_count == 0
    u = t.apply(PawnMove((1, 4)))
    assert u.pawns == ((7, 4), (1, 4)) and u.current == 0 and u.turn_count == 2


def test_apply_h_wall():
    s = GameState.initial()
    t = s.apply(WallMove(3, 2, "H"))
    assert t.h_walls == frozenset({(3, 2)}) and t.v_walls == frozenset()
    assert t.walls_left == (9, 10) and t.current == 1 and t.turn_count == 1
    assert s.h_walls == frozenset() and s.walls_left == (10, 10)


def test_apply_v_wall_decrements_right_player():
    s = GameState.initial().apply(PawnMove((7, 4)))  # now player 1 to move
    t = s.apply(WallMove(3, 2, "V"))
    assert t.v_walls == frozenset({(3, 2)}) and t.h_walls == frozenset()
    assert t.walls_left == (10, 9) and t.current == 0
    assert s.v_walls == frozenset() and s.walls_left == (10, 10)


def test_is_blocked_h_wall():
    s = state_with(h_walls=frozenset({(3, 2)}))
    assert s.is_blocked((3, 2), (4, 2))
    assert s.is_blocked((3, 3), (4, 3))
    assert not s.is_blocked((3, 1), (4, 1))
    assert not s.is_blocked((3, 4), (4, 4))
    # horizontal movement across the wall's row is not affected
    assert not s.is_blocked((3, 2), (3, 3))


def test_is_blocked_v_wall():
    s = state_with(v_walls=frozenset({(3, 2)}))
    assert s.is_blocked((3, 2), (3, 3))
    assert s.is_blocked((4, 2), (4, 3))
    assert not s.is_blocked((2, 2), (2, 3))
    assert not s.is_blocked((5, 2), (5, 3))
    assert not s.is_blocked((3, 2), (4, 2))


def test_is_blocked_symmetric():
    s = state_with(h_walls=frozenset({(3, 2)}), v_walls=frozenset({(5, 5)}))
    for r in range(9):
        for c in range(9):
            for dr, dc in ((1, 0), (0, 1)):
                a, b = (r, c), (r + dr, c + dc)
                if b[0] < 9 and b[1] < 9:
                    assert s.is_blocked(a, b) == s.is_blocked(b, a)


def test_is_blocked_off_board():
    s = GameState.initial()
    assert s.is_blocked((0, 0), (-1, 0))
    assert s.is_blocked((0, 0), (0, -1))
    assert s.is_blocked((8, 8), (9, 8))
    assert s.is_blocked((8, 8), (8, 9))
    assert s.is_blocked((-1, 0), (0, 0))
    assert not s.is_blocked((4, 4), (4, 5))


def test_winner():
    assert state_with(pawns=((0, 3), (4, 4))).winner() == 0
    assert state_with(pawns=((4, 4), (8, 1))).winner() == 1
    assert state_with(pawns=((4, 4), (5, 4))).winner() is None
    assert state_with(pawns=((0, 3), (4, 4))).is_terminal()
    assert not GameState.initial().is_terminal()


def test_to_dict_from_dict_roundtrip():
    s = (GameState.initial().apply(WallMove(5, 1, "H")).apply(WallMove(3, 2, "V"))
         .apply(PawnMove((7, 4))))
    d = s.to_dict()
    assert d["winner"] is None
    assert GameState.from_dict(d) == s
    d["winner"] = 1  # ignored by from_dict
    assert GameState.from_dict(d) == s


def test_to_dict_initial_and_sorted():
    d = GameState.initial().to_dict()
    assert d == {"pawns": [[8, 4], [0, 4]], "walls_left": [10, 10], "h_walls": [],
                 "v_walls": [], "current": 0, "turn_count": 0, "winner": None}
    s = state_with(h_walls=frozenset({(5, 1), (1, 6), (3, 2)}))
    assert s.to_dict()["h_walls"] == [[1, 6], [3, 2], [5, 1]]


def test_key_hashable_and_equal():
    a = GameState.initial().apply(WallMove(3, 2, "H"))
    b = GameState.initial().apply(WallMove(3, 2, "H"))
    assert a.key() == b.key()
    assert hash(a.key()) == hash(b.key())
    assert len({a.key(), b.key()}) == 1
    assert a.key() != GameState.initial().key()


def test_render_runs():
    s = GameState.initial().apply(WallMove(3, 2, "H")).apply(WallMove(1, 1, "V"))
    out = s.render()
    assert "0" in out and "1" in out and "-" in out and "|" in out


def test_legal_moves_delegates_to_rules():
    # rules is a stub until Rajnish lands; either way the call must reach quoridor.rules
    try:
        GameState.initial().legal_moves()
    except NotImplementedError:
        pass


def test_move_dict_roundtrip():
    for d in ({"type": "pawn", "to": [7, 4]},
              {"type": "wall", "r": 3, "c": 2, "o": "H"},
              {"type": "wall", "r": 0, "c": 7, "o": "V"}):
        assert move_to_dict(move_from_dict(d)) == d
    assert move_from_dict({"type": "pawn", "to": [7, 4]}) == PawnMove((7, 4))
    assert move_from_dict({"type": "wall", "r": 3, "c": 2, "o": "H"}) == WallMove(3, 2, "H")
    assert move_to_dict(PawnMove((7, 4))) == {"type": "pawn", "to": [7, 4]}


@pytest.mark.parametrize("bad", [
    {"type": "jump", "to": [1, 1]},
    {"type": "wall", "r": 1, "c": 1, "o": "X"},
    {"type": "wall", "r": 1, "c": 1},
    {"type": "wall", "c": 1, "o": "H"},
    {"type": "pawn"},
    {},
])
def test_move_from_dict_errors(bad):
    with pytest.raises(ValueError):
        move_from_dict(bad)


def test_move_to_str():
    assert move_to_str(PawnMove((7, 4))) == "P(7,4)"
    assert move_to_str(WallMove(3, 2, "H")) == "H(3,2)"
    assert move_to_str(WallMove(3, 2, "V")) == "V(3,2)"
