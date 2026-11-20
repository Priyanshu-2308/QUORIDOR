"""Move types and serialization helpers for dynamic Quoridor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

Cell = tuple[int, int]


@dataclass(frozen=True)
class PawnMove:
    """Move pawn to cell ``to``."""
    to: Cell


@dataclass(frozen=True)
class WallMove:
    """Place a wall at groove ``(r, c)`` with orientation ``o`` ('H' or 'V')."""
    r: int
    c: int
    o: str  # 'H' or 'V'


@dataclass(frozen=True)
class PassMove:
    """Pass turn when a player has zero legal pawn moves and zero legal walls."""
    pass


Move = Union[PawnMove, WallMove, PassMove]


def move_to_dict(m: Move) -> dict:
    """Convert a move to its JSON-friendly dictionary form."""
    if isinstance(m, PawnMove):
        return {"type": "pawn", "to": [m.to[0], m.to[1]]}
    if isinstance(m, WallMove):
        return {"type": "wall", "r": m.r, "c": m.c, "o": m.o}
    if isinstance(m, PassMove):
        return {"type": "pass"}
    raise TypeError(f"not a move: {m!r}")


def move_from_dict(d: dict) -> Move:
    """Reconstruct a Move from its dictionary form."""
    try:
        kind = d["type"]
        if kind == "pawn":
            r, c = d["to"]
            return PawnMove((int(r), int(c)))
        if kind == "wall":
            o = d["o"]
            if o not in ("H", "V"):
                raise ValueError(f"invalid wall orientation: {o!r}")
            return WallMove(int(d["r"]), int(d["c"]), o)
        if kind == "pass":
            return PassMove()
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid move dict: {d!r}") from exc
    raise ValueError(f"unknown move type: {kind!r}")


def move_to_str(m: Move) -> str:
    """Concise string format: P(r,c), H(r,c), V(r,c), or PASS."""
    if isinstance(m, PawnMove):
        return f"P({m.to[0]},{m.to[1]})"
    if isinstance(m, WallMove):
        return f"{m.o}({m.r},{m.c})"
    if isinstance(m, PassMove):
        return "PASS"
    raise TypeError(f"not a move: {m!r}")


def move_from_str(s: str) -> Move:
    """Parse concise string: P(r,c), H(r,c), V(r,c), or PASS."""
    s = s.strip()
    if s == "PASS":
        return PassMove()
    if s.startswith("P(") and s.endswith(")"):
        parts = s[2:-1].split(",")
        return PawnMove((int(parts[0]), int(parts[1])))
    if (s.startswith("H(") or s.startswith("V(")) and s.endswith(")"):
        o = s[0]
        parts = s[2:-1].split(",")
        return WallMove(int(parts[0]), int(parts[1]), o)
    raise ValueError(f"cannot parse move string: {s!r}")
