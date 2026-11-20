"""Oracle equivalence test against the baseline two-player engine at 9x9."""
from __future__ import annotations

import random
import pytest

import quoridor.pathfinding as old_pf
import quoridor.rules as old_rules
import quoridor.state as old_state
from quoridor.agents.alphabeta_agent import AlphaBetaAgent as OldAlphaBetaAgent

import quoridor_n.pathfinding as new_pf
import quoridor_n.rules as new_rules
import quoridor_n.state as new_state
from quoridor_n.agents.paranoid_agent import ParanoidAgent
from quoridor_n.config import GameConfig
from quoridor_n.types import PawnMove, WallMove


def old_to_new_state(s_old: old_state.GameState) -> new_state.GameState:
    """Map old 2P GameState to new 2P GameState (seats 0 and 2)."""
    cfg = GameConfig(board_size=9, num_players=2, walls_per_player=10, max_turns=360)
    curr_new = 0 if s_old.current == 0 else 2
    return new_state.GameState(
        config=cfg,
        pawns=s_old.pawns,
        walls_left=s_old.walls_left,
        h_walls=s_old.h_walls,
        v_walls=s_old.v_walls,
        current=curr_new,
        turn_count=s_old.turn_count,
    )


def test_2000_positions_equivalence_with_old_engine():
    """Verify pawn moves, legal walls, path lengths, and winner match old engine on >= 2,000 positions."""
    rng = random.Random(42)
    positions_checked = 0
    target_positions = 2000

    game_idx = 0
    while positions_checked < target_positions:
        game_idx += 1
        s_old = old_state.GameState.initial()

        while not s_old.is_terminal() and s_old.turn_count < 150:
            s_new = old_to_new_state(s_old)

            # 1. Legal pawn moves equivalence
            p_old = sorted([m.to for m in old_rules.legal_pawn_moves(s_old)])
            p_new = sorted([m.to for m in new_rules.legal_pawn_moves(s_new)])
            assert p_new == p_old, f"Pawn move mismatch at turn {s_old.turn_count}: old={p_old}, new={p_new}"

            # 2. Legal wall moves equivalence
            w_old = sorted([(w.r, w.c, w.o) for w in old_rules.legal_wall_moves(s_old)])
            w_new = sorted([(w.r, w.c, w.o) for w in new_rules.legal_wall_moves(s_new)])
            assert w_new == w_old, f"Wall move mismatch at turn {s_old.turn_count}: old count={len(w_old)}, new count={len(w_new)}"

            # 3. Path lengths equivalence
            d0_old = old_pf.shortest_path_length(s_old, 0)
            d1_old = old_pf.shortest_path_length(s_old, 1)
            d0_new = new_pf.shortest_path_length(s_new, 0)
            d2_new = new_pf.shortest_path_length(s_new, 2)
            assert d0_new == d0_old, f"P0 distance mismatch: old={d0_old}, new={d0_new}"
            assert d2_new == d1_old, f"P1/P2 distance mismatch: old={d1_old}, new={d2_new}"

            # 4. Winner detection
            w_old_winner = s_old.winner()
            w_new_winner = s_new.winner()
            if w_old_winner == 0:
                assert w_new_winner == 0
            elif w_old_winner == 1:
                assert w_new_winner == 2
            else:
                assert w_new_winner is None

            positions_checked += 1
            if positions_checked >= target_positions:
                break

            # Play random move
            p_moves = old_rules.legal_pawn_moves(s_old)
            w_moves = old_rules.legal_wall_moves(s_old)
            if w_moves and rng.random() < 0.3:
                move = rng.choice(w_moves)
            else:
                move = rng.choice(p_moves)
            s_old = s_old.apply(move)

    assert positions_checked >= 2000, f"Only checked {positions_checked} positions"


def test_paranoid_vs_old_alphabeta_root_values_100_positions():
    """Verify ParanoidAgent root evaluation equals old AlphaBetaAgent on >= 100 positions."""
    rng = random.Random(99)
    positions_checked = 0
    target_positions = 100

    old_ab = OldAlphaBetaAgent(depth=2, use_tt=False, use_move_ordering=True, use_wall_pruning=True, seed=42)
    new_ab = ParanoidAgent(depth=2, use_tt=False, use_move_ordering=True, use_wall_pruning=True, seed=42)

    while positions_checked < target_positions:
        s_old = old_state.GameState.initial()
        for _ in range(rng.randint(2, 20)):
            if s_old.is_terminal():
                break
            moves = old_rules.legal_moves(s_old)
            s_old = s_old.apply(rng.choice(moves))

        if s_old.is_terminal():
            continue

        s_new = old_to_new_state(s_old)
        old_ab.choose_move(s_old)
        new_ab.choose_move(s_new)

        val_old = old_ab.last_stats["eval"]
        val_new = new_ab.last_stats["eval"]

        assert abs(val_old - val_new) < 1e-4, (
            f"Eval score mismatch at position {positions_checked}: old={val_old}, new={val_new}"
        )
        positions_checked += 1

    assert positions_checked >= 100
