"""Tests for jump cases, diagonal options, wall legality, and pass moves."""
from __future__ import annotations

import pytest

from quoridor_n.config import GameConfig
from quoridor_n.constants import H, V
from quoridor_n.rules import is_legal, is_wall_legal, legal_moves, legal_pawn_moves
from quoridor_n.state import GameState
from quoridor_n.types import PawnMove, WallMove, PassMove


def test_straight_jump():
    """Verify straight jump over adjacent opponent into empty space."""
    cfg = GameConfig(board_size=9, num_players=2)
    state = GameState(
        config=cfg,
        pawns=((4, 4), (3, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    # Straight jump landing at (2, 4) must be legal
    assert PawnMove(to=(2, 4)) in moves


def test_diagonal_jump_when_wall_behind():
    """When a wall stands directly behind the opponent, diagonal jumps are legal."""
    cfg = GameConfig(board_size=9, num_players=2)
    # Wall at groove (2, 4, 'H') blocks step between (2, 4) and (3, 4)
    state = GameState(
        config=cfg,
        pawns=((4, 4), (3, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(2, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    assert PawnMove(to=(2, 4)) not in moves  # Straight jump blocked
    assert PawnMove(to=(3, 3)) in moves  # Left diagonal
    assert PawnMove(to=(3, 5)) in moves  # Right diagonal


def test_diagonal_jump_when_board_edge_behind():
    """When opponent stands at board edge, straight jump is off-board, diagonals are legal."""
    cfg = GameConfig(board_size=9, num_players=2)
    # P1 at row 0 (top edge), P0 at (1, 4)
    state = GameState(
        config=cfg,
        pawns=((1, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    assert PawnMove(to=(-1, 4)) not in moves
    assert PawnMove(to=(0, 3)) in moves
    assert PawnMove(to=(0, 5)) in moves


def test_diagonal_jump_when_third_pawn_behind_4p():
    """In 4P, if a 3rd pawn stands directly behind the jumped pawn, diagonals are legal."""
    cfg = GameConfig(board_size=9, num_players=4)
    # P0 at (4, 4), P1 at (3, 4), P2 at (2, 4), P3 at (4, 8)
    state = GameState(
        config=cfg,
        pawns=((4, 4), (3, 4), (2, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    assert PawnMove(to=(2, 4)) not in moves  # Occupied by P2
    assert PawnMove(to=(3, 3)) in moves
    assert PawnMove(to=(3, 5)) in moves


def test_two_pawns_adjacent_in_corner():
    """Verify pawn movement when pawns are adjacent near board edge."""
    cfg = GameConfig(board_size=9, num_players=2)
    # P0 at (1, 0), P1 (seat 2) at (1, 1) - neither on goal row (0 or 8)
    state = GameState(
        config=cfg,
        pawns=((1, 0), (1, 1)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    # Can move up to (0, 0)
    assert PawnMove(to=(0, 0)) in moves
    # Can move down to (2, 0)
    assert PawnMove(to=(2, 0)) in moves
    # Straight jump right over opponent to (1, 2) is open
    assert PawnMove(to=(1, 2)) in moves


def test_wall_overlap_and_crossing():
    """Verify wall overlap and crossing are illegal."""
    cfg = GameConfig(board_size=9, num_players=2)
    state = GameState(
        config=cfg,
        pawns=((8, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(4, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    # Exact overlap
    assert not is_wall_legal(state, WallMove(4, 4, H))
    # Horizontal overlap left
    assert not is_wall_legal(state, WallMove(4, 3, H))
    # Horizontal overlap right
    assert not is_wall_legal(state, WallMove(4, 5, H))
    # Perpendicular crossing
    assert not is_wall_legal(state, WallMove(4, 4, V))
    # Adjacent parallel non-overlapping is legal
    assert is_wall_legal(state, WallMove(4, 2, H))
    assert is_wall_legal(state, WallMove(4, 6, H))


def test_fair_play_invariant_no_enclosing():
    """Verify a wall that completely blocks a player's path is illegal."""
    cfg = GameConfig(board_size=7, num_players=2)
    # Build a box almost enclosing P1 at (0, 3)
    # Walls surrounding (0, 3): H walls at (0, 2), (0, 3); V walls at (0, 2), (0, 3)
    state = GameState(
        config=cfg,
        pawns=((6, 3), (0, 3)),
        walls_left=(8, 8),
        h_walls=frozenset([(0, 2), (0, 3)]),
        v_walls=frozenset([(0, 2)]),
        current=0,
    )
    # Placing V wall at (0, 3) seals P1 completely inside row 0!
    closing_wall = WallMove(0, 3, V)
    assert not is_wall_legal(state, closing_wall)


def test_wall_on_last_slot():
    """Verify wall at groove N - 2 is within bounds."""
    cfg = GameConfig(board_size=8, num_players=2)
    state = GameState.initial(cfg)
    # Last slot is 8 - 2 = 6
    assert is_wall_legal(state, WallMove(6, 6, H))
    assert is_wall_legal(state, WallMove(6, 6, V))
    # Slot 7 is out of bounds
    assert not is_wall_legal(state, WallMove(7, 6, H))
    assert not is_wall_legal(state, WallMove(6, 7, V))


def test_forced_pass_when_no_moves():
    """Verify PassMove is the only legal move when pawn is hemmed in with 0 walls."""
    cfg = GameConfig(board_size=7, num_players=2)
    # Surround P0 at (6, 0) with board edges and walls, 0 walls left
    state = GameState(
        config=cfg,
        pawns=((6, 0), (0, 3)),
        walls_left=(0, 0),
        h_walls=frozenset([(5, 0)]),
        v_walls=frozenset([(5, 0)]),
        current=0,
    )
    pawn_moves = legal_pawn_moves(state)
    assert len(pawn_moves) == 0
    all_moves = legal_moves(state)
    assert all_moves == [PassMove()]
    assert is_legal(state, PassMove())
