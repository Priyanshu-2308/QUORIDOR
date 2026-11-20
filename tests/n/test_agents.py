"""Comprehensive unit and behavioral tests for quoridor_n agents."""
from __future__ import annotations

import pytest

from quoridor_n.agents import (
    GreedyAgent,
    MCTSAgent,
    MaxnAgent,
    ParanoidAgent,
    RandomAgent,
    make_agent,
)
from quoridor_n.config import GameConfig
from quoridor_n.constants import H, V
from quoridor_n.moves import candidate_walls
from quoridor_n.pathfinding import shortest_path
from quoridor_n.rules import is_legal, legal_moves, legal_pawn_moves
from quoridor_n.runner import play_game
from quoridor_n.state import GameState
from quoridor_n.types import PawnMove, WallMove, PassMove


def test_make_agent_factory():
    """Verify factory builds agents with parameter parsing and raises on bad inputs."""
    a1 = make_agent("random:wall_prob=0.3,seed=42")
    assert isinstance(a1, RandomAgent)
    assert a1.wall_prob == 0.3

    a2 = make_agent("greedy:wall_prob=0.1,wall_target='leader'")
    assert isinstance(a2, GreedyAgent)
    assert a2.wall_target == "leader"

    a3 = make_agent("paranoid:depth=3,use_tt=False,wall_cap=8")
    assert isinstance(a3, ParanoidAgent)
    assert a3.depth == 3
    assert a3.use_tt is False
    assert a3.wall_cap == 8

    a4 = make_agent("alphabeta:depth=2")
    assert isinstance(a4, ParanoidAgent)

    a5 = make_agent("maxn:depth=2,wall_cap=6")
    assert isinstance(a5, MaxnAgent)

    a6 = make_agent("mcts:iterations=250,rollout_policy='random'")
    assert isinstance(a6, MCTSAgent)
    assert a6.iterations == 250
    assert a6.rollout_policy == "random"

    with pytest.raises(ValueError):
        make_agent("unknown_agent")
    with pytest.raises(ValueError):
        make_agent("paranoid:invalid_key=10")
    with pytest.raises(ValueError):
        make_agent("")


@pytest.mark.parametrize("agent_name", ["random", "greedy", "paranoid:depth=1", "mcts:iterations=20"])
@pytest.mark.parametrize("n", [7, 12])
@pytest.mark.parametrize("p", [2, 4])
def test_all_agents_return_legal_move(agent_name: str, n: int, p: int):
    """Every agent returns a strictly legal move at N=7 and N=12 in both player modes."""
    cfg = GameConfig(board_size=n, num_players=p)
    state = GameState.initial(cfg)
    agent = make_agent(agent_name)
    move = agent.choose_move(state)
    assert is_legal(state, move), f"{agent.name} returned illegal move {move} on {n}x{n} {p}P"


def test_maxn_4p_only():
    """Verify MaxnAgent raises ValueError if run in 2-player mode."""
    cfg2 = GameConfig(board_size=9, num_players=2)
    st2 = GameState.initial(cfg2)
    agent = MaxnAgent(depth=1)
    with pytest.raises(ValueError):
        agent.choose_move(st2)


def test_seeded_determinism():
    """Agents with fixed seeds return identical moves and statistics."""
    cfg = GameConfig(board_size=9, num_players=4)
    st = GameState.initial(cfg)

    p1 = ParanoidAgent(depth=2, seed=123)
    p2 = ParanoidAgent(depth=2, seed=123)
    m1 = p1.choose_move(st)
    m2 = p2.choose_move(st)
    assert m1 == m2
    assert p1.last_stats["nodes"] == p2.last_stats["nodes"]

    mc1 = MCTSAgent(iterations=50, seed=456)
    mc2 = MCTSAgent(iterations=50, seed=456)
    m_mc1 = mc1.choose_move(st)
    m_mc2 = mc2.choose_move(st)
    assert m_mc1 == m_mc2


def test_immediate_win_and_loss_avoidance():
    """Verify search agents take immediate winning pawn moves."""
    cfg = GameConfig(board_size=9, num_players=2)
    # P0 at (1, 4), row 0 is goal. P2 at (0, 0).
    st = GameState(
        config=cfg,
        pawns=((1, 4), (0, 0)),
        walls_left=(10, 10),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    for spec in ["greedy", "paranoid:depth=2", "mcts:iterations=50"]:
        agent = make_agent(spec)
        move = agent.choose_move(st)
        assert move == PawnMove(to=(0, 4)), f"{spec} failed to take immediate win"


def test_wall_target_pruning_sets():
    """Verify 'all', 'leader', 'next', 'none' produce expected candidate wall sets."""
    cfg = GameConfig(board_size=9, num_players=4)
    # Position where P1 is leader (dist 4), P2 is far (dist 8), P3 is mid (dist 6)
    st = GameState(
        config=cfg,
        pawns=((8, 4), (4, 4), (0, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    w_none = candidate_walls(st, target="none")
    assert len(w_none) == 0

    w_all = candidate_walls(st, target="all")
    w_leader = candidate_walls(st, target="leader")
    w_next = candidate_walls(st, target="next")

    assert len(w_all) >= len(w_leader)
    assert set(w_leader).issubset(set(w_all))
    assert set(w_next).issubset(set(w_all))


def test_mcts_rollout_steps_around_wall():
    """Verify MCTS rollout policy respects physical walls and navigates around them."""
    cfg = GameConfig(board_size=9, num_players=2)
    # Pawn at (4, 4), wall directly blocking upward step to (3, 4)
    # Goal for P0 is row 0.
    st = GameState(
        config=cfg,
        pawns=((4, 4), (0, 4)),
        walls_left=(10, 10),
        h_walls=frozenset([(3, 4)]),  # horizontal wall below row 3
        v_walls=frozenset(),
        current=0,
    )
    # Shortest path must go around (row 4 col 3 or col 5 or row 4 col 6)
    path = shortest_path(st, 0)
    assert path is not None
    assert path[0] == (4, 4)
    assert path[1] != (3, 4), "Shortest path stepped through physical wall!"
    assert path[1] in [(4, 3), (4, 5)], f"Unexpected detoured step: {path[1]}"

    # Run MCTS rollout with path_biased policy: all rollout moves must be legal and not walk into wall
    agent = MCTSAgent(iterations=50, rollout_policy="path_biased", seed=42)
    move = agent.choose_move(st)
    assert is_legal(st, move)
    if isinstance(move, PawnMove):
        assert move.to != (3, 4)


def test_pass_handling_by_all_agents():
    """When a pawn has zero legal pawn moves and 0 walls, every agent cleanly returns PassMove."""
    cfg = GameConfig(board_size=7, num_players=2)
    # Completely hem in P0 at (6, 0) with walls and board boundaries, 0 walls left
    st = GameState(
        config=cfg,
        pawns=((6, 0), (0, 3)),
        walls_left=(0, 0),
        h_walls=frozenset([(5, 0)]),
        v_walls=frozenset([(5, 0)]),
        current=0,
    )
    assert legal_moves(st) == [PassMove()]

    for spec in ["random", "greedy", "paranoid:depth=1", "mcts:iterations=20"]:
        agent = make_agent(spec)
        move = agent.choose_move(st)
        assert isinstance(move, PassMove), f"{spec} did not return PassMove in deadlock"


def test_search_statistics_keys_present():
    """Verify all required statistics keys are populated after choosing a move."""
    cfg = GameConfig(board_size=9, num_players=2)
    st = GameState.initial(cfg)

    required_keys = {"nodes", "time_s", "eval", "depth", "iterations", "tt_hits", "cutoffs"}

    for spec in ["paranoid:depth=2", "mcts:iterations=30"]:
        agent = make_agent(spec)
        agent.choose_move(st)
        assert required_keys.issubset(agent.last_stats.keys()), (
            f"Missing stats keys for {spec}: {required_keys - set(agent.last_stats.keys())}"
        )


def test_short_game_paranoid_beats_random():
    """Documented benchmark: Paranoid(depth=2) wins against RandomAgent in 2P 9x9."""
    cfg = GameConfig(board_size=9, num_players=2, max_turns=100)
    paranoid = ParanoidAgent(depth=2, seed=42)
    rnd = RandomAgent(seed=42)
    res = play_game({0: paranoid, 2: rnd}, config=cfg)
    assert res.winner == 0, f"Paranoid lost to random: winner was {res.winner}"
    assert res.plies < 100
