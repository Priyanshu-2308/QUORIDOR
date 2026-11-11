# Quoridor AI (V2)

A Python implementation of the board game Quoridor ($9 \times 9$ board, two players, 10 walls each) featuring four AI search strategies (Random, Greedy, Alpha-Beta Minimax, and Monte Carlo Tree Search), an automated tournament and ablation runner, and the V2 "Quiet Bastion" web interface with real-time corridor path analysis, interactive wall placement, and AI telemetry. The core game logic uses only the Python standard library with an immutable state architecture.

---

## Live Demo

- Live deployment: [quoridor-ai.onrender.com](https://quoridor-ai.onrender.com) (or local container at `http://localhost:7860`)

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running Tests

Run the test suite with pytest:

```bash
python -m pytest -q
```

All 103 unit and regression tests across state representations, game rules, pathfinding, evaluation heuristics, Alpha-Beta search, MCTS, server endpoints, and tournament multiprocessing pass.

---

## File Layout

```
QUORIDOR/
  README.md                       Project overview, setup, tournament guide
  requirements.txt  .gitignore    Development dependencies
  requirements-deploy.txt         Production dependencies (FastAPI, Uvicorn)
  Dockerfile  render.yaml         Container build and deployment configuration
  quoridor/
    __init__.py  constants.py  types.py  state.py        Core rules and state
    pathfinding.py  rules.py                              Pathfinding and moves
    eval.py  moves.py  runner.py                          Evaluation and runner
    agents/__init__.py  random_agent.py  greedy_agent.py  Baselines
    agents/base.py                                        Agent base class
    agents/alphabeta_agent.py  agents/mcts_agent.py       Search agents
    tournament.py                                         Tournament CLI
  server/app.py                                           FastAPI backend
  web/                                                    Three.js web UI
  tests/                                                  Unit and regression tests
  results/                                                Tournament logs and CSVs
  docs/REPORT.md                                          Empirical evaluation report
```

---

## Running the Web UI (V2)

Start the backend server with Uvicorn:

```bash
uvicorn server.app:app --port 8000
```

Open `http://localhost:8000` in your browser to access the V2 "Quiet Bastion" interface:
- **Title Screen (`#/title`):** Minimalist archival introduction, feature synopsis, and game start.
- **Setup Screen (`#/setup`):** Character persona cards with dedicated badges and complexity controls:
  - **Wobbles (`random`):** Casual baseline (*"Walks like it lost its keys"*).
  - **Dash (`greedy`):** Fast baseline with zero wall usage (*"Zero walls. All speed"*).
  - **Professor Prune (`alphabeta`):** Minimax with alpha-beta pruning, iterative deepening, transposition table, and killer heuristics (*"Thinks first. Snips bad ideas"*). Search depth options: Casual (Depth 1), Careful (Depth 2), Sharp (Depth 3), Ruthless (Depth 4).
  - **The Gambler (`mcts`):** Monte Carlo Tree Search with UCB1 exploration and rollout heuristics (*"Rolls a thousand dice. Hopes"*). Iteration count options: Casual (200), Careful (400), Sharp (600), Ruthless (1000).
  - **Side Selection:** Choose who moves first: **You (Cobalt `#2E4BDB`)** or **Opponent (Vermilion `#E5532D`)**.
- **Match Arena (`#/game`):**
  - High-precision $9 \times 9$ Quoridor matrix with algebraic coordinates (`a-i`, `1-9`) and goal row tinting.
  - Interactive pawn moves with legal dot indicator pips.
  - Interactive wall placement with live ghost wall preview, orientation tooltip, and illegal attempt detection.
  - Real-time SVG shortest-path trails (Cobalt for Player 0, Vermilion for Player 1).
  - Wall inventory tracking (10-pill counters for both players with remaining counts).
  - Real-time path distance metrics (`You: X steps · Opponent: Y steps`).
  - Search engine telemetry (`nodes`, `latency`, `eval`).
  - Scrollable move notation log formatted in standard algebraic notation.
  - One-click Undo (`U`), shortest path toggle (`P`), and new game reset (`Esc`).
- **Game Over Modal (`#/result`):** Post-match review card featuring match duration, plies count, walls placed, winner monogram, Rematch action, Review mode, and New Game.

### Keyboard Shortcuts
- `R`: Rotate candidate wall orientation (`H` $\leftrightarrow$ `V`) or trigger rematch.
- `P`: Toggle shortest-path trails.
- `U`: Undo human move and subsequent AI reply.
- `Esc`: Return to setup screen or main menu.

---

## Running Tournaments & Experiments

The tournament CLI supports single matchups, the evaluation suite, ablation studies, and chart rendering.

### 1. Single Matchup
```bash
python -m quoridor.tournament --a "alphabeta:depth=3" --b "mcts:iterations=800" --games 20 --workers 4 --out results/custom_match.json
```

### 2. Tournament Suite
Runs the 7-matchup matrix (20 games each with alternating seats) and writes `results/summary.csv` and `results/win_rates.png`:
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

Summary of results from the 20-game alternating-seat evaluation suite (`results/summary.csv`):

| Matchup (Agent A vs Agent B) | Games | Wins A | Wins B | Draws | Win Rate A | Mean Plies | Nodes/Move A | Latency A | Nodes/Move B | Latency B |
|---|---|---|---|---|---|---|---|---|---|---|
| **Greedy vs Random** | 20 | 20 | 0 | 0 | **100.0%** | 15.2 | 3.8 | 0.8 ms | 32.6 | 11.2 ms |
| **AlphaBeta(d=2) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 19.1 | 36.2 | 140.5 ms | 3.6 | 0.9 ms |
| **AlphaBeta(d=3) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 26.6 | 247.7 | 467.1 ms | 3.3 | 1.0 ms |
| **MCTS(500) vs Greedy** | 20 | 18 | 2 | 0 | **90.0%** | 38.2 | 486.3 | 2,037.6 ms | 3.3 | 1.0 ms |
| **MCTS(1000) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 31.7 | 976.3 | 3,735.0 ms | 3.4 | 1.2 ms |
| **AlphaBeta(d=3) vs MCTS(1000)** | 20 | 12 | 8 | 0 | **60.0%** | 66.8 | 179.3 | 617.0 ms | 956.7 | 4,746.7 ms |
| **AlphaBeta(d=2) vs AlphaBeta(d=3)** | 20 | 6 | 14 | 0 | **30.0%** | 62.0 | 35.1 | 185.6 ms | 189.8 | 726.3 ms |

See `docs/REPORT.md` for in-depth algorithmic analyses, confidence intervals, ablation breakdowns, and architectural details.

---

## Deploying

The application can be deployed with Docker on any container hosting platform (Render, Hugging Face Spaces, Fly.io, Railway).

### Deploying to Render
1. Create a new Web Service on [Render](https://render.com).
2. Connect this repository (`https://github.com/Priyanshu-2308/QUORIDOR`).
3. Select "Docker" as the runtime. Render automatically detects `Dockerfile` and `render.yaml`.
4. Choose the Free plan and click "Create Web Service".

### Deploying to Hugging Face Spaces
1. Create a new Space on [Hugging Face](https://huggingface.co/spaces).
2. Select "Docker" as the Space SDK.
3. Push this repository to the Space remote. The Dockerfile exposes port 7860, which Hugging Face routes automatically.

### Running with Docker Locally
```bash
docker build -t quoridor .
docker run -p 7860:7860 quoridor
```
Open `http://localhost:7860` in your browser.

> Note: Use exactly one worker process (`--workers 1`) because game sessions live in memory. To protect public instances, opponent parameters are capped: Alpha-Beta depth is limited to 1-4, MCTS iterations are limited to 50-1000, and idle sessions are evicted automatically.
