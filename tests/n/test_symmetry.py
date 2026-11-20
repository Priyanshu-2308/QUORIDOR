"""Symmetry property tests for dynamic Quoridor boards."""
from __future__ import annotations

import pytest

from quoridor_n.config import GameConfig
from quoridor_n.constants import H, V
from quoridor_n.rules import legal_moves
from quoridor_n.state import GameState
from quoridor_n.types import Move, PawnMove, WallMove, PassMove

SIZES = [7, 8, 9, 10, 11, 12]


def rotate_cell(r: int, c: int, n: int) -> tuple[int, int]:
    """Rotate cell (r, c) 90 degrees clockwise on an N x N board."""
    return (c, n - 1 - r)


def rotate_wall(r: int, c: int, o: str, n: int) -> tuple[int, int, str]:
    """Rotate groove (r, c, o) 90 degrees clockwise."""
    # A groove (r, c) between rows r/r+1 and cols c/c+1 rotates to:
    # row' = c, col' = (N - 2) - r
    # Horizontal wall becomes Vertical wall, Vertical wall becomes Horizontal wall.
    new_r = c
    new_c = (n - 2) - r
    new_o = V if o == H else H
    return new_r, new_c, new_o


def rotate_move(m: Move, n: int) -> Move:
    """Rotate a move 90 degrees clockwise."""
    if isinstance(m, PawnMove):
        return PawnMove(to=rotate_cell(m.to[0], m.to[1], n))
    if isinstance(m, WallMove):
        nr, nc, no = rotate_wall(m.r, m.c, m.o, n)
        return WallMove(nr, nc, no)
    if isinstance(m, PassMove):
        return PassMove()
    raise TypeError(f"unknown move: {m!r}")


def rotate_state_quarter_turn(state: GameState) -> GameState:
    """Rotate a 4-player state 90 degrees clockwise.

    Maps Seat i -> Seat (i + 1) % 4.
    """
    n = state.config.board_size
    assert state.config.num_players == 4

    # Pawns: Seat 0 was at pawns[0], in new state it corresponds to player 1's position
    # rotated pawns: Seat (i + 1) % 4 gets rotated pawn of Seat i
    new_pawns = [None] * 4
    new_walls_left = [None] * 4
    for i in range(4):
        new_i = (i + 1) % 4
        old_r, old_c = state.pawns[i]
        new_pawns[new_i] = rotate_cell(old_r, old_c, n)
        new_walls_left[new_i] = state.walls_left[i]

    new_h_walls = set()
    new_v_walls = set()
    for r, c in state.h_walls:
        nr, nc, no = rotate_wall(r, c, H, n)
        if no == H:
            new_h_walls.add((nr, nc))
        else:
            new_v_walls.add((nr, nc))

    for r, c in state.v_walls:
        nr, nc, no = rotate_wall(r, c, V, n)
        if no == H:
            new_h_walls.add((nr, nc))
        else:
            new_v_walls.add((nr, nc))

    new_current = (state.current + 1) % 4

    return GameState(
        config=state.config,
        pawns=tuple(new_pawns),  # type: ignore
        walls_left=tuple(new_walls_left),  # type: ignore
        h_walls=frozenset(new_h_walls),
        v_walls=frozenset(new_v_walls),
        current=new_current,
        turn_count=state.turn_count,
        pass_count=state.pass_count,
    )


@pytest.mark.parametrize("n", SIZES)
def test_quarter_turn_symmetry_4p(n: int):
    """For 4 players at every N, rotating state quarter-turn rotates legal moves identically."""
    cfg = GameConfig(board_size=n, num_players=4)
    state = GameState.initial(cfg)

    # Initial moves
    orig_moves = set(legal_moves(state))
    rotated_state = rotate_state_quarter_turn(state)
    rot_moves = set(legal_moves(rotated_state))

    # Transforming orig_moves by quarter turn must exactly match rot_moves
    expected_rot_moves = {rotate_move(m, n) for m in orig_moves}
    assert expected_rot_moves == rot_moves, f"Quarter turn move mismatch at N={n}"


@pytest.mark.parametrize("n", SIZES)
def test_half_turn_symmetry_2p(n: int):
    """For 2 players at every N, rotating state half-turn (180 deg) swaps seat 0 and seat 2."""
    cfg = GameConfig(board_size=n, num_players=2)
    state = GameState.initial(cfg)

    p0 = state.pawn(0)
    p2 = state.pawn(2)

    # 180 deg rotation: (r, c) -> (N - 1 - r, N - 1 - c)
    p0_rot = (n - 1 - p0[0], n - 1 - p0[1])
    assert p0_rot == p2, f"Half turn of P0 {p0} is not P2 {p2} at N={n}"
