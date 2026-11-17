"""Types for quoridor_n, extending quoridor.types with PassMove for cul-de-sacs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from quoridor.types import (
    Cell,
    PawnMove,
    WallMove,
    move_to_dict as _base_to_dict,
    move_from_dict as _base_from_dict,
    move_to_str as _base_to_str,
)


@dataclass(frozen=True)
class PassMove:
    """Pass turn when a player is completely blocked by pawns/walls and has 0 walls."""
    pass


Move = Union[PawnMove, WallMove, PassMove]


def move_to_dict(m: Move) -> dict:
    if isinstance(m, PassMove):
        return {"type": "pass"}
    return _base_to_dict(m)


def move_from_dict(d: dict) -> Move:
    if d.get("type") == "pass":
        return PassMove()
    return _base_from_dict(d)


def move_to_str(m: Move) -> str:
    if isinstance(m, PassMove):
        return "PASS"
    return _base_to_str(m)


__all__ = [
    "Cell",
    "PawnMove",
    "WallMove",
    "PassMove",
    "Move",
    "move_to_dict",
    "move_from_dict",
    "move_to_str",
]

