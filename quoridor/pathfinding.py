"""BFS path utilities over cells; walls only, the other pawn is ignored."""
from __future__ import annotations

from collections import deque
from .constants import BOARD_SIZE, DIRECTIONS, GOAL_ROW
from .state import GameState
from .types import Cell


def shortest_path(state: GameState, player: int) -> list[Cell] | None:
    """Shortest path incl. start and goal cell; [pawn] if already on goal row; None if unreachable."""
    start = state.pawns[player]
    goal_row = GOAL_ROW[player]
    
    if start[0] == goal_row:
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
                        if nr == goal_row:
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
    """Number of steps; 0 if on goal row; None if unreachable."""
    start = state.pawns[player]
    goal_row = GOAL_ROW[player]
    if start[0] == goal_row:
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
                        if nr == goal_row:
                            return nd
                        visited[nxt_idx] = 1
                        queue.append((nr, nc, nd))
    return None


def has_path(state: GameState, player: int) -> bool:
    """True if ``player`` can reach its goal row."""
    start = state.pawns[player]
    goal_row = GOAL_ROW[player]
    if start[0] == goal_row:
        return True
    visited = bytearray(81)
    visited[start[0] * 9 + start[1]] = 1
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                nxt_idx = nr * 9 + nc
                if not visited[nxt_idx]:
                    if not state.is_blocked((r, c), (nr, nc)):
                        if nr == goal_row:
                            return True
                        visited[nxt_idx] = 1
                        queue.append((nr, nc))
    return False


def distances(state: GameState) -> tuple[int | None, int | None]:
    """(path length for player 0, path length for player 1)."""
    return (shortest_path_length(state, 0), shortest_path_length(state, 1))
