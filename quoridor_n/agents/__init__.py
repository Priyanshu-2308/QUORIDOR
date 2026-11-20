"""Agent factory and registry for dynamic Quoridor."""
from __future__ import annotations

import ast
from typing import Any

from .base import Agent
from .greedy_agent import GreedyAgent
from .maxn_agent import MaxnAgent
from .mcts_agent import MCTSAgent
from .paranoid_agent import ParanoidAgent
from .random_agent import RandomAgent

AGENT_CLASSES: dict[str, type[Agent]] = {
    "random": RandomAgent,
    "greedy": GreedyAgent,
    "paranoid": ParanoidAgent,
    "alphabeta": ParanoidAgent,
    "maxn": MaxnAgent,
    "mcts": MCTSAgent,
}


def make_agent(spec: str) -> Agent:
    """Construct an Agent from a specification string.

    Format: "name" or "name:key=value,key2=value2"
    Examples:
        "random"
        "greedy"
        "paranoid:depth=3,eval_mode='mean'"
        "mcts:iterations=500,rollout_policy='path_biased'"
    """
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError(f"spec must be a non-empty string, got {spec!r}")

    parts = spec.strip().split(":", 1)
    name = parts[0].strip().lower()

    if name not in AGENT_CLASSES:
        raise ValueError(f"unknown agent name: {name!r}; valid choices: {sorted(AGENT_CLASSES.keys())}")

    agent_cls = AGENT_CLASSES[name]
    kwargs: dict[str, Any] = {}

    if len(parts) == 2 and parts[1].strip():
        param_str = parts[1].strip()
        for item in param_str.split(","):
            if not item.strip():
                continue
            if "=" not in item:
                raise ValueError(f"invalid parameter format: {item!r}; expected key=value")
            k, v = item.split("=", 1)
            k = k.strip()
            v = v.strip()
            try:
                parsed_val = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                # Fallback to string if not literal
                parsed_val = v
            kwargs[k] = parsed_val

    try:
        return agent_cls(**kwargs)
    except TypeError as exc:
        raise ValueError(f"invalid arguments for agent {name!r}: {exc}") from exc


__all__ = [
    "Agent",
    "RandomAgent",
    "GreedyAgent",
    "ParanoidAgent",
    "MaxnAgent",
    "MCTSAgent",
    "make_agent",
]
