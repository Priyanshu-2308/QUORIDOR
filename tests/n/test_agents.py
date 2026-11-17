"""Unit tests for four-player Quoridor agents."""
import pytest
from quoridor_n.agents import (
    GreedyAgent,
    MaxnAgent,
    MCTSAgent,
    ParanoidAgent,
    RandomAgent,
    make_agent,
)
from quoridor_n.moves import candidate_walls
from quoridor_n.rules import is_legal
from quoridor_n.runner import play_game
from quoridor_n.state import GameState
from quoridor_n.types import PawnMove, WallMove


def test_factory_creation_and_errors():
    a1 = make_agent("random:wall_prob=0.3,seed=42")
    assert isinstance(a1, RandomAgent)
    assert a1.wall_prob == 0.3

    a2 = make_agent("paranoid:depth=3,eval_mode='leader'")
    assert isinstance(a2, ParanoidAgent)
    assert a2.depth == 3
    assert a2.eval_mode == "leader"

    a3 = make_agent("maxn:depth=2,wall_target='next'")
    assert isinstance(a3, MaxnAgent)
    assert a3.wall_target == "next"

    a4 = make_agent("mcts:iterations=250,c=1.5")
    assert isinstance(a4, MCTSAgent)
    assert a4.iterations == 250
    assert a4.c == 1.5

    with pytest.raises(ValueError, match="unknown agent 'bad_agent'"):
        make_agent("bad_agent")

    with pytest.raises(ValueError, match="bad kwargs"):
        make_agent("random:invalid_key=123")


def test_agents_return_legal_moves():
    state = GameState.initial(num_players=4)
    agents = [
        RandomAgent(seed=1),
        GreedyAgent(seed=2),
        ParanoidAgent(depth=1, seed=3),
        MaxnAgent(depth=1, seed=4),
        MCTSAgent(iterations=50, seed=5),
    ]
    for agent in agents:
        move = agent.choose_move(state)
        assert is_legal(state, move), f"Agent {agent.name} returned illegal move {move!r}"
        stats = agent.last_stats
        assert "nodes" in stats and stats["nodes"] >= 1
        assert "time_s" in stats and stats["time_s"] >= 0.0


def test_seeded_determinism():
    state = GameState.initial(num_players=4)
    # Paranoid
    p1 = ParanoidAgent(depth=2, seed=123)
    p2 = ParanoidAgent(depth=2, seed=123)
    assert p1.choose_move(state) == p2.choose_move(state)

    # MCTS
    m1 = MCTSAgent(iterations=60, seed=456)
    m2 = MCTSAgent(iterations=60, seed=456)
    assert m1.choose_move(state) == m2.choose_move(state)


def test_immediate_win_detection():
    # P0 at (1, 4), goal row 0 is empty at (0, 4)
    state = GameState(
        num_players=4,
        pawns=((1, 4), (4, 0), (2, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    winning_move = PawnMove(to=(0, 4))

    for agent in [
        ParanoidAgent(depth=1),
        MaxnAgent(depth=1),
        MCTSAgent(iterations=50),
    ]:
        m = agent.choose_move(state)
        assert m == winning_move, f"{agent.name} failed to find immediate win: chose {m!r}"


def test_wall_targets_produce_expected_candidate_sets():
    # P0 at (8, 4), P1 at (4, 1) [dist 7 to col 8], P2 at (1, 4) [dist 7 to row 8], P3 at (4, 7) [dist 7 to col 0]
    # Set P2 at (2, 4) [dist 6, leader]
    state = GameState(
        num_players=4,
        pawns=((8, 4), (4, 0), (2, 4), (4, 8)),
        walls_left=(5, 5, 5, 5),
        h_walls=frozenset(),
        v_walls=frozenset(),
        current=0,
    )
    # Target "next" -> P1 only
    walls_next = candidate_walls(state, target="next")
    # Target "leader" -> P2 only (shortest distance 6)
    walls_leader = candidate_walls(state, target="leader")
    # Target "all" -> Union of P1, P2, P3
    walls_all = candidate_walls(state, target="all")

    assert len(walls_all) >= len(walls_next)
    assert len(walls_all) >= len(walls_leader)
    assert set(walls_next).issubset(set(walls_all))
    assert set(walls_leader).issubset(set(walls_all))


def test_search_beats_greedy_smoke_games():
    # Play 5 short games: Paranoid(d=2) vs 3 Greedy agents
    # Paranoid should win at least 3 of 5 games
    wins = 0
    num_games = 5
    for i in range(num_games):
        agents = [
            ParanoidAgent(depth=2, seed=i),
            GreedyAgent(seed=i + 1),
            GreedyAgent(seed=i + 2),
            GreedyAgent(seed=i + 3),
        ]
        res = play_game(agents, max_turns=150)
        if res.winner == 0:
            wins += 1

    assert wins >= 3, f"Paranoid won only {wins}/{num_games} against 3 Greedy agents"
