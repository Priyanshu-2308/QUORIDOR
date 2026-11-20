"""FastAPI server for dynamic-board Quoridor."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import threading
import time
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from quoridor_n import pathfinding, rules
from quoridor_n.agents import make_agent
from quoridor_n.agents.base import Agent
from quoridor_n.config import GameConfig
from quoridor_n.runner import compute_ranks
from quoridor_n.state import GameState
from quoridor_n.types import Move, move_from_dict, move_to_dict

app = FastAPI(title="Quoridor Server", description="Dynamic-board Quoridor Game Server & Web UI Backend")

MAX_SESSIONS = 200
SESSION_IDLE_TIMEOUT_SECONDS = 2 * 3600  # 2 hours
SEARCH_SEMAPHORE = threading.Semaphore(4)

ALLOWED_KEYS = {
    "depth",
    "iterations",
    "seed",
    "wall_prob",
    "wall_target",
    "wall_cap",
    "use_tt",
    "use_move_ordering",
    "use_wall_pruning",
    "eval_mode",
    "rollout_policy",
    "rollout_greedy_share",
    "cutoff_scoring",
    "c",
}

STRENGTH_TIERS = {
    "alphabeta": {
        "easy": "alphabeta:depth=1",
        "medium": "alphabeta:depth=2",
        "hard": "alphabeta:depth=3",
    },
    "paranoid": {
        "easy": "paranoid:depth=1",
        "medium": "paranoid:depth=2",
        "hard": "paranoid:depth=3",
    },
    "maxn": {
        "easy": "maxn:depth=1",
        "medium": "maxn:depth=2",
        "hard": "maxn:depth=2",
    },
    "mcts": {
        "easy": "mcts:iterations=50",
        "medium": "mcts:iterations=200",
        "hard": "mcts:iterations=600",
    },
}


@dataclass
class Session:
    state: GameState
    history: list[GameState]
    history_moves: list[Move]
    history_movers: list[int]
    opponents: dict[int, Agent]
    opponent_specs: dict[int, str]
    human_player: int
    last_stats: dict[str, Any] | None = None
    last_accessed: float = field(default_factory=time.time)


sessions: dict[str, Session] = {}


def validate_opponent_spec(spec: str) -> None:
    """Check opponent spec against allowlist and bound parameters."""
    if not isinstance(spec, str) or not spec.strip():
        raise HTTPException(status_code=400, detail="invalid opponent spec: empty spec")

    parts = spec.strip().split(":", 1)
    name = parts[0].strip().lower()
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

    if name not in ("random", "greedy", "alphabeta", "paranoid", "maxn", "mcts"):
        raise HTTPException(
            status_code=400,
            detail=f"invalid opponent spec: unknown agent name {name!r}",
        )

    if name in ("alphabeta", "paranoid"):
        depth = kwargs.get("depth", 3)
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1 or depth > 4:
            raise HTTPException(
                status_code=400,
                detail=f"invalid opponent spec: {name} depth must be between 1 and 4",
            )
    elif name == "maxn":
        depth = kwargs.get("depth", 2)
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1 or depth > 3:
            raise HTTPException(
                status_code=400,
                detail="invalid opponent spec: maxn depth must be between 1 and 3",
            )
    elif name == "mcts":
        iterations = kwargs.get("iterations", 500)
        if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 50 or iterations > 2000:
            raise HTTPException(
                status_code=400,
                detail="invalid opponent spec: mcts iterations must be between 50 and 2000",
            )


def _evict_stale_sessions() -> None:
    """Evict sessions idle for >2 hours, keeping count strictly under MAX_SESSIONS."""
    now = time.time()
    stale_keys = [
        gid for gid, s in sessions.items()
        if now - s.last_accessed > SESSION_IDLE_TIMEOUT_SECONDS
    ]
    for gid in stale_keys:
        sessions.pop(gid, None)

    if len(sessions) >= MAX_SESSIONS:
        sorted_sessions = sorted(sessions.items(), key=lambda item: item[1].last_accessed)
        num_to_evict = len(sessions) - MAX_SESSIONS + 1
        for i in range(num_to_evict):
            sessions.pop(sorted_sessions[i][0], None)


class NewGameRequest(BaseModel):
    board_size: int = 9
    num_players: int = 2
    human_player: int = 0
    opponent: str | None = None
    opponents: list[str] | None = None


class MoveRequest(BaseModel):
    move: dict[str, Any]


@app.get("/api/health")
def api_health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Empty favicon."""
    return Response(content=b"", media_type="image/x-icon")


@app.post("/api/new")
def api_new(req: NewGameRequest) -> dict[str, Any]:
    """Start a new game session with dynamic board size and player count."""
    if not (7 <= req.board_size <= 12):
        raise HTTPException(status_code=400, detail="board_size must be between 7 and 12")
    if req.num_players not in (2, 4):
        raise HTTPException(status_code=400, detail="num_players must be 2 or 4")

    config = GameConfig(board_size=req.board_size, num_players=req.num_players)
    if req.human_player not in config.players:
        raise HTTPException(
            status_code=400,
            detail=f"human_player must be one of active seats {list(config.players)}",
        )

    ai_seats = [p for p in config.players if p != req.human_player]

    if req.opponents is not None:
        if len(req.opponents) != len(ai_seats):
            raise HTTPException(
                status_code=400,
                detail=f"expected {len(ai_seats)} opponents, got {len(req.opponents)}",
            )
        spec_map = {ai_seats[i]: req.opponents[i] for i in range(len(ai_seats))}
    elif req.opponent is not None:
        if len(ai_seats) == 1:
            spec_map = {ai_seats[0]: req.opponent}
        else:
            raise HTTPException(
                status_code=400,
                detail="multiple opponents required for 4-player game",
            )
    else:
        default_spec = "paranoid:depth=2" if req.num_players == 4 else "alphabeta:depth=3"
        spec_map = {p: default_spec for p in ai_seats}

    for spec in spec_map.values():
        validate_opponent_spec(spec)

    try:
        opponents = {p: make_agent(spec) for p, spec in spec_map.items()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid opponent: {exc}") from exc

    _evict_stale_sessions()

    initial_state = GameState.initial(config)
    game_id = uuid.uuid4().hex

    sessions[game_id] = Session(
        state=initial_state,
        history=[initial_state],
        history_moves=[],
        history_movers=[],
        opponents=opponents,
        opponent_specs=spec_map,
        human_player=req.human_player,
        last_accessed=time.time(),
    )

    return {
        "game_id": game_id,
        "state": initial_state.to_dict(),
        "human_player": req.human_player,
        "board_size": req.board_size,
        "num_players": req.num_players,
        "players": list(config.players),
        "opponents": list(spec_map.values()),
    }


def _get_session(game_id: str) -> Session:
    session = sessions.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="game not found")
    session.last_accessed = time.time()
    return session


@app.get("/api/state/{game_id}")
def api_state(game_id: str) -> dict[str, Any]:
    """Return the current game state and ranks."""
    session = _get_session(game_id)
    st = session.state
    is_term = st.is_terminal()
    ranks = compute_ranks(st) if is_term else None

    pass_flag = False
    if session.history_moves:
        last_m = session.history_moves[-1]
        pass_flag = getattr(last_m, "type", None) == "pass" or last_m.__class__.__name__ == "PassMove"

    return {
        "state": st.to_dict(),
        "ranks": ranks,
        "pass_flag": pass_flag,
        "human_player": session.human_player,
        "last_move": move_to_dict(session.history_moves[-1]) if session.history_moves else None,
        "last_mover": session.history_movers[-1] if session.history_movers else None,
        "is_terminal": is_term,
    }


@app.get("/api/legal/{game_id}")
def api_legal(game_id: str) -> dict[str, Any]:
    """Return all legal moves for state.current."""
    session = _get_session(game_id)
    if session.state.is_terminal():
        return {"moves": []}
    legal = rules.legal_moves(session.state)
    return {"moves": [move_to_dict(m) for m in legal]}


@app.post("/api/move/{game_id}")
def api_move(game_id: str, req: MoveRequest) -> dict[str, Any]:
    """Apply a move chosen by the human player."""
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

    mover = session.state.current
    new_state = session.state.apply(move)
    session.state = new_state
    session.history.append(new_state)
    session.history_moves.append(move)
    session.history_movers.append(mover)

    is_term = new_state.is_terminal()
    ranks = compute_ranks(new_state) if is_term else None

    return {
        "state": new_state.to_dict(),
        "ranks": ranks,
        "is_terminal": is_term,
    }


@app.post("/api/ai/{game_id}")
def api_ai(game_id: str) -> dict[str, Any]:
    """Trigger the computer opponent for state.current."""
    session = _get_session(game_id)

    if session.state.is_terminal():
        raise HTTPException(status_code=400, detail="game is over")

    mover = session.state.current
    if mover == session.human_player:
        raise HTTPException(status_code=400, detail="not AI's turn")

    opponent = session.opponents.get(mover)
    if opponent is None:
        raise HTTPException(status_code=500, detail=f"no agent registered for seat {mover}")

    with SEARCH_SEMAPHORE:
        move = opponent.choose_move(session.state)

    stats = getattr(opponent, "last_stats", {})
    session.last_stats = stats

    new_state = session.state.apply(move)
    session.state = new_state
    session.history.append(new_state)
    session.history_moves.append(move)
    session.history_movers.append(mover)

    is_term = new_state.is_terminal()
    ranks = compute_ranks(new_state) if is_term else None

    return {
        "move": move_to_dict(move),
        "mover": mover,
        "state": new_state.to_dict(),
        "stats": stats,
        "ranks": ranks,
        "is_terminal": is_term,
    }


@app.get("/api/paths/{game_id}")
def api_paths(game_id: str) -> dict[str, Any]:
    """Return shortest paths for all active players."""
    session = _get_session(game_id)
    cfg = session.state.config
    paths_list = []
    paths_dict = {}

    for p in cfg.players:
        sp = pathfinding.shortest_path(session.state, p)
        coords = [[r, c] for r, c in sp] if sp else []
        paths_list.append(coords)
        paths_dict[str(p)] = coords

    return {"paths": paths_list, "player_paths": paths_dict}


@app.post("/api/undo/{game_id}")
def api_undo(game_id: str) -> dict[str, Any]:
    """Undo back to the start of the human's previous turn."""
    session = _get_session(game_id)

    target_idx = -1
    for i in range(len(session.history) - 1):
        if session.history[i].current == session.human_player:
            target_idx = i

    if target_idx >= 0:
        session.history = session.history[: target_idx + 1]
        session.history_moves = session.history_moves[:target_idx]
        session.history_movers = session.history_movers[:target_idx]
        session.state = session.history[-1]

    return {"state": session.state.to_dict()}


web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
