"""Agent registry and factory."""
from __future__ import annotations

import ast

from .base import Agent
from .greedy_agent import GreedyAgent
from .random_agent import RandomAgent

AGENT_NAMES = ("random", "greedy", "alphabeta", "mcts")


def make_agent(spec: str) -> Agent:
    """Create an agent from a spec string.

    Format: ``"name"`` or ``"name:key=value,key=value,..."``.
    Values are parsed with ``ast.literal_eval``, falling back to the raw string.
    Raises ``ValueError`` for unknown names or unknown keyword arguments.
    """
    if ":" in spec:
        name, rest = spec.split(":", 1)
        kwargs: dict[str, object] = {}
        for pair in rest.split(","):
            pair = pair.strip()
            if not pair:
                continue
            if "=" not in pair:
                raise ValueError(f"expected key=value, got {pair!r}")
            k, v_raw = pair.split("=", 1)
            k = k.strip()
            v_raw = v_raw.strip()
            try:
                kwargs[k] = ast.literal_eval(v_raw)
            except (ValueError, SyntaxError):
                kwargs[k] = v_raw
    else:
        name = spec
        kwargs = {}

    name = name.strip()

    if name == "random":
        try:
            return RandomAgent(**kwargs)  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError(f"bad kwargs for 'random': {exc}") from exc

    if name == "greedy":
        try:
            return GreedyAgent(**kwargs)  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError(f"bad kwargs for 'greedy': {exc}") from exc

    if name == "alphabeta":
        from .alphabeta_agent import AlphaBetaAgent  # lazy import
        try:
            return AlphaBetaAgent(**kwargs)  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError(f"bad kwargs for 'alphabeta': {exc}") from exc

    if name == "mcts":
        from .mcts_agent import MCTSAgent  # lazy import
        try:
            return MCTSAgent(**kwargs)  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError(f"bad kwargs for 'mcts': {exc}") from exc

    raise ValueError(
        f"unknown agent {name!r}. Valid names: {', '.join(AGENT_NAMES)}"
    )