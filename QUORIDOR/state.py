"""Immutable game state (owner: Shubham)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .constants import BOARD_SIZE, GOAL_ROW, H, START, V, WALLS_PER_PLAYER
from .types import Cell, Move, PawnMove, WallMove


@dataclass(frozen=True)
class GameState:
    """Immutable Quoridor position. ``apply`` returns a new state."""
    pawns: tuple[Cell, Cell]
    walls_left: tuple[int, int]
    h_walls: frozenset[tuple[int, int]]
    v_walls: frozenset[tuple[int, int]]
    current: int
    turn_count: int = 0

    @classmethod
    def initial(cls) -> "GameState":
        """The starting position."""
        return cls(
            pawns=(START[0], START[1]),
            walls_left=(WALLS_PER_PLAYER, WALLS_PER_PLAYER),
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=0,
            turn_count=0,
        )

    def is_blocked(self, a: Cell, b: Cell) -> bool:
        """True if a wall (or the board edge) blocks the step between adjacent cells a and b."""
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
        """Return the state after ``move``. No legality checks."""
        nxt = 1 - self.current
        if isinstance(move, PawnMove):
            pawns = list(self.pawns)
            pawns[self.current] = (move.to[0], move.to[1])
            return replace(self, pawns=(pawns[0], pawns[1]), current=nxt,
                           turn_count=self.turn_count + 1)
        if isinstance(move, WallMove):
            walls_left = list(self.walls_left)
            walls_left[self.current] -= 1
            wall = frozenset([(move.r, move.c)])
            h_walls, v_walls = self.h_walls, self.v_walls
            if move.o == H:
                h_walls = h_walls | wall
            elif move.o == V:
                v_walls = v_walls | wall
            else:
                raise ValueError(f"invalid wall orientation: {move.o!r}")
            return replace(self, walls_left=(walls_left[0], walls_left[1]),
                           h_walls=h_walls, v_walls=v_walls, current=nxt,
                           turn_count=self.turn_count + 1)
        raise TypeError(f"not a move: {move!r}")

    def winner(self) -> int | None:
        """0 or 1 if that player's pawn is on its goal row, else None."""
        if self.pawns[0][0] == GOAL_ROW[0]:
            return 0
        if self.pawns[1][0] == GOAL_ROW[1]:
            return 1
        return None

    def is_terminal(self) -> bool:
        """True once someone has won."""
        return self.winner() is not None

    def key(self) -> tuple:
        """Hashable identity of the position."""
        return (self.pawns, self.walls_left, self.h_walls, self.v_walls, self.current)

    def legal_moves(self) -> list[Move]:
        """All legal moves for the current player (delegates to rules)."""
        from .rules import legal_moves
        return legal_moves(self)

    def to_dict(self) -> dict:
        """JSON form of the state (wall lists sorted for stable output)."""
        return {
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
        """Rebuild a state from ``to_dict`` output (the "winner" key is ignored)."""
        p0, p1 = d["pawns"]
        return cls(
            pawns=((p0[0], p0[1]), (p1[0], p1[1])),
            walls_left=(d["walls_left"][0], d["walls_left"][1]),
            h_walls=frozenset((w[0], w[1]) for w in d["h_walls"]),
            v_walls=frozenset((w[0], w[1]) for w in d["v_walls"]),
            current=d["current"],
            turn_count=d.get("turn_count", 0),
        )

    def render(self) -> str:
        """ASCII board for debugging: 0/1 pawns, '.' empty, '-' / '|' walls."""
        size = 2 * BOARD_SIZE - 1
        grid = [[" "] * size for _ in range(size)]
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                grid[2 * r][2 * c] = "."
        for pl, (r, c) in enumerate(self.pawns):
            grid[2 * r][2 * c] = str(pl)
        for r, c in self.h_walls:  # spans columns c and c+1 in groove below row r
            for k in range(3):
                grid[2 * r + 1][2 * c + k] = "-"
        for r, c in self.v_walls:  # spans rows r and r+1 in groove right of column c
            for k in range(3):
                grid[2 * r + k][2 * c + 1] = "|"
        header = "  " + " ".join(str(c) for c in range(BOARD_SIZE))
        lines = [header]
        for i, row in enumerate(grid):
            label = str(i // 2) if i % 2 == 0 else " "
            lines.append(f"{label} " + "".join(row))
        lines.append(f"walls left: P0={self.walls_left[0]} P1={self.walls_left[1]}  "
                     f"to move: P{self.current}  turn: {self.turn_count}")
        return "\n".join(lines)
