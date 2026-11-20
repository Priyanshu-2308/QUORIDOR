"""Tests for GameConfig, start cells, goal rules, and initial state across all 12 combinations."""
from __future__ import annotations

import pytest

from quoridor_n.config import GameConfig
from quoridor_n.constants import default_walls_per_player, goal_reached, start_cell
from quoridor_n.pathfinding import shortest_path_length
from quoridor_n.state import GameState

SIZES = [7, 8, 9, 10, 11, 12]
PLAYERS = [2, 4]


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize("p", PLAYERS)
def test_all_12_combinations_initial_state(n: int, p: int):
    """Verify all 12 size/player combinations satisfy initial state invariants."""
    config = GameConfig(board_size=n, num_players=p)
    state = GameState.initial(config)

    # 1. Active player IDs
    expected_players = (0, 1, 2, 3) if p == 4 else (0, 2)
    assert config.players == expected_players
    assert state.players == expected_players

    # 2. Wall counts
    expected_walls = default_walls_per_player(n, p)
    assert config.walls_per_player == expected_walls
    assert state.walls_left == tuple(expected_walls for _ in expected_players)

    # 3. Start cells and no overlaps
    assert len(set(state.pawns)) == p
    c0 = (n - 1) // 2
    assert state.pawns[0] == (n - 1, c0)

    # 4. Every player is exactly N - 1 steps from its goal side on the empty board
    for pid in expected_players:
        d = shortest_path_length(state, pid)
        assert d == n - 1, f"Player {pid} distance was {d}, expected {n - 1} on board {n}x{n}"

    # 5. Not terminal, no winner, turn count 0
    assert not state.is_terminal()
    assert state.winner() is None
    assert state.turn_count == 0
    assert state.current == 0


def test_invalid_configs_raise():
    """Verify out-of-range board sizes and player counts raise ValueError."""
    with pytest.raises(ValueError):
        GameConfig(board_size=6)
    with pytest.raises(ValueError):
        GameConfig(board_size=13)
    with pytest.raises(ValueError):
        GameConfig(num_players=3)
    with pytest.raises(ValueError):
        GameConfig(walls_per_player=-1)
    with pytest.raises(ValueError):
        GameConfig(max_turns=0)


def test_even_board_geometry_and_asymmetric_start():
    """Verify start cells for even N follow quarter-turn rotation."""
    # N = 8: c0 = 3
    # P0: (7, 3), P1: (3, 0), P2: (0, 4), P3: (4, 7)
    cfg8_4p = GameConfig(board_size=8, num_players=4)
    st8_4p = GameState.initial(cfg8_4p)
    assert st8_4p.pawn(0) == (7, 3)
    assert st8_4p.pawn(1) == (3, 0)
    assert st8_4p.pawn(2) == (0, 4)
    assert st8_4p.pawn(3) == (4, 7)

    # In 2-player mode on N = 8: P0 starts at col 3, P2 starts at col 4
    cfg8_2p = GameConfig(board_size=8, num_players=2)
    st8_2p = GameState.initial(cfg8_2p)
    assert st8_2p.pawn(0) == (7, 3)
    assert st8_2p.pawn(2) == (0, 4)
