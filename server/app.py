"""FastAPI server for the Quoridor web UI (owner: Priyanshu)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from quoridor import pathfinding, rules
from quoridor.agents import make_agent
from quoridor.agents.base import Agent
from quoridor.state import GameState
from quoridor.types import Move, move_from_dict, move_to_dict

app = FastAPI(title="Quoridor Server", description="Quoridor Game Server & Web UI Backend")

# Allow CORS for development if opened from separate port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Session:
    state: GameState
    history: list[GameState]
    opponent: Agent
    opponent_spec: str
    human_player: int
    last_stats: dict[str, Any] | None = None


# In-memory session store
sessions: dict[str, Session] = {}


class NewGameRequest(BaseModel):
    opponent: str = "alphabeta:depth=3"
    human_player: int = 0


class MoveRequest(BaseModel):
    move: dict[str, Any]


@app.post("/api/new")
def api_new(req: NewGameRequest) -> dict[str, Any]:
    """Start a new game session with a specified opponent and human player side."""
    if req.human_player not in (0, 1):
        raise HTTPException(status_code=400, detail="human_player must be 0 or 1")

    try:
        opponent = make_agent(req.opponent)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"invalid opponent spec '{req.opponent}': {exc}",
        ) from exc

    initial_state = GameState.initial()
    game_id = uuid.uuid4().hex

    sessions[game_id] = Session(
        state=initial_state,
        history=[initial_state],
        opponent=opponent,
        opponent_spec=req.opponent,
        human_player=req.human_player,
    )

    return {
        "game_id": game_id,
        "state": initial_state.to_dict(),
        "human_player": req.human_player,
    }


def _get_session(game_id: str) -> Session:
    session = sessions.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="game not found")
    return session


@app.get("/api/state/{game_id}")
def api_state(game_id: str) -> dict[str, Any]:
    """Return the current game state for the given session."""
    session = _get_session(game_id)
    return {"state": session.state.to_dict()}


@app.get("/api/legal/{game_id}")
def api_legal(game_id: str) -> dict[str, Any]:
    """Return the list of all legal moves for the current player to move."""
    session = _get_session(game_id)
    if session.state.is_terminal():
        return {"moves": []}
    legal = rules.legal_moves(session.state)
    return {"moves": [move_to_dict(m) for m in legal]}


@app.post("/api/move/{game_id}")
def api_move(game_id: str, req: MoveRequest) -> dict[str, Any]:
    """Apply a move by the human player."""
    session = _get_session(game_id)

    if session.state.is_terminal():
        raise HTTPException(status_code=400, detail="game is over")

    if session.state.current != session.human_player:
        raise HTTPException(status_code=400, detail="not human's turn")

    try:
        move = move_from_dict(req.move)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"illegal move: {exc}") from exc

    if not rules.is_legal(session.state, move):
        raise HTTPException(status_code=400, detail="illegal move")

    new_state = session.state.apply(move)
    session.state = new_state
    session.history.append(new_state)

    return {"state": new_state.to_dict()}


@app.post("/api/ai/{game_id}")
def api_ai(game_id: str) -> dict[str, Any]:
    """Trigger the AI opponent to compute and make a move."""
    session = _get_session(game_id)

    if session.state.is_terminal():
        raise HTTPException(status_code=400, detail="game is over")

    if session.state.current == session.human_player:
        raise HTTPException(status_code=400, detail="not AI's turn")

    move = session.opponent.choose_move(session.state)
    stats = getattr(session.opponent, "last_stats", {})
    session.last_stats = stats

    new_state = session.state.apply(move)
    session.state = new_state
    session.history.append(new_state)

    return {
        "move": move_to_dict(move),
        "state": new_state.to_dict(),
        "stats": stats,
    }


@app.get("/api/paths/{game_id}")
def api_paths(game_id: str) -> dict[str, Any]:
    """Return shortest paths for player 0 and player 1."""
    session = _get_session(game_id)
    p0_path = pathfinding.shortest_path(session.state, 0)
    p1_path = pathfinding.shortest_path(session.state, 1)

    p0_coords = [[r, c] for r, c in p0_path] if p0_path else []
    p1_coords = [[r, c] for r, c in p1_path] if p1_path else []

    return {"paths": [p0_coords, p1_coords]}


@app.post("/api/undo/{game_id}")
def api_undo(game_id: str) -> dict[str, Any]:
    """Undo back to the last position in which it was the human's turn before the most recent human move."""
    session = _get_session(game_id)

    # Find the transition history where the human made a move
    # history[i] -> history[i+1] is a move made by history[i].current
    last_human_idx = -1
    for i in range(len(session.history) - 1):
        if session.history[i].current == session.human_player:
            last_human_idx = i

    if last_human_idx >= 0:
        # Revert to state before that human move
        session.history = session.history[: last_human_idx + 1]
        session.state = session.history[-1]

    return {"state": session.state.to_dict()}


# Mount web directory if it exists
web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
