"""Tests for quoridor.rules (owner: Rajnish)."""
import random
import pytest

from quoridor.constants import H, V
from quoridor.pathfinding import has_path
from quoridor.rules import (is_legal, is_wall_legal, legal_moves,
                            legal_pawn_moves, legal_wall_moves)
from quoridor.state import GameState
from quoridor.types import PawnMove, WallMove


def test_initial_state_moves():
    """Initial state: exactly 3 pawn moves, 128 legal walls, 131 legal moves."""
    s = GameState.initial()

    p_moves = legal_pawn_moves(s)
    assert len(p_moves) == 3
    assert [m.to for m in p_moves] == [(7, 4), (8, 3), (8, 5)]

    w_moves = legal_wall_moves(s)
    assert len(w_moves) == 128

    assert all(w.o == H for w in w_moves[:64])
    assert all(w.o == V for w in w_moves[64:])

    all_moves = legal_moves(s)
    assert len(all_moves) == 131
    assert all_moves[:3] == p_moves
    assert all_moves[3:] == w_moves

    for m in all_moves:
        assert is_legal(s, m) is True

    assert is_legal(s, PawnMove((0, 0))) is False
    assert is_legal(s, WallMove(-1, 0, H)) is False


def test_pawn_moves_plain_blocked_and_edges():
    """Pawn moves: orthogonal steps, blocked by walls, and blocked by board edges."""
    s_center = GameState(
        pawns=((4, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert [m.to for m in legal_pawn_moves(s_center)] == [
        (3, 4), (5, 4), (4, 3), (4, 5)
    ]

    s_wall = GameState(
        pawns=((4, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(3, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    assert [m.to for m in legal_pawn_moves(s_wall)] == [(5, 4), (4, 3), (4, 5)]

    s_corner = GameState(
        pawns=((8, 0), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert [m.to for m in legal_pawn_moves(s_corner)] == [(7, 0), (8, 1)]


def test_jumping_straight_jump():
    """Straight jump over opponent when cell behind is unblocked (both perspectives)."""

    s0 = GameState(
        pawns=((2, 4), (1, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves0 = legal_pawn_moves(s0)

    assert PawnMove((0, 4)) in moves0
    assert PawnMove((1, 3)) not in moves0
    assert PawnMove((1, 5)) not in moves0

    s1 = GameState(
        pawns=((7, 4), (6, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=1,
    )
    moves1 = legal_pawn_moves(s1)
    assert PawnMove((8, 4)) in moves1
    assert PawnMove((7, 3)) not in moves1
    assert PawnMove((7, 5)) not in moves1


def test_jumping_blocked_by_wall_between_pawns():
    """No jump and no plain step when a wall lies between mover and opponent."""
    s = GameState(
        pawns=((2, 4), (1, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(1, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(s)
    assert PawnMove((0, 4)) not in moves
    assert PawnMove((1, 4)) not in moves
    assert PawnMove((1, 3)) not in moves
    assert PawnMove((1, 5)) not in moves
    assert [m.to for m in moves] == [(3, 4), (2, 3), (2, 5)]


def test_jumping_diagonals_wall_behind_opponent():
    """Diagonals allowed when a wall is behind the opponent (both perspectives)."""
    s0 = GameState(
        pawns=((2, 4), (1, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(0, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    moves0 = legal_pawn_moves(s0)
    assert PawnMove((0, 4)) not in moves0
    assert PawnMove((1, 3)) in moves0
    assert PawnMove((1, 5)) in moves0
    assert [m.to for m in moves0] == [(1, 3), (1, 5), (3, 4), (2, 3), (2, 5)]
    s1 = GameState(
        pawns=((7, 4), (6, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(7, 4)]),
        v_walls=frozenset(),
        current=1,
    )
    moves1 = legal_pawn_moves(s1)
    assert PawnMove((8, 4)) not in moves1
    assert PawnMove((7, 3)) in moves1
    assert PawnMove((7, 5)) in moves1


def test_jumping_diagonals_opponent_at_board_edge():
    """Diagonals allowed when opponent is at the board edge (straight jump off-board)."""
    s0 = GameState(
        pawns=((1, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves0 = legal_pawn_moves(s0)
    assert PawnMove((0, 3)) in moves0
    assert PawnMove((0, 5)) in moves0
    assert [m.to for m in moves0] == [(0, 3), (0, 5), (2, 4), (1, 3), (1, 5)]
    s_left = GameState(
        pawns=((4, 1), (4, 0)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves_left = legal_pawn_moves(s_left)
    assert PawnMove((3, 0)) in moves_left
    assert PawnMove((5, 0)) in moves_left


def test_wall_legality_bounds_inventory_overlap_crossing():
    """Walls: bounds, 0 inventory, overlap, crossing, and legal placement."""
    s = GameState.initial()

    assert is_wall_legal(s, WallMove(-1, 0, H)) is False
    assert is_wall_legal(s, WallMove(8, 0, H)) is False
    assert is_wall_legal(s, WallMove(0, 8, V)) is False
    assert is_wall_legal(s, WallMove(0, 0, "X")) is False

    s_nowalls = GameState(
        pawns=((8, 4), (0, 4)),
        walls_left=(0, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert legal_wall_moves(s_nowalls) == []
    assert is_wall_legal(s_nowalls, WallMove(3, 2, H)) is False

    s_h = s.apply(WallMove(3, 2, H))

    assert is_wall_legal(s_h, WallMove(3, 1, H)) is False
    assert is_wall_legal(s_h, WallMove(3, 2, H)) is False
    assert is_wall_legal(s_h, WallMove(3, 3, H)) is False

    assert is_wall_legal(s_h, WallMove(3, 2, V)) is False

    assert is_wall_legal(s_h, WallMove(3, 0, H)) is True
    assert is_wall_legal(s_h, WallMove(3, 4, H)) is True

    s_v = s.apply(WallMove(3, 2, V))
    assert is_wall_legal(s_v, WallMove(2, 2, V)) is False
    assert is_wall_legal(s_v, WallMove(3, 2, V)) is False
    assert is_wall_legal(s_v, WallMove(4, 2, V)) is False
    assert is_wall_legal(s_v, WallMove(3, 2, H)) is False


def test_wall_sealing_gap_rejected():
    """Wall that would seal a player is rejected, while a lengthening wall is accepted."""
    h_walls = frozenset([(0, 0), (0, 2), (0, 4), (0, 6), (2, 0), (2, 2), (2, 4)])
    s = GameState(
        pawns=((8, 4), (0, 4)),
        walls_left=(5, 5),
        h_walls=h_walls,
        v_walls=frozenset(),
        current=0,
    )
    assert has_path(s, 0) and has_path(s, 1)

    closing_wall = WallMove(0, 7, V)
    assert is_wall_legal(s, closing_wall) is False

    lengthening_wall = WallMove(4, 4, H)
    assert is_wall_legal(s, lengthening_wall) is True


def test_is_legal_agrees_with_legal_moves_random_play():
    """is_legal agrees with legal_moves on random game positions across 200+ plies."""
    rng = random.Random(12345)
    total_plies = 0

    for _ in range(5):
        s = GameState.initial()
        for _ in range(50):
            if s.is_terminal():
                break
            moves = legal_moves(s)
            assert len(moves) > 0

            for m in moves:
                assert is_legal(s, m) is True

            assert is_legal(s, PawnMove((-1, -1))) is False
            assert is_legal(s, WallMove(10, 10, H)) is False

            m = rng.choice(moves)
            s = s.apply(m)
            total_plies += 1

    assert total_plies >= 200


def test_terminal_state_has_no_legal_moves():
    """A terminal state returns [] for legal_moves and False for is_legal."""
    s_won = GameState(
        pawns=((0, 4), (4, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert s_won.is_terminal() is True
    assert legal_moves(s_won) == []
    assert legal_pawn_moves(s_won) == []
    assert legal_wall_moves(s_won) == []
    assert is_legal(s_won, PawnMove((0, 3))) is False
    assert is_legal(s_won, WallMove(3, 3, H)) is False