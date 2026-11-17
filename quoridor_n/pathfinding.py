"""BFS path utilities for four-player and two-player Quoridor."""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from .constants import (
    BOARD_SIZE,
    DIRECTIONS,
    UNREACHABLE_DIST,
    goal_cells,
    goal_reached,
)
from .types import Cell

if TYPE_CHECKING:
    from .state import GameState


def shortest_path(state: GameState, player: int) -> list[Cell] | None:
    """Shortest path from player's pawn to their goal side.
    
    Returns:
        List of cells including current position and landing goal cell,
        or [start] if already on goal side, or None if unreachable.
    """
    start = state.pawn(player)
    if goal_reached(player, start):
        return [start]

    visited = bytearray(81)
    visited[start[0] * 9 + start[1]] = 1
    parent = [None] * 81
    queue = deque([start])

    while queue:
        curr = queue.popleft()
        r, c = curr
        curr_idx = r * 9 + c

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nxt_idx = nr * 9 + nc
                if not visited[nxt_idx]:
                    nxt = (nr, nc)
                    if not state.is_blocked(curr, nxt):
                        visited[nxt_idx] = 1
                        parent[nxt_idx] = curr_idx

                        if goal_reached(player, nxt):
                            path = [nxt]
                            step = nxt_idx
                            start_idx = start[0] * 9 + start[1]
                            while step != start_idx:
                                p = parent[step]
                                path.append((p // 9, p % 9))
                                step = p
                            path.reverse()
                            return path

                        queue.append(nxt)

    return None


def shortest_path_length(state: GameState, player: int) -> int | None:
    """Number of steps to goal side; 0 if already on goal side; None if unreachable."""
    start = state.pawn(player)
    if goal_reached(player, start):
        return 0

    visited = bytearray(81)
    visited[start[0] * 9 + start[1]] = 1
    queue = deque([(start[0], start[1], 0)])

    while queue:
        r, c, d = queue.popleft()
        nd = d + 1

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nxt_idx = nr * 9 + nc
                if not visited[nxt_idx]:
                    if not state.is_blocked((r, c), (nr, nc)):
                        if goal_reached(player, (nr, nc)):
                            return nd
                        visited[nxt_idx] = 1
                        queue.append((nr, nc, nd))

    return None


def has_path(state: GameState, player: int) -> bool:
    """True if player has an unblocked path to their target goal side."""
    start = state.pawn(player)
    if goal_reached(player, start):
        return True

    visited = bytearray(81)
    visited[start[0] * 9 + start[1]] = 1
    queue = deque([start])

    while queue:
        curr = queue.popleft()
        for dr, dc in DIRECTIONS:
            nr, nc = curr[0] + dr, curr[1] + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nxt_idx = nr * 9 + nc
                if not visited[nxt_idx]:
                    if not state.is_blocked(curr, (nr, nc)):
                        if goal_reached(player, (nr, nc)):
                            return True
                        visited[nxt_idx] = 1
                        queue.append((nr, nc))

    return False


def multi_source_distances(state: GameState, player: int) -> list[int | None]:
    """Single multi-source BFS backwards from the goal side.
    
    Returns:
        A list of length 81 where index r * 9 + c holds the shortest distance
        from cell (r, c) to player's goal side, or None if unreachable.
    """
    dist: list[int | None] = [None] * 81
    queue: deque[tuple[int, int]] = deque()

    for gr, gc in goal_cells(player):
        dist[gr * 9 + gc] = 0
        queue.append((gr, gc))

    while queue:
        r, c = queue.popleft()
        d = dist[r * 9 + c]
        assert d is not None

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nxt_idx = nr * 9 + nc
                if dist[nxt_idx] is None:
                    if not state.is_blocked((r, c), (nr, nc)):
                        dist[nxt_idx] = d + 1
                        queue.append((nr, nc))

    return dist


def distances(state: GameState) -> tuple[int | None, ...]:
    """Shortest-path distance for each active player in state.players."""
    return tuple(shortest_path_length(state, p) for p in state.players)
