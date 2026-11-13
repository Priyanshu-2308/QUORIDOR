# Quoridor AI

A two-player Quoridor game with a web interface and four computer opponents (random, greedy, alpha-beta search, Monte Carlo tree search), plus the tools we used to compare them. The game engine uses an immutable state representation with pathfinding and move pruning.

Live demo: https://quoridor-rqj3.onrender.com
(free hosting: the first load after a quiet period can take about a minute)

## Setup

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate       # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the game

Start the local server with:

```bash
uvicorn server.app:app --port 8000
```

Open `http://localhost:8000` in your browser.

| Action | Control |
|---|---|
| Move | Click a dot, or use the arrow keys |
| Place a wall | Hover a gap between cells and click |
| Rotate the wall | R or right-click |
| Shortcuts | U undo, P show shortest paths, Esc back to setup |

## Tests

```bash
python -m pytest -q
node --test tests/web
```

## Experiments

Run a custom head-to-head match:
```bash
python -m quoridor.tournament --a "alphabeta:depth=3" --b "mcts:iterations=800" --games 20 --workers 4
```

Run the full tournament suite across all agent pairings:
```bash
python -m quoridor.tournament --suite --workers 6
```

Run the search ablation benchmark:
```bash
python -m quoridor.tournament --ablation
```

See `docs/REPORT.md` for the experimental setup, win rates, and ablation results.

## Layout

- `quoridor/`: engine and agents
- `server/`: API and game session store
- `web/`: interface and controls
- `tests/`: unit and regression tests
- `results/`: match logs, summaries, and plots
- `docs/`: experiment report
