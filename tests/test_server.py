"""Tests for FastAPI backend server with dynamic board sizing and player counts."""
from __future__ import annotations

import time
import pytest
from fastapi.testclient import TestClient

from server.app import app, sessions, MAX_SESSIONS, Session
from quoridor_n.config import GameConfig
from quoridor_n.state import GameState
from quoridor_n.agents.random_agent import RandomAgent
from quoridor_n.types import PassMove


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_allowed_opponent_specs(client):
    valid_specs = [
        "random",
        "greedy",
        "alphabeta:depth=1",
        "alphabeta:depth=4",
        "paranoid:depth=2",
        "mcts:iterations=50",
        "mcts:iterations=1000",
        "alphabeta:depth=3,seed=42",
    ]
    for spec in valid_specs:
        resp = client.post("/api/new", json={"opponent": spec, "human_player": 0})
        assert resp.status_code == 200, f"Expected 200 for {spec}, got {resp.status_code}: {resp.text}"
        assert "game_id" in resp.json()


def test_rejected_opponent_specs(client):
    invalid_specs = [
        "alphabeta:depth=9",
        "alphabeta:depth=0",
        "mcts:iterations=100000",
        "mcts:iterations=10",
        "mcts:time_limit_s=100",
        "alphabeta:unknown_key=1",
        "greedy:depth=3",
        "unknown_agent",
        "",
    ]
    for spec in invalid_specs:
        resp = client.post("/api/new", json={"opponent": spec, "human_player": 0})
        assert resp.status_code == 400, f"Expected 400 for {spec}, got {resp.status_code}"


def test_session_cap_and_eviction(client):
    sessions.clear()
    now = time.time()

    cfg = GameConfig(board_size=9, num_players=2)
    dummy_state = GameState.initial(cfg)
    dummy_agent = RandomAgent()
    for i in range(MAX_SESSIONS):
        gid = f"session_{i}"
        sessions[gid] = Session(
            state=dummy_state,
            history=[dummy_state],
            history_moves=[],
            history_movers=[],
            opponents={2: dummy_agent},
            opponent_specs={2: "random"},
            human_player=0,
            last_accessed=now - (MAX_SESSIONS - i) * 10,
        )

    assert len(sessions) == MAX_SESSIONS
    oldest_id = "session_0"
    assert oldest_id in sessions

    resp = client.post("/api/new", json={"opponent": "random", "human_player": 0})
    assert resp.status_code == 200
    assert len(sessions) == MAX_SESSIONS
    assert oldest_id not in sessions

    expired_id = "session_expired"
    sessions[expired_id] = Session(
        state=dummy_state,
        history=[dummy_state],
        history_moves=[],
        history_movers=[],
        opponents={2: dummy_agent},
        opponent_specs={2: "random"},
        human_player=0,
        last_accessed=now - 8000,
    )
    resp = client.post("/api/new", json={"opponent": "random", "human_player": 0})
    assert resp.status_code == 200
    assert expired_id not in sessions


def test_validation_errors(client):
    """Test rejection of invalid board sizes, player counts, human seats, and opponent counts."""
    # Invalid board size
    assert client.post("/api/new", json={"board_size": 6, "num_players": 2}).status_code == 400
    assert client.post("/api/new", json={"board_size": 13, "num_players": 2}).status_code == 400

    # Invalid num_players
    assert client.post("/api/new", json={"board_size": 9, "num_players": 3}).status_code == 400
    assert client.post("/api/new", json={"board_size": 9, "num_players": 5}).status_code == 400

    # Invalid human_player seat
    assert client.post("/api/new", json={"board_size": 9, "num_players": 2, "human_player": 1}).status_code == 400
    assert client.post("/api/new", json={"board_size": 9, "num_players": 4, "human_player": 5}).status_code == 400

    # Opponent count mismatch for 4P
    assert client.post("/api/new", json={"board_size": 9, "num_players": 4, "opponents": ["random", "random"]}).status_code == 400


def test_all_12_sizes_and_modes(client):
    """Verify creating games for all 12 combinations of N in 7..12 and 2 or 4 players."""
    for n in range(7, 13):
        for p in (2, 4):
            opps = ["random"] * (p - 1)
            resp = client.post("/api/new", json={"board_size": n, "num_players": p, "opponents": opps})
            assert resp.status_code == 200, f"Failed for size={n}, players={p}: {resp.text}"
            data = resp.json()
            assert data["board_size"] == n
            assert data["num_players"] == p
            assert len(data["state"]["pawns"]) == p
            assert len(data["state"]["walls_left"]) == p


def test_server_flow_2p(client):
    resp = client.get("/api/state/nonexistent_game_id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "game not found"

    resp = client.post("/api/new", json={"opponent": "unknown_ai_spec:xyz=123", "human_player": 0})
    assert resp.status_code == 400
    assert "invalid opponent spec" in resp.json()["detail"]

    resp = client.post("/api/new", json={"opponent": "greedy", "human_player": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "game_id" in data
    assert "state" in data
    assert data["human_player"] == 0
    game_id = data["game_id"]

    resp = client.get(f"/api/state/{game_id}")
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["current"] == 0
    assert state["pawns"] == [[8, 4], [0, 4]]

    resp = client.get(f"/api/legal/{game_id}")
    assert resp.status_code == 200
    moves = resp.json()["moves"]
    assert len(moves) == 131

    illegal_move = {"type": "pawn", "to": [0, 0]}
    resp = client.post(f"/api/move/{game_id}", json={"move": illegal_move})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "illegal move"

    legal_move = {"type": "pawn", "to": [7, 4]}
    resp = client.post(f"/api/move/{game_id}", json={"move": legal_move})
    assert resp.status_code == 200
    new_state = resp.json()["state"]
    assert new_state["pawns"][0] == [7, 4]
    # In 2P, next player is seat 2
    assert new_state["current"] == 2

    resp = client.post(f"/api/move/{game_id}", json={"move": {"type": "pawn", "to": [6, 4]}})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "not human's turn"

    resp = client.get(f"/api/paths/{game_id}")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert len(paths) == 2
    assert paths[0][0] == [7, 4]
    assert paths[0][-1][0] == 0
    assert paths[1][0] == [0, 4]
    assert paths[1][-1][0] == 8

    resp = client.post(f"/api/ai/{game_id}")
    assert resp.status_code == 200
    ai_data = resp.json()
    assert "move" in ai_data
    assert "state" in ai_data
    assert "stats" in ai_data
    ai_state = ai_data["state"]
    assert ai_state["current"] == 0

    resp = client.post(f"/api/undo/{game_id}")
    assert resp.status_code == 200
    undone_state = resp.json()["state"]
    assert undone_state["pawns"] == [[8, 4], [0, 4]]
    assert undone_state["current"] == 0

    resp = client.post(f"/api/undo/{game_id}")
    assert resp.status_code == 200
    assert resp.json()["state"]["pawns"] == [[8, 4], [0, 4]]


def test_4p_flow_and_undo(client):
    """Test 4-player sequential AI triggering and human turn-boundary undo."""
    resp = client.post(
        "/api/new",
        json={
            "board_size": 9,
            "num_players": 4,
            "human_player": 0,
            "opponents": ["greedy", "greedy", "greedy"],
        },
    )
    assert resp.status_code == 200
    game_id = resp.json()["game_id"]

    # Seat 0 moves up
    resp = client.post(f"/api/move/{game_id}", json={"move": {"type": "pawn", "to": [7, 4]}})
    assert resp.status_code == 200
    assert resp.json()["state"]["current"] == 1

    # Seat 1, 2, 3 move
    for seat in (1, 2, 3):
        resp_ai = client.post(f"/api/ai/{game_id}")
        assert resp_ai.status_code == 200
        assert resp_ai.json()["mover"] == seat

    # Now it is human's turn again (seat 0)
    st = client.get(f"/api/state/{game_id}").json()["state"]
    assert st["current"] == 0

    # Human moves again
    resp = client.post(f"/api/move/{game_id}", json={"move": {"type": "pawn", "to": [6, 4]}})
    assert resp.status_code == 200
    assert resp.json()["state"]["pawns"][0] == [6, 4]

    # Undo should revert back to human's previous turn start (pawns[0] == [7, 4])
    resp_undo = client.post(f"/api/undo/{game_id}")
    assert resp_undo.status_code == 200
    undone = resp_undo.json()["state"]
    assert undone["pawns"][0] == [7, 4]
    assert undone["current"] == 0


def test_full_scripted_games(client):
    """Scripted game at N=7 and N=12 in both 2P and 4P modes."""
    # N=7 2P: Human walks straight up to row 0
    resp = client.post("/api/new", json={"board_size": 7, "num_players": 2, "opponents": ["greedy"]})
    assert resp.status_code == 200
    gid = resp.json()["game_id"]

    # Start at row 6, col 3; goal is row 0
    # Human moves up, greedy moves down; they will pass each other
    for _ in range(20):
        st = client.get(f"/api/state/{gid}").json()["state"]
        if st.get("winner") is not None or st.get("no_winner"):
            break
        if st["current"] == 0:
            legal = client.get(f"/api/legal/{gid}").json()["moves"]
            pawn_moves = [m for m in legal if m["type"] == "pawn"]
            # Pick pawn move that reduces row
            best_move = min(pawn_moves, key=lambda m: m["to"][0])
            res = client.post(f"/api/move/{gid}", json={"move": best_move})
            assert res.status_code == 200
        else:
            res = client.post(f"/api/ai/{gid}")
            assert res.status_code == 200

    final_state = client.get(f"/api/state/{gid}").json()
    assert final_state["is_terminal"] is True
    assert final_state["ranks"] is not None

    # N=12 4P: Run 15 plies with greedy opponents
    resp = client.post(
        "/api/new",
        json={"board_size": 12, "num_players": 4, "opponents": ["greedy", "greedy", "greedy"]},
    )
    assert resp.status_code == 200
    gid12 = resp.json()["game_id"]
    for ply in range(12):
        st = client.get(f"/api/state/{gid12}").json()["state"]
        if st["current"] == 0:
            legal = client.get(f"/api/legal/{gid12}").json()["moves"]
            pawn_moves = [m for m in legal if m["type"] == "pawn"]
            best_move = min(pawn_moves, key=lambda m: m["to"][0])
            client.post(f"/api/move/{gid12}", json={"move": best_move})
        else:
            client.post(f"/api/ai/{gid12}")


def test_pass_handling_server(client):
    """Verify server correctly exposes pass move and pass flag."""
    cfg = GameConfig(board_size=7, num_players=2)
    state = GameState(
        config=cfg,
        pawns=((6, 0), (0, 3)),
        walls_left=(0, 0),
        h_walls=frozenset([(5, 0)]),
        v_walls=frozenset([(5, 0)]),
        current=0,
    )
    gid = "test_pass_gid"
    sessions[gid] = Session(
        state=state,
        history=[state],
        history_moves=[],
        history_movers=[],
        opponents={2: RandomAgent()},
        opponent_specs={2: "random"},
        human_player=0,
        last_accessed=time.time(),
    )

    legal_resp = client.get(f"/api/legal/{gid}")
    assert legal_resp.status_code == 200
    moves = legal_resp.json()["moves"]
    assert moves == [{"type": "pass"}]

    move_resp = client.post(f"/api/move/{gid}", json={"move": {"type": "pass"}})
    assert move_resp.status_code == 200
    assert move_resp.json()["state"]["current"] == 2

    state_resp = client.get(f"/api/state/{gid}")
    assert state_resp.status_code == 200
    assert state_resp.json()["pass_flag"] is True


def test_static_files_served(client):
    """Web folder is served at root."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "QUORIDOR" in resp.text

    # Also check styles.css
    resp_css = client.get("/styles.css")
    assert resp_css.status_code == 200
    assert "--bone" in resp_css.text
