"""Unit tests for quoridor_n move legality and jump rules."""
import pytest
from quoridor_n.constants import START
from quoridor_n.rules import (
    is_legal,
    is_wall_legal,
    legal_moves,
    legal_pawn_moves,
    legal_wall_moves,
)
from quoridor_n.state import GameState
from quoridor_n.types import PawnMove, WallMove


def test_straight_jump():
    # P0 at (5, 4), P2 at (4, 4). P0 moving North straight jumps over P2 to (3, 4).
    state = GameState(
        num_players=4,
        pawns=((5, 4), (4, 0), (4, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (3, 4) in targets  # Straight jump over (4, 4)
    assert (4, 4) not in targets  # Cannot land on opponent pawn


def test_jump_blocked_by_wall_gives_two_diagonals():
    # P0 at (5, 4), P2 at (4, 4). Wall blocks (4, 4) -> (3, 4).
    # H wall at (3, 4) blocks (3,4)-(4,4) and (3,5)-(4,5).
    state = GameState(
        num_players=4,
        pawns=((5, 4), (4, 0), (4, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset([(3, 4)]),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (3, 4) not in targets  # Straight jump blocked by wall
    assert (4, 3) in targets      # Diagonal jump West
    assert (4, 5) in targets      # Diagonal jump East


def test_jump_blocked_by_board_edge_gives_diagonals():
    # P2 at (0, 4), P0 at (1, 4). P0 wants to jump North, but (0, 4) is row 0; beyond is off-board.
    state = GameState(
        num_players=4,
        pawns=((1, 4), (4, 0), (0, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (0, 3) in targets  # Diagonal West
    assert (0, 5) in targets  # Diagonal East


def test_jump_blocked_by_pawn_behind_pawn():
    # P0 at (6, 4), P1 at (5, 4), P2 at (4, 4).
    # P0 tries straight jump over P1, but (4, 4) is occupied by P2!
    # Straight jump is impossible, so P0 gets diagonal jumps beside P1 to (5, 3) and (5, 5).
    state = GameState(
        num_players=4,
        pawns=((6, 4), (5, 4), (4, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (4, 4) not in targets  # Cannot jump into P2
    assert (5, 3) in targets      # Diagonal West
    assert (5, 5) in targets      # Diagonal East


def test_one_diagonal_only_when_other_blocked():
    # P0 at (5, 4), P2 at (4, 4). Wall behind P2 at (3, 4) 'H'.
    # Also wall between (4, 4) and (4, 5): V wall at (4, 4) blocks (4,4)-(4,5) and (5,4)-(5,5).
    # East diagonal is blocked, so only West diagonal (4, 3) is legal.
    state = GameState(
        num_players=4,
        pawns=((5, 4), (4, 0), (4, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset([(3, 4)]),
        v_walls=frozenset([(4, 4)]),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (3, 4) not in targets
    assert (4, 3) in targets
    assert (4, 5) not in targets


def test_two_pawns_adjacent_in_corner():
    # P1 at (0, 0), P0 at (1, 0).
    # P0 moving North encounters P1 at (0, 0).
    # North straight jump goes off-board.
    # Beside P1: West goes off board; East is (0, 1).
    state = GameState(
        num_players=4,
        pawns=((1, 0), (0, 0), (0, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    moves = legal_pawn_moves(state)
    targets = {m.to for m in moves}
    assert (0, 1) in targets  # Single valid diagonal into corner neighbour


def test_wall_overlap_and_crossing():
    state = GameState.initial(num_players=4)
    s1 = state.apply(WallMove(3, 3, "H"))

    # Overlap exact same
    assert not is_wall_legal(s1, WallMove(3, 3, "H"))
    # Overlap left
    assert not is_wall_legal(s1, WallMove(3, 2, "H"))
    # Overlap right
    assert not is_wall_legal(s1, WallMove(3, 4, "H"))
    # Crossing vertical wall
    assert not is_wall_legal(s1, WallMove(3, 3, "V"))

    # Adjacent non-overlapping is legal
    assert is_wall_legal(s1, WallMove(3, 5, "H"))
    assert is_wall_legal(s1, WallMove(3, 1, "H"))


def test_fair_play_invariant_blocks_wall():
    # Trap P0 from reaching row 0
    # Surround (8, 4) with walls
    # H wall at (7, 4) and (7, 3), V walls at (7, 3) and (7, 4)
    state = GameState.initial(num_players=4)
    s1 = state.apply(WallMove(7, 3, "H"))
    s2 = s1.apply(WallMove(7, 4, "H"))
    s3 = s2.apply(WallMove(7, 3, "V"))
    # WallMove(7, 4, "V") would seal the trap completely
    assert not is_wall_legal(s3, WallMove(7, 4, "V"))


def test_walls_left_exhaustion():
    state = GameState(
        num_players=4,
        pawns=((8, 4), (4, 0), (0, 4), (4, 8)),
        walls_left=(0, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    assert legal_wall_moves(state) == []
    assert not is_wall_legal(state, WallMove(3, 3, "H"))


def test_immediate_win():
    # P0 at (1, 4), one step from empty goal cell (0, 4)
    state = GameState(
        num_players=4,
        pawns=((1, 4), (4, 0), (2, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    winning_move = PawnMove(to=(0, 4))
    assert is_legal(state, winning_move)
    next_state = state.apply(winning_move)
    assert next_state.winner() == 0
    assert next_state.is_terminal()
