"""Fuzz testing for random four-player games to verify system invariants."""
import random
from quoridor_n.pathfinding import has_path
from quoridor_n.rules import is_legal, legal_moves
from quoridor_n.state import GameState


def test_fuzz_random_4p_games():
    """Verify that random 4-player games never violate invariants:

    - Move chosen is always legal.
    - Every active player maintains an open path to their goal at every ply.
    - Pawn positions never overlap.
    - Games terminate either through victory or at the 400 turn cap.
    """
    NUM_GAMES = 15
    MAX_CAP = 400

    for seed in range(NUM_GAMES):
        rng = random.Random(seed + 1000)
        state = GameState.initial(num_players=4)

        while not state.is_terminal() and state.turn_count < MAX_CAP:
            # 1. Invariant: All 4 players have an open path to goal
            for p in range(4):
                assert has_path(state, p), f"Player {p} trapped without path at ply {state.turn_count}"

            # 2. Invariant: Pawns do not occupy identical coordinates
            pawn_coords = [state.pawn(p) for p in range(4)]
            assert len(set(pawn_coords)) == 4, f"Overlapping pawns detected: {pawn_coords}"

            # 3. Invariant: Legal moves exist
            avail = legal_moves(state)
            assert len(avail) > 0, f"No legal moves available at ply {state.turn_count}"

            # 4. Pick random move and verify is_legal
            chosen = rng.choice(avail)
            assert is_legal(state, chosen)

            # Apply move
            state = state.apply(chosen)

        # Game ended: either terminal win or reached turn cap
        if state.is_terminal():
            winner = state.winner()
            assert winner is not None
            assert 0 <= winner <= 3
        else:
            assert state.turn_count == MAX_CAP
