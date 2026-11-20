"""Immutable game state for dynamic Quoridor."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .config import GameConfig
from .constants import H, V, goal_reached, start_cell
from .types import Cell, Move, PawnMove, WallMove, PassMove

if TYPE_CHECKING:
    from .render import render_board


@dataclass(frozen=True)
class GameState:
    """Immutable Quoridor game state."""
    config: GameConfig
    pawns: tuple[Cell, ...]
    walls_left: tuple[int, ...]
    h_walls: frozenset[tuple[int, int]]
    v_walls: frozenset[tuple[int, int]]
    current: int
    turn_count: int = 0
    pass_count: int = 0

    @classmethod
    def initial(cls, config: GameConfig | None = None) -> "GameState":
        """Construct the starting position from a GameConfig."""
        if config is None:
            config = GameConfig()

        players = config.players
        pawns = tuple(start_cell(p, config.board_size) for p in players)
        assert config.walls_per_player is not None
        walls_left = tuple(config.walls_per_player for _ in players)

        return cls(
            config=config,
            pawns=pawns,
            walls_left=walls_left,
            h_walls=frozenset(),
            v_walls=frozenset(),
            current=players[0],
            turn_count=0,
            pass_count=0,
        )

    @property
    def num_players(self) -> int:
        return self.config.num_players

    @property
    def board_size(self) -> int:
        return self.config.board_size

    @property
    def players(self) -> tuple[int, ...]:
        return self.config.players

    def player_index(self, player: int) -> int:
        """Map player ID to its tuple index in pawns and walls_left."""
        if self.config.num_players == 4:
            if 0 <= player < 4:
                return player
        elif self.config.num_players == 2:
            if player == 0:
                return 0
            if player == 2:
                return 1
        raise ValueError(f"invalid player {player} for players {self.config.players}")

    def pawn(self, player: int) -> Cell:
        """Position (row, col) of the given player."""
        return self.pawns[self.player_index(player)]

    def walls(self, player: int) -> int:
        """Remaining walls for the given player."""
        return self.walls_left[self.player_index(player)]

    def is_blocked(self, a: Cell, b: Cell) -> bool:
        """True if moving between adjacent cells a and b is blocked by board edges or walls."""
        n = self.config.board_size
        for r, c in (a, b):
            if not (0 <= r < n and 0 <= c < n):
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
        """Return the next state after applying move (legality assumed verified)."""
        curr_idx = self.player_index(self.current)
        next_player = self.config.players[(curr_idx + 1) % self.config.num_players]

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

        if isinstance(move, PassMove):
            return replace(
                self,
                current=next_player,
                turn_count=self.turn_count + 1,
                pass_count=self.pass_count + 1,
            )

        raise TypeError(f"not a move: {move!r}")

    def winner(self) -> int | None:
        """Player ID of the winner if someone has reached their goal side, else None."""
        bs = self.config.board_size
        for p in self.config.players:
            if goal_reached(p, self.pawn(p), bs):
                return p
        return None

    def is_terminal(self) -> bool:
        """True if someone won or the game reached max_turns."""
        if self.winner() is not None:
            return True
        if self.config.max_turns is not None and self.turn_count >= self.config.max_turns:
            return True
        return False

    def key(self) -> tuple:
        """Hashable identity of the game position."""
        return (
            self.config.board_size,
            self.config.num_players,
            self.pawns,
            self.walls_left,
            self.h_walls,
            self.v_walls,
            self.current,
        )

    def legal_moves(self) -> list[Move]:
        """All legal moves for the current player."""
        from .rules import legal_moves
        return legal_moves(self)

    def to_dict(self) -> dict:
        """JSON serializable representation."""
        return {
            "board_size": self.config.board_size,
            "num_players": self.config.num_players,
            "walls_per_player": self.config.walls_per_player,
            "max_turns": self.config.max_turns,
            "players": list(self.config.players),
            "pawns": [list(p) for p in self.pawns],
            "walls_left": list(self.walls_left),
            "h_walls": [list(w) for w in sorted(self.h_walls)],
            "v_walls": [list(w) for w in sorted(self.v_walls)],
            "current": self.current,
            "turn_count": self.turn_count,
            "pass_count": self.pass_count,
            "winner": self.winner(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        """Reconstruct GameState from dictionary."""
        config = GameConfig(
            board_size=d.get("board_size", 9),
            num_players=d.get("num_players", len(d["pawns"])),
            walls_per_player=d.get("walls_per_player"),
            max_turns=d.get("max_turns"),
        )
        pawns = tuple((int(p[0]), int(p[1])) for p in d["pawns"])
        walls_left = tuple(int(w) for w in d["walls_left"])
        h_walls = frozenset((int(w[0]), int(w[1])) for w in d["h_walls"])
        v_walls = frozenset((int(w[0]), int(w[1])) for w in d["v_walls"])
        current = int(d["current"])
        turn_count = int(d.get("turn_count", 0))
        pass_count = int(d.get("pass_count", 0))

        return cls(
            config=config,
            pawns=pawns,
            walls_left=walls_left,
            h_walls=h_walls,
            v_walls=v_walls,
            current=current,
            turn_count=turn_count,
            pass_count=pass_count,
        )

    def render(self) -> str:
        """ASCII board representation."""
        from .render import render_board
        return render_board(self)
