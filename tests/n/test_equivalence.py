"""Equivalence test comparing quoridor_n (in 2-player mode) against the quoridor oracle."""
import random
import pytest

from quoridor import pathfinding as old_pf, rules as old_rules
from quoridor.state import GameState as OldGameState
from quoridor.types import PawnMove, WallMove

from quoridor_n import pathfinding as new_pf, rules as new_rules
from quoridor_n.state import GameState as NewGameState


def test_2000_positions_equivalence_with_old_engine():
    """Verify that quoridor_n in 2-player mode produces identical legal moves,

    shortest paths, and winner detection across at least 2,000 random positions.
    """
    TOTAL_POSITIONS_TARGET = 2000
    positions_checked = 0
    rng = random.Random(42)
    game_idx = 0

    while positions_checked < TOTAL_POSITIONS_TARGET:
        game_idx += 1
        old_s = OldGameState.initial()
        new_s = NewGameState.initial(num_players=2)

        while not old_s.is_terminal() and old_s.turn_count < 200:
            positions_checked += 1

            # 1. Verify State Core
            assert old_s.pawns[0] == new_s.pawn(0)
            assert old_s.pawns[1] == new_s.pawn(2)
            assert old_s.walls_left[0] == new_s.walls(0)
            assert old_s.walls_left[1] == new_s.walls(2)
            assert old_s.h_walls == new_s.h_walls
            assert old_s.v_walls == new_s.v_walls

            expected_new_current = 0 if old_s.current == 0 else 2
            assert new_s.current == expected_new_current

            # 2. Verify Shortest Path Lengths
            assert old_pf.shortest_path_length(old_s, 0) == new_pf.shortest_path_length(new_s, 0)
            assert old_pf.shortest_path_length(old_s, 1) == new_pf.shortest_path_length(new_s, 2)
            assert old_pf.has_path(old_s, 0) == new_pf.has_path(new_s, 0)
            assert old_pf.has_path(old_s, 1) == new_pf.has_path(new_s, 2)

            # 3. Verify Winner
            old_w = old_s.winner()
            new_w = new_s.winner()
            if old_w is None:
                assert new_w is None
            elif old_w == 0:
                assert new_w == 0
            else:
                assert new_w == 2

            # 4. Verify Legal Pawn Moves
            old_pawn_moves = set(old_rules.legal_pawn_moves(old_s))
            new_pawn_moves = set(new_rules.legal_pawn_moves(new_s))
            assert old_pawn_moves == new_pawn_moves, f"Pawn move mismatch at ply {old_s.turn_count}"

            # 5. Verify Legal Wall Moves
            old_wall_moves = set(old_rules.legal_wall_moves(old_s))
            new_wall_moves = set(new_rules.legal_wall_moves(new_s))
            assert old_wall_moves == new_wall_moves, f"Wall move mismatch at ply {old_s.turn_count}"

            # Step forward with random legal move
            all_legal = list(old_rules.legal_moves(old_s))
            if not all_legal:
                break
            move = rng.choice(all_legal)

            old_s = old_s.apply(move)
            new_s = new_s.apply(move)

            if positions_checked >= TOTAL_POSITIONS_TARGET:
                break

    assert positions_checked >= TOTAL_POSITIONS_TARGET
    print(f"Verified equivalence across {positions_checked} positions over {game_idx} games.")
