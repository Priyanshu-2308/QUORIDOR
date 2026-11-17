"""Immutable game state for four-player and two-player Quoridor."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .constants import (
    BOARD_SIZE,
    DEFAULT_WALLS_2P,
    DEFAULT_WALLS_4P,
    H,
    START,
    V,
    goal_reached,
)
from .types import Cell, Move, PawnMove, WallMove

if TYPE_CHECKING:
    from .render import render_board


@dataclass(frozen=True)
class GameState:
    """Immutable Quoridor position for 2 or 4 players."""
    num_players: int
    pawns: tuple[Cell, ...]
    walls_left: tuple[int, ...]
    h_walls: frozenset[tuple[int, int]]
    v_walls: frozenset[tuple[int, int]]
    current: int
    turn_count: int = 0
    players: tuple[int, ...] = (0, 1, 2, 3)

    @classmethod
    def initial(cls, num_players: int = 4, walls_per_player: int | None = None) -> "GameState":
        """Construct the starting position for 4 or 2 players."""
        if num_players == 4:
            players = (0, 1, 2, 3)
            walls = DEFAULT_WALLS_4P if walls_per_player is None else walls_per_player
            pawns = (START[0], START[1], START[2], START[3])
            walls_left = (walls, walls, walls, walls)
            current = 0
        elif num_players == 2:
            players = (0, 2)
            walls = DEFAULT_WALLS_2P if walls_per_player is None else walls_per_player
            pawns = (START[0], START[2])
            walls_left = (walls, walls)
            current = 0
        else:
            raise ValueError(f"num_players must be 2 or 4, got {num_players!r}")

        return cls(
            num_players=num_players,
            pawns=pawns,
            walls_left=walls_left,
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=current,
            turn_count=0,
            players=players,
        )

    def player_index(self, player: int) -> int:
        """Map a player ID (0..3) to its internal tuple index."""
        if self.num_players == 4:
            return player
        return 0 if player == 0 else 1

    def pawn(self, player: int) -> Cell:
        """Return the coordinate (r, c) of the specified player."""
        return self.pawns[self.player_index(player)]

    def walls(self, player: int) -> int:
        """Return the number of remaining walls for the specified player."""
        return self.walls_left[self.player_index(player)]

    def is_blocked(self, a: Cell, b: Cell) -> bool:
        """True if a wall or board edge blocks movement between adjacent cells a and b."""
        for r, c in (a, b):
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
                return True
        (ar, ac), (br, bc) = a, b
        if ar == br and abs(ac - bc) == 1:  # horizontal step
            r, c = ar, min(ac, bc)
            return (r, c) in self.v_walls or (r - 1, c) in self.v_walls
        if ac == bc and abs(ar - br) == 1:  # vertical step
            r, c = min(ar, br), ac
            return (r, c) in self.h_walls or (r, c - 1) in self.h_walls
        raise ValueError(f"cells are not adjacent: {a}, {b}")

    def apply(self, move: Move) -> "GameState":
        """Return the new position after applying move. Legality is assumed checked."""
        curr_idx = self.player_index(self.current)
        next_player = self.players[(curr_idx + 1) % self.num_players]

        if isinstance(move, PawnMove):
            new_pawns = list(self.pawns)
            new_pawns[curr_idx] = (move.to[0], move.to[1])
            return replace(
                self,
                pawns=tuple(new_pawns),
                current=next_player,
                turn_count=self.turn_count + 1,
            )

        if isinstance(move, WallMove):
            new_walls_left = list(self.walls_left)
            new_walls_left[curr_idx] -= 1
            wall = frozenset([(move.r, move.c)])
            h_walls, v_walls = self.h_walls, self.v_walls
            if move.o == H:
                h_walls = h_walls | wall
            elif move.o == V:
                v_walls = v_walls | wall
            else:
                raise ValueError(f"invalid wall orientation: {move.o!r}")

            return replace(
                self,
                walls_left=tuple(new_walls_left),
                h_walls=h_walls,
                v_walls=v_walls,
                current=next_player,
                turn_count=self.turn_count + 1,
            )

        raise TypeError(f"not a move: {move!r}")

    def winner(self) -> int | None:
        """Return the ID of the winner if any player reached their goal, else None."""
        for p in self.players:
            if goal_reached(p, self.pawn(p)):
                return p
        return None

    def is_terminal(self) -> bool:
        """True if someone has reached their goal."""
        return self.winner() is not None

    def key(self) -> tuple:
        """Hashable identity of the game position."""
        return (self.players, self.pawns, self.walls_left, self.h_walls, self.v_walls, self.current)

    def legal_moves(self) -> list[Move]:
        """All legal moves for the current player."""
        from .rules import legal_moves
        return legal_moves(self)

    def to_dict(self) -> dict:
        """JSON serialisable representation of the state."""
        return {
            "num_players": self.num_players,
            "players": list(self.players),
            "pawns": [list(p) for p in self.pawns],
            "walls_left": list(self.walls_left),
            "h_walls": [list(w) for w in sorted(self.h_walls)],
            "v_walls": [list(w) for w in sorted(self.v_walls)],
            "current": self.current,
            "turn_count": self.turn_count,
            "winner": self.winner(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        """Reconstruct GameState from dictionary."""
        num_players = d.get("num_players", len(d["pawns"]))
        players = tuple(d.get("players", (0, 1, 2, 3) if num_players == 4 else (0, 2)))
        pawns = tuple((p[0], p[1]) for p in d["pawns"])
        walls_left = tuple(d["walls_left"])
        h_walls = frozenset((w[0], w[1]) for w in d["h_walls"])
        v_walls = frozenset((w[0], w[1]) for w in d["v_walls"])
        current = d["current"]
        turn_count = d.get("turn_count", 0)

        return cls(
            num_players=num_players,
            players=players,
            pawns=pawns,
            walls_left=walls_left,
            h_walls=h_walls,
            v_walls=v_walls,
            current=current,
            turn_count=turn_count,
        )

    def render(self) -> str:
        """ASCII board representation."""
        from .render import render_board
        return render_board(self)
