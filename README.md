# Quoridor AI

A high-performance Python implementation of the board game Quoridor ($9 \times 9$ board, two players, 10 walls each) featuring multiple AI search strategies (Random, Greedy, Alpha-Beta Minimax, and Monte Carlo Tree Search), an automated tournament and ablation runner, and a modern reactive 3D web UI built with Three.js. The core game logic uses only the Python standard library with an immutable state architecture.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running Tests

Run the full pytest suite:

```bash
python -m pytest -q
```

All unit and regression tests across state representations, game rules, pathfinding, evaluation heuristics, Alpha-Beta search, MCTS, server endpoints, and tournament multiprocessing execute and pass cleanly.

---

## File Layout and Module Ownership

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
  tests/test_server.py  tests/test_tournament.py          Priyanshu
  results/  docs/REPORT.md                                Priyanshu
```

---

## Running the Web UI

Start the backend server with Uvicorn:

```bash
uvicorn server.app:app --port 8000
```

Open your browser to `http://localhost:8000` to access the full-bleed **Monolith** 3D interface:
- **Title Screen (`#/title`):** Rotating pawn monolith, single-click start.
- **Setup Screen (`#/setup`):** Select opponent (`RANDOM`, `GREEDY`, `ALPHA-BETA`, `MCTS`), adjust strength level (depth 2/3/4 or iterations 200/500/1000/2000), and choose who moves first (`YOU START` or `AI STARTS`).
- **Game Screen (`#/game`):** Interactive $9 \times 9$ board with legal pawn move markers, groove raycasting with ghost wall preview, wall orientation rotation (`R`), and live HUD.
- **Stats Screen (`#/stats`):** 3D telemetry visualization displaying nodes visited, execution latency, and position evaluation.
- **Result Screen (`#/result`):** Immediate rematch option or return to main menu.

### Keyboard Shortcuts
- `P`: Toggle shortest-path trails on the board.
- `R`: Rotate candidate wall orientation (`H` $\leftrightarrow$ `V`) or trigger rematch.
- `U`: Undo human move and subsequent AI reply.
- `S`: View AI telemetry and stats.
- `Esc`: Return to menu or back to game.

---

## Running Tournaments & Experiments

The tournament CLI supports single matchups, the standard evaluation suite, ablation studies, and matplotlib chart rendering.

### 1. Single Matchup
```bash
python -m quoridor.tournament --a "alphabeta:depth=3" --b "mcts:iterations=800" --games 20 --workers 4 --out results/custom_match.json
```

### 2. Standard Tournament Suite
Runs the full 7-matchup matrix (20 games each with alternating seats) and writes `results/summary.csv` and `results/win_rates.png`:
```bash
python -m quoridor.tournament --suite --workers 6
```

### 3. Search Ablation Study
Evaluates 9 configurations across 15 fixed middle-game positions and writes `results/ablation.csv`, `results/ablation_nodes.png`, and `results/ablation_ms.png`:
```bash
python -m quoridor.tournament --ablation
```

### 4. Regenerate Charts
```bash
python -m quoridor.tournament --charts
```

---

## Empirical Tournament Results

Below is the summary of results from the 20-game alternating-seat evaluation suite (`results/summary.csv`):

| Matchup (Agent A vs Agent B) | Games | Wins A | Wins B | Draws | Win Rate A | Mean Plies | Nodes/Move A | Latency A | Nodes/Move B | Latency B |
|---|---|---|---|---|---|---|---|---|---|---|
| **Greedy vs Random** | 20 | 20 | 0 | 0 | **100.0%** | 15.2 | 3.8 | 0.8 ms | 32.6 | 11.2 ms |
| **AlphaBeta(d=2) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 19.1 | 36.2 | 140.5 ms | 3.6 | 0.9 ms |
| **AlphaBeta(d=3) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 26.6 | 247.7 | 467.1 ms | 3.3 | 1.0 ms |
| **MCTS(500) vs Greedy** | 20 | 18 | 2 | 0 | **90.0%** | 38.2 | 486.3 | 2,037.6 ms | 3.3 | 1.0 ms |
| **MCTS(1000) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 31.7 | 976.3 | 3,735.0 ms | 3.4 | 1.2 ms |
| **AlphaBeta(d=3) vs MCTS(1000)** | 20 | 12 | 8 | 0 | **60.0%** | 66.8 | 179.3 | 617.0 ms | 956.7 | 4,746.7 ms |
| **AlphaBeta(d=2) vs AlphaBeta(d=3)** | 20 | 6 | 14 | 0 | **30.0%** | 62.0 | 35.1 | 185.6 ms | 189.8 | 726.3 ms |

*See `docs/REPORT.md` for in-depth algorithmic analyses, search ablation breakdowns, and architectural details.*
