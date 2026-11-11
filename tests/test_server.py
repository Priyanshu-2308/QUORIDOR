"""Tests for FastAPI backend server (owner: Priyanshu)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_server_flow(client):
    # 1. 404 on unknown game_id
    resp = client.get("/api/state/nonexistent_game_id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "game not found"

    # 2. Reject invalid opponent spec with 400
    resp = client.post("/api/new", json={"opponent": "unknown_ai_spec:xyz=123", "human_player": 0})
    assert resp.status_code == 400
    assert "invalid opponent spec" in resp.json()["detail"]

    # 3. Create a valid game with greedy opponent
    resp = client.post("/api/new", json={"opponent": "greedy", "human_player": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "game_id" in data
    assert "state" in data
    assert data["human_player"] == 0
    game_id = data["game_id"]

    # 4. Read state
    resp = client.get(f"/api/state/{game_id}")
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["current"] == 0
    assert state["pawns"] == [[8, 4], [0, 4]]

    # 5. Read legal moves
    resp = client.get(f"/api/legal/{game_id}")
    assert resp.status_code == 200
    moves = resp.json()["moves"]
    assert len(moves) == 131  # 3 pawn moves + 128 wall moves

    # 6. Reject illegal move
    illegal_move = {"type": "pawn", "to": [0, 0]}
    resp = client.post(f"/api/move/{game_id}", json={"move": illegal_move})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "illegal move"

    # 7. Make a legal pawn move: P0 moves (8, 4) -> (7, 4)
    legal_move = {"type": "pawn", "to": [7, 4]}
    resp = client.post(f"/api/move/{game_id}", json={"move": legal_move})
    assert resp.status_code == 200
    new_state = resp.json()["state"]
    assert new_state["pawns"][0] == [7, 4]
    assert new_state["current"] == 1  # AI turn now

    # 8. Human tries to move again out of turn -> 400
    resp = client.post(f"/api/move/{game_id}", json={"move": {"type": "pawn", "to": [6, 4]}})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "not human's turn"

    # 9. Fetch paths
    resp = client.get(f"/api/paths/{game_id}")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert len(paths) == 2
    # P0 path starts at (7, 4) and reaches row 0
    assert paths[0][0] == [7, 4]
    assert paths[0][-1][0] == 0
    # P1 path starts at (0, 4) and reaches row 8
    assert paths[1][0] == [0, 4]
    assert paths[1][-1][0] == 8

    # 10. Request AI move
    resp = client.post(f"/api/ai/{game_id}")
    assert resp.status_code == 200
    ai_data = resp.json()
    assert "move" in ai_data
    assert "state" in ai_data
    assert "stats" in ai_data
    ai_state = ai_data["state"]
    assert ai_state["current"] == 0  # Back to human's turn

    # 11. Undo: reverts AI move and human move back to initial position
    resp = client.post(f"/api/undo/{game_id}")
    assert resp.status_code == 200
    undone_state = resp.json()["state"]
    assert undone_state["pawns"] == [[8, 4], [0, 4]]
    assert undone_state["current"] == 0

    # 12. Undo at start is a no-op
    resp = client.post(f"/api/undo/{game_id}")
    assert resp.status_code == 200
    assert resp.json()["state"]["pawns"] == [[8, 4], [0, 4]]


def test_static_files_served(client):
    """Verify web/ folder is served as static files at root /."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "QUORIDOR" in resp.text
    assert "canvas-container" in resp.text

    # Also check styles.css
    resp_css = client.get("/styles.css")
    assert resp_css.status_code == 200
    assert "--bone" in resp_css.text

