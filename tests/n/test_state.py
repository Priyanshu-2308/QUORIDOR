"""Unit tests for quoridor_n GameState."""
import pytest
from quoridor_n.constants import START
from quoridor_n.state import GameState
from quoridor_n.types import PawnMove, WallMove


def test_initial_4p_state():
    state = GameState.initial(num_players=4)
    assert state.num_players == 4
    assert state.players == (0, 1, 2, 3)
    assert state.pawns == (START[0], START[1], START[2], START[3])
    assert state.walls_left == (5, 5, 5, 5)
    assert len(state.h_walls) == 0
    assert len(state.v_walls) == 0
    assert state.current == 0
    assert state.turn_count == 0
    assert not state.is_terminal()
    assert state.winner() is None


def test_initial_2p_state():
    state = GameState.initial(num_players=2)
    assert state.num_players == 2
    assert state.players == (0, 2)
    assert state.pawns == (START[0], START[2])
    assert state.walls_left == (10, 10)
    assert state.current == 0
    assert state.turn_count == 0


def test_immutability_and_apply():
    state = GameState.initial(num_players=4)
    m = PawnMove(to=(7, 4))
    nxt = state.apply(m)

    assert state.pawns[0] == (8, 4)
    assert state.current == 0
    assert state.turn_count == 0

    assert nxt.pawns[0] == (7, 4)
    assert nxt.current == 1  # Clockwise rotation: 0 -> 1 -> 2 -> 3
    assert nxt.turn_count == 1


def test_wall_apply_and_inventory():
    state = GameState.initial(num_players=4)
    wm = WallMove(r=3, c=3, o="H")
    nxt = state.apply(wm)

    assert state.walls(0) == 5
    assert len(state.h_walls) == 0

    assert nxt.walls(0) == 4
    assert (3, 3) in nxt.h_walls
    assert nxt.current == 1


def test_turn_rotation_4p():
    state = GameState.initial(num_players=4)
    # Rotate 4 moves
    s1 = state.apply(PawnMove((7, 4)))  # P0
    assert s1.current == 1
    s2 = s1.apply(PawnMove((4, 1)))     # P1
    assert s2.current == 2
    s3 = s2.apply(PawnMove((1, 4)))     # P2
    assert s3.current == 3
    s4 = s3.apply(PawnMove((4, 7)))     # P3
    assert s4.current == 0


def test_turn_rotation_2p():
    state = GameState.initial(num_players=2)
    s1 = state.apply(PawnMove((7, 4)))
    assert s1.current == 2
    s2 = s1.apply(PawnMove((1, 4)))
    assert s2.current == 0


def test_key_equality():
    s1 = GameState.initial(num_players=4)
    s2 = GameState.initial(num_players=4)
    assert s1.key() == s2.key()
    assert hash(s1.key()) == hash(s2.key())

    m = PawnMove((7, 4))
    s3 = s1.apply(m)
    assert s1.key() != s3.key()


def test_serialization_round_trip():
    s = GameState.initial(num_players=4)
    s = s.apply(WallMove(2, 2, "H"))
    s = s.apply(PawnMove((4, 1)))

    d = s.to_dict()
    reconstructed = GameState.from_dict(d)

    assert reconstructed.key() == s.key()
    assert reconstructed.num_players == s.num_players
    assert reconstructed.current == s.current
    assert reconstructed.turn_count == s.turn_count
    assert reconstructed.pawns == s.pawns
    assert reconstructed.walls_left == s.walls_left
    assert reconstructed.h_walls == s.h_walls
    assert reconstructed.v_walls == s.v_walls
