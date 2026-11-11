"""FastAPI server for the Quoridor web UI."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from quoridor import pathfinding, rules
from quoridor.agents import make_agent
from quoridor.agents.base import Agent
from quoridor.state import GameState
from quoridor.types import Move, move_from_dict, move_to_dict

app = FastAPI(title="Quoridor Server", description="Quoridor Game Server & Web UI Backend")

MAX_SESSIONS = 200
SESSION_IDLE_TIMEOUT_SECONDS = 2 * 3600  # 2 hours
ALLOWED_KEYS = {"depth", "iterations", "seed"}


@dataclass
class Session:
    state: GameState
    history: list[GameState]
    opponent: Agent
    opponent_spec: str
    human_player: int
    last_stats: dict[str, Any] | None = None
    last_accessed: float = field(default_factory=time.time)


# In-memory session store
sessions: dict[str, Session] = {}


def validate_opponent_spec(spec: str) -> None:
    """Validate opponent specification against an allowlist."""
    if not isinstance(spec, str) or not spec.strip():
        raise HTTPException(status_code=400, detail="invalid opponent spec: empty spec")

    parts = spec.strip().split(":", 1)
    name = parts[0].strip()
    kwargs: dict[str, Any] = {}

    if len(parts) == 2:
        for pair in parts[1].split(","):
            pair = pair.strip()
            if not pair:
                continue
            if "=" not in pair:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: expected key=value, got {pair!r}",
                )
            k, v_raw = pair.split("=", 1)
            k = k.strip()
            v_raw = v_raw.strip()
            if k not in ALLOWED_KEYS:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: key {k!r} is not allowed",
                )
            try:
                val = ast.literal_eval(v_raw)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: cannot parse value {v_raw!r} for key {k!r}",
                ) from exc
            kwargs[k] = val

    if name not in ("random", "greedy", "alphabeta", "mcts"):
        raise HTTPException(
            status_code=400,
            detail=f"invalid opponent spec: unknown agent name {name!r}",
        )

    if name in ("random", "greedy"):
        for k in kwargs:
            if k != "seed":
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: key {k!r} is not allowed for {name}",
                )
    elif name == "alphabeta":
        for k in kwargs:
            if k not in ("depth", "seed"):
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: key {k!r} is not allowed for alphabeta",
                )
        depth = kwargs.get("depth", 3)
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1 or depth > 4:
            raise HTTPException(
                status_code=400,
                detail="invalid opponent spec: alphabeta depth must be between 1 and 4",
            )
    elif name == "mcts":
        for k in kwargs:
            if k not in ("iterations", "seed"):
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid opponent spec: key {k!r} is not allowed for mcts",
                )
        iterations = kwargs.get("iterations", 500)
        if (
            not isinstance(iterations, int)
            or isinstance(iterations, bool)
            or iterations < 50
            or iterations > 1000
        ):
            raise HTTPException(
                status_code=400,
                detail="invalid opponent spec: mcts iterations must be between 50 and 1000",
            )


def _evict_stale_sessions() -> None:
    """Evict sessions idle for >2 hours, and ensure total sessions stay strictly under MAX_SESSIONS."""
    now = time.time()
    # 1. Delete sessions idle for > 2 hours
    stale_keys = [
        gid for gid, s in sessions.items()
        if now - s.last_accessed > SESSION_IDLE_TIMEOUT_SECONDS
    ]
    for gid in stale_keys:
        sessions.pop(gid, None)

    # 2. If at or above cap, evict oldest sessions
    if len(sessions) >= MAX_SESSIONS:
        sorted_sessions = sorted(sessions.items(), key=lambda item: item[1].last_accessed)
        num_to_evict = len(sessions) - MAX_SESSIONS + 1
        for i in range(num_to_evict):
            sessions.pop(sorted_sessions[i][0], None)


class NewGameRequest(BaseModel):
    opponent: str = "alphabeta:depth=3"
    human_player: int = 0


class MoveRequest(BaseModel):
    move: dict[str, Any]


@app.get("/api/health")
def api_health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Empty favicon response to prevent 404 logs."""
    return Response(content=b"", media_type="image/x-icon")


@app.post("/api/new")
def api_new(req: NewGameRequest) -> dict[str, Any]:
    """Start a new game session with a specified opponent and human player side."""
    if req.human_player not in (0, 1):
        raise HTTPException(status_code=400, detail="human_player must be 0 or 1")

    validate_opponent_spec(req.opponent)

    try:
        opponent = make_agent(req.opponent)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"invalid opponent spec '{req.opponent}': {exc}",
        ) from exc

    _evict_stale_sessions()

    initial_state = GameState.initial()
    game_id = uuid.uuid4().hex

    sessions[game_id] = Session(
        state=initial_state,
        history=[initial_state],
        opponent=opponent,
        opponent_spec=req.opponent,
        human_player=req.human_player,
        last_accessed=time.time(),
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
    session.last_accessed = time.time()
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

    last_human_idx = -1
    for i in range(len(session.history) - 1):
        if session.history[i].current == session.human_player:
            last_human_idx = i

    if last_human_idx >= 0:
        session.history = session.history[: last_human_idx + 1]
        session.state = session.history[-1]

    return {"state": session.state.to_dict()}


# Mount web directory if it exists
web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
