"""Tests for pathfinding and multi-source BFS equivalence."""
from __future__ import annotations

import random
import pytest

from quoridor_n.config import GameConfig
from quoridor_n.constants import H, V
from quoridor_n.pathfinding import (
    has_path,
    multi_source_distances,
    shortest_path,
    shortest_path_length,
)
from quoridor_n.state import GameState

SIZES = [7, 8, 9, 10, 11, 12]


@pytest.mark.parametrize("n", SIZES)
def test_multi_source_bfs_equals_single_pawn_bfs_on_empty_board(n: int):
    """Multi-source BFS distance table must equal single-pawn shortest path length for all cells."""
    cfg = GameConfig(board_size=n, num_players=4)
    state = GameState.initial(cfg)

    for p in state.players:
        table = multi_source_distances(state, p)
        # Check for various cells
        for r in range(n):
            for c in range(n):
                cell_idx = r * n + c
                expected_dist = table[cell_idx]

                # Construct state with player's pawn placed at (r, c)
                pawns = list(state.pawns)
                pawns[state.player_index(p)] = (r, c)
                test_state = GameState(
                    config=cfg,
                    pawns=tuple(pawns),
                    walls_left=state.walls_left,
                    h_walls=state.h_walls,
                    v_walls=state.v_walls,
                    current=p,
                )
                single_dist = shortest_path_length(test_state, p)
                assert single_dist == expected_dist, (
                    f"Mismatch at cell ({r}, {c}) for player {p} on {n}x{n}: "
                    f"single={single_dist}, multi={expected_dist}"
                )


def test_multi_source_bfs_with_maze_walls():
    """Verify multi-source BFS matches single-source BFS on a board with walls."""
    n = 9
    cfg = GameConfig(board_size=n, num_players=4)
    # Add several walls
    h_walls = frozenset([(2, 2), (4, 4), (6, 2)])
    v_walls = frozenset([(1, 4), (5, 4)])
    state = GameState(
        config=cfg,
        pawns=((8, 4), (4, 0), (0, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=h_walls,
        v_walls=v_walls,
        current=0,
    )

    for p in (0, 1, 2, 3):
        table = multi_source_distances(state, p)
        for r in [1, 3, 5, 7]:
            for c in [1, 3, 5, 7]:
                pawns = list(state.pawns)
                pawns[p] = (r, c)
                test_state = GameState(
                    config=cfg,
                    pawns=tuple(pawns),
                    walls_left=state.walls_left,
                    h_walls=h_walls,
                    v_walls=v_walls,
                    current=p,
                )
                assert shortest_path_length(test_state, p) == table[r * n + c]
