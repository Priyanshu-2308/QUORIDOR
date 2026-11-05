# Quoridor AI

A Python implementation of the board game Quoridor (9x9 board, two players, 10 walls each) with several AI opponents (random, greedy, alpha-beta search and Monte Carlo tree search), a tournament runner for comparing them, and a web UI built with plain ES modules and Three.js. The core game logic uses only the Python standard library.

## Setup

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running tests

```
python -m pytest -q
```

## File layout

```
QUORIDOR/
  README.md                       Shubham creates; Priyanshu finalises
  requirements.txt  .gitignore    Shubham
  quoridor/
    __init__.py  constants.py  types.py  state.py        Shubham
    pathfinding.py  rules.py                              Rajnish
    eval.py  moves.py  runner.py                          Siddhesh
    agents/__init__.py  random_agent.py  greedy_agent.py  Siddhesh
    agents/base.py                                        Shubham
    agents/alphabeta_agent.py  agents/mcts_agent.py       Shivam
    tournament.py                                         Priyanshu
  server/app.py                                           Priyanshu
  web/                                                    Priyanshu
  tests/test_state.py                                     Shubham
  tests/test_pathfinding.py  tests/test_rules.py          Rajnish
  tests/test_eval_moves.py  tests/test_agents_basic.py  tests/test_runner.py    Siddhesh
  tests/test_alphabeta.py  tests/test_mcts.py             Shivam
  tests/test_server.py                                    Priyanshu
  results/  docs/REPORT.md                                Priyanshu
```

## Running the web UI

## Running tournaments

## Results
