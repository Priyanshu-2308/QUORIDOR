"""Unit tests for quoridor_n pathfinding."""
import random
from quoridor_n.constants import START
from quoridor_n.pathfinding import (
    distances,
    has_path,
    multi_source_distances,
    shortest_path,
    shortest_path_length,
)
from quoridor_n.state import GameState
from quoridor_n.types import WallMove


def test_open_board_distances_all_players():
    state = GameState.initial(num_players=4)
    # Every player starts exactly 8 steps from their respective goal
    # P0: (8, 4) -> row 0: 8 steps
    # P1: (4, 0) -> col 8: 8 steps
    # P2: (0, 4) -> row 8: 8 steps
    # P3: (4, 8) -> col 0: 8 steps
    dists = distances(state)
    assert dists == (8, 8, 8, 8)
    for p in range(4):
        assert shortest_path_length(state, p) == 8
        path = shortest_path(state, p)
        assert path is not None
        assert len(path) == 9  # 9 cells = 8 steps
        assert path[0] == START[p]


def test_walls_lengthen_path():
    state = GameState.initial(num_players=4)
    # Place horizontal wall directly blocking P0's path: groove (7, 3) blocks step (8,4)->(7,4) and (8,3)->(7,3)
    s1 = state.apply(WallMove(7, 3, "H"))
    assert shortest_path_length(s1, 0) == 9  # Wall lengthens path from 8 to 9 steps


def test_multi_source_equals_single_pawn_bfs_on_random_positions():
    rng = random.Random(42)
    for _ in range(50):
        # Generate random wall placements
        state = GameState.initial(num_players=4)
        for _ in range(8):
            r = rng.randint(0, 7)
            c = rng.randint(0, 7)
            o = rng.choice(["H", "V"])
            wm = WallMove(r, c, o)
            # Try applying wall if legal
            from quoridor_n.rules import is_wall_legal
            if is_wall_legal(state, wm):
                state = state.apply(wm)

        for p in range(4):
            # Check single pawn BFS vs multi-source backward BFS
            single_d = shortest_path_length(state, p)
            multi_grid = multi_source_distances(state, p)
            pr, pc = state.pawn(p)
            multi_d = multi_grid[pr * 9 + pc]
            assert single_d == multi_d, f"Mismatch for player {p} on board:\n{state.render()}"


def test_unreachable_handling():
    # Construct a state where pawn is completely trapped
    state = GameState.initial(num_players=4)
    # Surround (0, 0) with walls
    # Move P2 to (0, 0)
    p2_trapped = GameState(
        num_players=4,
        pawns=((8, 4), (4, 0), (0, 0), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset([(0, 0)]),  # blocks (0,0)-(1,0) and (0,1)-(1,1)
        v_walls=frozenset([(0, 0)]),  # blocks (0,0)-(0,1) and (1,0)-(1,1)
        current=2,
        turn_count=0,
    )
    # (0, 0) is blocked to south by h_wall(0,0) and to east by v_wall(0,0). Board edges block north and west.
    assert shortest_path(p2_trapped, 2) is None
    assert shortest_path_length(p2_trapped, 2) is None
    assert not has_path(p2_trapped, 2)
