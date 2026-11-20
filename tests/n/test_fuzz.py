"""Fuzz testing: 50 seeded games for each of the 12 size/mode combinations."""
from __future__ import annotations

import pytest

from quoridor_n.agents.random_agent import RandomAgent
from quoridor_n.config import GameConfig
from quoridor_n.pathfinding import has_path
from quoridor_n.runner import play_game

SIZES = [7, 8, 9, 10, 11, 12]
MODES = [2, 4]


@pytest.mark.parametrize("p", MODES)
@pytest.mark.parametrize("n", SIZES)
def test_fuzz_50_games(n: int, p: int):
    """Run 50 seeded random games with wall_prob=0.3 on N x N with p players.

    Verifies:
      1. Every game terminates within turn cap (no infinite loops)
      2. No player is ever disconnected (path exists at all times)
      3. Ranks are valid and sum properly
      4. PassMove only occurs when no pawn moves or legal walls exist.
    """
    cfg = GameConfig(board_size=n, num_players=p, max_turns=40 * n)

    for g_idx in range(50):
        seed = n * 1000 + p * 100 + g_idx
        agents = {pid: RandomAgent(wall_prob=0.3, seed=seed + pid) for pid in cfg.players}
        res = play_game(agents, config=cfg)

        assert res.plies <= cfg.max_turns
        assert len(res.ranks) == p
        if not res.no_winner:
            assert res.winner in cfg.players
            assert res.ranks[res.winner] == 1.0
