"""Game configuration for dynamic-board Quoridor."""
from __future__ import annotations

from dataclasses import dataclass

from .constants import default_walls_per_player


@dataclass(frozen=True)
class GameConfig:
    """Configuration for an N x N Quoridor game with 2 or 4 players."""
    board_size: int = 9
    num_players: int = 4
    walls_per_player: int | None = None
    max_turns: int | None = None

    def __post_init__(self) -> None:
        if not (7 <= self.board_size <= 12):
            raise ValueError(f"board_size must be between 7 and 12, got {self.board_size}")
        if self.num_players not in (2, 4):
            raise ValueError(f"num_players must be 2 or 4, got {self.num_players}")
        if self.walls_per_player is None:
            object.__setattr__(
                self,
                "walls_per_player",
                default_walls_per_player(self.board_size, self.num_players),
            )
        elif self.walls_per_player < 0:
            raise ValueError(f"walls_per_player must be non-negative, got {self.walls_per_player}")

        if self.max_turns is None:
            object.__setattr__(self, "max_turns", 40 * self.board_size)
        elif self.max_turns <= 0:
            raise ValueError(f"max_turns must be positive, got {self.max_turns}")

    @property
    def players(self) -> tuple[int, ...]:
        """Active player IDs: (0, 1, 2, 3) for 4 players; (0, 2) for 2 players."""
        return (0, 1, 2, 3) if self.num_players == 4 else (0, 2)
