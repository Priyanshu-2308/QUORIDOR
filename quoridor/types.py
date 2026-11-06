"""Move types and (de)serialisation helpers (owner: Shubham)."""
from __future__ import annotations

from dataclasses import dataclass

Cell = tuple[int, int]


@dataclass(frozen=True)
class PawnMove:
    """Move the current pawn to cell ``to``."""
    to: Cell


@dataclass(frozen=True)
class WallMove:
    """Place a wall at ``(r, c)`` with orientation ``o`` ("H" or "V")."""
    r: int
    c: int
    o: str  # "H" or "V"


Move = PawnMove | WallMove


def move_to_dict(m: Move) -> dict:
    """Convert a move to its JSON-friendly dict form."""
    if isinstance(m, PawnMove):
        return {"type": "pawn", "to": [m.to[0], m.to[1]]}
    if isinstance(m, WallMove):
        return {"type": "wall", "r": m.r, "c": m.c, "o": m.o}
    raise TypeError(f"not a move: {m!r}")


def move_from_dict(d: dict) -> Move:
    """Build a move from its dict form. Raises ValueError on invalid input."""
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
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid move dict: {d!r}") from exc
    raise ValueError(f"unknown move type: {kind!r}")


def move_to_str(m: Move) -> str:
    """Short text form: "P(7,4)" for pawn moves, "H(3,2)" / "V(3,2)" for walls."""
    if isinstance(m, PawnMove):
        return f"P({m.to[0]},{m.to[1]})"
    if isinstance(m, WallMove):
        return f"{m.o}({m.r},{m.c})"
    raise TypeError(f"not a move: {m!r}")
