"""BFS path utilities for dynamic Quoridor."""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from .constants import DIRECTIONS, goal_cells, goal_reached
from .types import Cell

if TYPE_CHECKING:
    from .state import GameState


def shortest_path(state: GameState, player: int) -> list[Cell] | None:
    """Shortest path from player's pawn to their goal side ignoring pawns.

    Returns:
        List of cells including current position and goal landing cell,
        or [start] if already on goal side, or None if unreachable.
    """
    bs = state.config.board_size
    start = state.pawn(player)
    if goal_reached(player, start, bs):
        return [start]

    total_cells = bs * bs
    visited = bytearray(total_cells)
    start_idx = start[0] * bs + start[1]
    visited[start_idx] = 1
    parent = [None] * total_cells
    queue = deque([start])

    while queue:
        curr = queue.popleft()
        r, c = curr
        curr_idx = r * bs + c

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < bs and 0 <= nc < bs:
                nxt_idx = nr * bs + nc
                if not visited[nxt_idx]:
                    nxt = (nr, nc)
                    if not state.is_blocked(curr, nxt):
                        visited[nxt_idx] = 1
                        parent[nxt_idx] = curr_idx

                        if goal_reached(player, nxt, bs):
                            path = [nxt]
                            step = nxt_idx
                            while step != start_idx:
                                p = parent[step]
                                assert p is not None
                                path.append((p // bs, p % bs))
                                step = p
                            path.reverse()
                            return path

                        queue.append(nxt)

    return None


def shortest_path_length(state: GameState, player: int) -> int | None:
    """Number of steps to goal side; 0 if on goal side; None if unreachable."""
    bs = state.config.board_size
    start = state.pawn(player)
    if goal_reached(player, start, bs):
        return 0

    total_cells = bs * bs
    visited = bytearray(total_cells)
    start_idx = start[0] * bs + start[1]
    visited[start_idx] = 1
    queue = deque([(start_idx, 0)])

    while queue:
        curr_idx, d = queue.popleft()
        r = curr_idx // bs
        c = curr_idx % bs
        nd = d + 1

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < bs and 0 <= nc < bs:
                nxt_idx = nr * bs + nc
                if not visited[nxt_idx]:
                    if not state.is_blocked((r, c), (nr, nc)):
                        if goal_reached(player, (nr, nc), bs):
                            return nd
                        visited[nxt_idx] = 1
                        queue.append((nxt_idx, nd))

    return None


def has_path(state: GameState, player: int) -> bool:
    """True if player has an unblocked path to their target goal side."""
    bs = state.config.board_size
    start = state.pawn(player)
    if goal_reached(player, start, bs):
        return True

    total_cells = bs * bs
    visited = bytearray(total_cells)
    start_idx = start[0] * bs + start[1]
    visited[start_idx] = 1
    queue = deque([start_idx])

    while queue:
        curr_idx = queue.popleft()
        r = curr_idx // bs
        c = curr_idx % bs
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < bs and 0 <= nc < bs:
                nxt_idx = nr * bs + nc
                if not visited[nxt_idx]:
                    if not state.is_blocked((r, c), (nr, nc)):
                        if goal_reached(player, (nr, nc), bs):
                            return True
                        visited[nxt_idx] = 1
                        queue.append(nxt_idx)

    return False


def multi_source_distances(state: GameState, player: int) -> list[int | None]:
    """Single multi-source BFS backwards from the goal side.

    Returns:
        List of length N * N where index r * N + c holds the shortest distance
        from cell (r, c) to player's goal side, or None if unreachable.
    """
    bs = state.config.board_size
    total_cells = bs * bs
    dist: list[int | None] = [None] * total_cells
    queue: deque[tuple[int, int]] = deque()

    for gr, gc in goal_cells(player, bs):
        dist[gr * bs + gc] = 0
        queue.append((gr, gc))

    while queue:
        r, c = queue.popleft()
        d = dist[r * bs + c]
        assert d is not None

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < bs and 0 <= nc < bs:
                nxt_idx = nr * bs + nc
                if dist[nxt_idx] is None:
                    if not state.is_blocked((r, c), (nr, nc)):
                        dist[nxt_idx] = d + 1
                        queue.append((nr, nc))

    return dist


def distances(state: GameState) -> dict[int, int | None]:
    """Return dictionary mapping active player IDs to their shortest path length."""
    return {p: shortest_path_length(state, p) for p in state.config.players}
