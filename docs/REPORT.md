# Quoridor AI: Engine, Search Agents and a Small Comparison

CS AI course project. Team: Shubham, Rajnish, Siddhesh, Shivam, Priyanshu.

## 1. Summary

We built a Quoridor engine in Python and four computer players: random, greedy, alpha-beta search, and Monte Carlo tree search (MCTS). We then ran a small tournament between them and a benchmark of the alpha-beta speed-ups. A web interface sits on top so the agents can be played against.

What we can say from the data:

- Alpha-beta (depth 2 or 3) and MCTS (500 or 1000 simulations) beat the greedy baseline in 18 to 20 of 20 games each. The greedy agent in these runs never places walls (see 6.2), so this is a weak baseline.
- Alpha-beta depth 3 won 12 of 20 against MCTS with 1000 simulations. That is **not** a significant difference (p = 0.50). We cannot say which agent is stronger.
- Alpha-beta depth 3 won 14 of 20 against depth 2 (p = 0.12). Suggestive, not conclusive.
- Pruning the wall candidates is what makes multi-ply search affordable. With only wall pruning switched off, the search visits about 40 times more nodes at depth 3 (561 to 22,336) and takes about 56 times longer.
- Move ordering reduces nodes (by 38% at depth 3, 44% at depth 4) but did not reduce time in our runs. The transposition table helped only at depth 4 (about 7% fewer nodes, about 18% less time).

What we did not do: there is no learning or training anywhere in the project. All weights are set by hand. We did not compare against outside engines or human players, and 20 games per matchup is a small sample.

## 2. Game rules as implemented

- Board: 9 x 9 cells, `(row, col)`, row 0 at the top. Each player has 10 walls.
- Player 0 starts at (8, 4) and must reach row 0. Player 1 starts at (0, 4) and must reach row 8. Player 0 moves first.
- A turn is either a pawn move or a wall placement.
- Pawn moves: one step up, down, left or right if no wall or board edge blocks it. If the opponent is in the adjacent cell, the pawn jumps straight over if the cell behind the opponent is open. If that is blocked, it moves diagonally to a free cell beside the opponent.
- A wall covers two cell edges, horizontal (`H`) or vertical (`V`). It cannot overlap or cross another wall, and it cannot be placed if either player would be left with no path to the goal row.
- At the start there are 131 legal moves: 3 pawn moves and 128 walls (`quoridor/rules.py`). This is why plain search is expensive.

## 3. Code layout

```
quoridor/
  constants.py      board size, start cells, goal rows, directions
  types.py          PawnMove, WallMove, dict conversion
  state.py          immutable GameState (frozen dataclass)
  pathfinding.py    BFS shortest path / length / reachability
  rules.py          legal pawn moves, wall legality, legal moves
  eval.py           position evaluation used by alpha-beta
  moves.py          candidate (pruned) wall and move generation
  runner.py         play_game
  tournament.py     matches, suite, ablation, charts
  agents/           base, random, greedy, alphabeta, mcts, make_agent
server/app.py       FastAPI API
web/                browser interface (plain JavaScript modules)
tests/              pytest suite, plus tests/web (node)
results/            match logs, summary.csv, ablation.csv, stats.txt, plots
```

The engine and agents use only the Python standard library. The server needs FastAPI, and the tournament charts need matplotlib.

## 4. State and rules engine

### 4.1 State

`GameState` is a frozen dataclass: `pawns`, `walls_left`, `h_walls`, `v_walls` (frozensets), `current`, `turn_count`. `state.apply(move)` returns a new state and does no legality check. Immutability means search code never has to undo a move and states can be shared across worker processes. `state.key()` returns a hashable tuple used by the transposition table.

A wall is stored as `(r, c)` with `r, c` in 0..7 plus an orientation. An `H` wall at `(r, c)` blocks the steps between rows `r` and `r+1` in columns `c` and `c+1`. A `V` wall at `(r, c)` blocks the steps between columns `c` and `c+1` in rows `r` and `r+1`. `state.is_blocked(a, b)` implements this.

### 4.2 Pathfinding

`pathfinding.py` has three breadth-first searches that start from the pawn and stop when any goal-row cell is reached: `shortest_path` (returns the cells), `shortest_path_length`, and `has_path`. They ignore the other pawn. Walls are checked on the fly with `is_blocked`; there is no stored graph. We used BFS rather than A* because every step costs 1 on a 9 x 9 board, so BFS already gives the shortest path and the board is small.

### 4.3 Wall legality

`rules.is_wall_legal` first runs the cheap checks (game not over, walls left, in bounds, no overlap, no crossing). Only then does it apply the wall and run `has_path` for both players. That ordering avoids a BFS for walls that are already illegal.

## 5. Agents

### 5.1 Random and greedy (baselines)

- **Random**: with probability `wall_prob` (default 0.2) picks a random legal wall, otherwise a random legal pawn move.
- **Greedy**: picks the pawn move that leaves its own shortest path shortest. It can place walls only if `wall_prob > 0`. The default is 0.0, and the tournament runs use the default, so **greedy never places a wall in any of our matches**.

### 5.2 Candidate wall pruning (`moves.py`)

Instead of all 128 walls, `candidate_walls` takes the opponent's current shortest path and, for each step on it, tries the two walls that would block that step. It keeps those that are legal. The idea is that a wall off the opponent's path does not make them walk further right now.

At the opening this gives 16 candidate walls, so 19 candidate moves instead of 131.

What this can miss: walls that only matter after the path changes, walls that protect the agent's own route, and anything that is useful for reasons other than lengthening the opponent's current shortest path. We did not measure how often the best wall is missed. The ablation (section 7) only shows that pruning changes the chosen move in many positions; it does not say whether the pruned or unpruned choice is better.

### 5.3 Evaluation (`eval.py`)

For the player to move:

```
eval = 1.0 * (d_opp - d_me) + 0.25 * (walls_me - walls_opp)
```

`d_me` and `d_opp` are BFS shortest-path lengths (99 if no path). A win scores +10,000 and a loss -10,000. The opening position evaluates to 0. The weights 1.0 and 0.25 were set by hand. We did not tune them or test other values.

### 5.4 Alpha-beta (`alphabeta_agent.py`)

Fixed-depth negamax with alpha-beta cutoffs. At a terminal node the score is `WIN_SCORE - ply` (or the negative), so earlier wins score higher. At depth 0 it calls the evaluation above. Three switches, all on by default:

- **Wall pruning**: use `candidate_moves` instead of all legal moves.
- **Move ordering**: pawn moves sorted by the distance left after the move; walls sorted by (opponent distance minus own distance) after the wall, and **only the top 12 walls are kept**. So turning ordering off also changes which moves are searched, not only their order.
- **Transposition table**: a dict keyed by `state.key()` storing depth, value, a bound flag (exact, lower, upper) and the best move. It is cleared at the start of every `choose_move`.

At the root, all moves that tie for the best value are collected and one is picked with a seeded random choice. The root uses a window that tightens as moves are found, so a move reported as tied may in fact be slightly worse. We did not test whether this affects play.

Iterative deepening and a time limit exist in the code but are off by default and were not used in any experiment. Search depth is fixed (depth 2, 3, or 4 depending on the experiment).

### 5.5 MCTS (`mcts_agent.py`)

Standard UCT with exploration constant c = 1.4.

1. **Selection**: pick the child maximising `value/visits + c * sqrt(ln(parent visits) / visits)`.
2. **Expansion**: add one untried move from `candidate_moves`.
3. **Simulation** (up to 60 plies): with probability 0.95, the player to move steps along its shortest path (or the best-distance pawn step); with probability 0.05 it plays a random candidate move.
4. **Result**: a finished game scores 1 for a root-player win and 0 for a loss. If the 60 plies run out, the score is `0.5 + 0.5 * tanh((d_opp - d_me) / 4)`, viewed from the root player.
5. **Backpropagation**, then the final move is the **most-visited** root child. If a root child is an immediate win, that move is played.

The rollout parameters (0.95, 60, the divisor 4) were set by hand. The path-biased rollout is a design choice; we did not run a comparison against plain random rollouts, so we make no claim about how much it helps.

## 6. Tournament

### 6.1 Setup

`python -m quoridor.tournament --suite --workers N` plays 20 games per pairing. Game `i` uses seed `base_seed + i` for both agents. Seats alternate: Agent A plays Player 0 in even games and Player 1 in odd games, so each agent plays 10 games on each side. Games are capped at 200 plies (no game hit the cap; there were 0 draws). Games run in parallel processes and each pairing is saved as a JSON file in `results/`. `results/stats.py` computes a 95% Wilson interval and an exact two-sided binomial p-value against 50%.

Agent settings: `alphabeta:depth=2` or `depth=3` with all switches on; `mcts:iterations=500` or `1000` with c = 1.4, rollout depth 60.

### 6.2 Results (`results/summary.csv`, `results/stats.txt`)

| Matchup (A vs B) | A wins | Win % | 95% CI | p vs 50% | Mean plies | ms/move A | ms/move B |
|---|---|---|---|---|---|---|---|
| Greedy vs Random | 20/20 | 100% | 83.9 to 100 | <0.0001 | 15.2 | 0.8 | 11.2 |
| AlphaBeta d=2 vs Greedy | 20/20 | 100% | 83.9 to 100 | <0.0001 | 19.1 | 140.5 | 0.9 |
| AlphaBeta d=3 vs Greedy | 20/20 | 100% | 83.9 to 100 | <0.0001 | 26.6 | 467.1 | 1.0 |
| MCTS 500 vs Greedy | 18/20 | 90% | 69.9 to 97.2 | 0.0004 | 38.2 | 2037.6 | 1.0 |
| MCTS 1000 vs Greedy | 20/20 | 100% | 83.9 to 100 | <0.0001 | 31.7 | 3735.0 | 1.2 |
| AlphaBeta d=3 vs MCTS 1000 | 12/20 | 60% | 38.7 to 78.1 | 0.50 | 66.8 | 617.0 | 4746.7 |
| AlphaBeta d=2 vs AlphaBeta d=3 | 6/20 | 30% | 14.5 to 51.9 | 0.12 | 62.0 | 185.6 | 726.3 |

(In the last row depth 3 is Agent B and won 14 of 20.)

### 6.3 What the results show

- **Against greedy**: every search agent wins almost every game. Keep in mind the greedy opponent only walks its shortest path and never places a wall, so this shows the search agents can beat a pure runner, not that they play well.
- **Alpha-beta vs MCTS**: 12 to 8 is within chance. The 95% interval (38.7% to 78.1%) includes 50%. To separate two agents whose true win rate is 60% from 50% we would need roughly 100 to 200 games.
- **Time**: MCTS used about 4.7 s per move against about 0.6 s for alpha-beta, roughly 8 times more. This is measured wall-clock in Python while several games ran in parallel, so the absolute numbers depend on the machine and are only comparable within this run.
- **Depth 2 vs depth 3**: depth 3 won 14 of 20. With p = 0.12 we cannot rule out chance.
- **Seats**: in the matches the first mover won 8 to 12 of 20 depending on the pairing (10 of 20 in most). With seat alternation, any first-move advantage cancels between the two agents; we did not measure the advantage itself.

## 7. Alpha-beta ablation

`python -m quoridor.tournament --ablation` takes 15 positions and runs 9 configurations. The positions come from seeded games of greedy vs random (both with wall probability 0.3), taking the positions after plies 4, 8, 12 and 16 until 15 are collected. That means they come from only four games (seeds 0 to 3), they are early-game positions, and positions from the same game are not independent. For each configuration the table gives mean nodes, mean time per move, transposition-table hits, cutoffs, and how often the chosen move equals the chosen move of the full configuration at the same depth.

| Config | Depth | Nodes | ms | TT hits | Cutoffs | Same move as all_on |
|---|---|---|---|---|---|---|
| all_on | 3 | 346.1 | 316.5 | 0.0 | 28.1 | 100% |
| no_tt | 3 | 346.1 | 319.1 | 0.0 | 28.1 | 100% |
| no_ordering | 3 | 561.4 | 280.4 | 0.0 | 30.8 | 80% |
| no_ordering_no_tt | 3 | 561.4 | 262.6 | 0.0 | 30.8 | 80% |
| no_pruning (also no ordering, no TT) | 3 | 22,335.7 | 14,604.4 | 0.0 | 309.7 | 53.3% |
| all_on | 4 | 861.5 | 1496.2 | 52.9 | 316.1 | 100% |
| no_tt | 4 | 923.2 | 1833.7 | 0.0 | 316.4 | 100% |
| no_ordering | 4 | 1548.5 | 1282.9 | 98.7 | 519.7 | 33.3% |
| no_ordering_no_tt | 4 | 1700.6 | 1503.7 | 0.0 | 520.1 | 33.3% |

How to read it:

- **Wall pruning.** The `no_pruning` row also has move ordering and the transposition table off, so the fair comparison is against `no_ordering_no_tt`: 561.4 to 22,335.7 nodes (about 40 times) and 262.6 to 14,604.4 ms (about 56 times). Comparing against `all_on` (64.5 times in nodes) mixes in the other two switches. The unpruned search picked a different move in 47% of positions. The table does not tell us which move was better.
- **Move ordering.** Fewer nodes (561 to 346 at depth 3, 1548 to 862 at depth 4), but the time per move went up (280 to 317 ms, 1283 to 1496 ms) because each node now does extra path computations. Because ordering also applies the 12-wall cap, the lower move agreement (80% and 33%) comes from both the order and the cap. This says the capped, ordered search picks different moves, not that it picks worse ones.
- **Transposition table.** No hits at depth 3. At depth 4 it saved about 7% of nodes (923 to 862) and about 18% of time (1834 to 1496 ms).
- **Noise.** Each row is one run on 15 positions. Differences of a few percent in time, like `all_on` against `no_tt` at depth 3, are within what we would expect from noise.

## 8. Web interface

A FastAPI server (`server/app.py`) exposes endpoints to start a game, get the state and legal moves, play a move, ask the AI for a move, get the shortest paths, undo, and check health. The server only accepts known opponents (random, greedy, alpha-beta with depth 1 to 4, MCTS with 50 to 1000 simulations) and keeps at most 200 sessions, dropping those idle for over 2 hours.

The browser interface (`web/`) is plain JavaScript modules with three screens (setup, game, result). You can move by clicking a dot or with the arrow keys, place a wall by clicking a gap, rotate with R or right-click, undo with U, and show shortest paths with P. A Dockerfile and `render.yaml` deploy it to Render's free tier; the first request after idle can take about a minute. The live demo is at https://quoridor-rqj3.onrender.com. The interface is not part of the evaluation.

## 9. Testing

`python -m pytest -q` runs 107 tests (about 100 seconds on the machine we used); `node --test tests/web` runs 7 tests for the arrow-key logic. The tests cover the state and wall encoding, BFS, the legality rules (jumps, diagonals, overlaps, crossings, the no-path rule), the evaluation and candidate walls, the baseline agents, the game runner, both search agents (on hand-built positions and in short games), the server API and the tournament harness.

What the tests do not cover: whether the pruned search plays better or worse than unpruned search, whether the evaluation weights are good, and the browser interface beyond the arrow-key logic.

## 10. Limitations

1. **Sample size.** 20 games per matchup resolves large gaps only. Alpha-beta against MCTS is undecided.
2. **Weak baselines.** Greedy places no walls in these runs and random plays randomly. Beating them shows little about strength.
3. **Hand-set parameters.** Evaluation weights, the 12-wall cap, rollout depth, the 0.95 rollout share and the tanh scale were chosen by hand and never tuned or compared.
4. **Pruning can miss moves.** Candidate walls only block the opponent's current shortest path. We measured speed, not lost move quality.
5. **Shallow search.** Alpha-beta looks 2 to 4 plies ahead, so walls whose value shows up later are missed.
6. **Small ablation.** 15 early-game positions from four games, one run each; timing is single-run.
7. **Timing.** Times were taken in Python with parallel games on one machine.
8. **No outside comparison.** We did not test against other Quoridor engines or human players.
9. **Not new.** Quoridor, alpha-beta and MCTS are standard. What this repository adds is a common rules engine and pruning shared by both agents, switches for measuring each speed-up, and a reproducible, seeded, seat-swapped tournament with exact statistics.

## 11. Team

The work was split by module:

- **Shubham**: constants, types, `GameState`, project setup, state tests.
- **Rajnish**: pathfinding, rules, legal move generation and their tests.
- **Siddhesh**: evaluation, candidate-move pruning, random and greedy agents, agent factory, game runner and their tests.
- **Shivam**: alpha-beta and MCTS agents and their tests.
- **Priyanshu**: tournament and ablation harness, statistics, server, web interface, deployment, report.

The git history has 33 commits from seven author names: Priyanshu (20) and Priyanshu-2308 (3), Rajnish (5), Shubham7094 (2), Shivam Yadav (1), Siddhesh Bansal (1) and Siddhesh1420 (1). Much of the later integration and fixing was committed from Priyanshu's account, so the history does not show exactly who wrote each part.

## 12. Reproducing everything

```bash
git clone https://github.com/Priyanshu-2308/QUORIDOR.git
cd QUORIDOR
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q                                  # 107 tests
node --test tests/web                                # 7 tests
python -m quoridor.tournament --suite --workers 4    # writes results/*.json, summary.csv
python results/stats.py                              # writes results/stats.txt
python -m quoridor.tournament --ablation             # writes results/ablation.csv
uvicorn server.app:app --port 8000                   # play in the browser
```

Existing result files are skipped unless `--force` is given. Reruns use the same seeds, but the timing columns will differ from ours.

## 13. Four-player extension

Following presentation feedback, the project was extended to four players on a dedicated branch `four-player` without modifying the two-player engine. The extension includes:
- An immutable four-player engine in `quoridor_n/` supporting both 4-player games (5 walls each, clockwise turn order, jumping rules) and 2-player mode.
- Four-player adaptations of search algorithms: Paranoid Alpha-Beta (`ParanoidAgent`), $Max^n$ multi-agent search (`MaxnAgent`), vector-payoff Monte Carlo Tree Search (`MCTSAgent`), and Greedy baseline (`GreedyAgent`).
- A seating permutation tournament harness and statistical inference module in `quoridor_n/tournament.py` and `quoridor_n/stats.py`.
- Complete pre-registered hypotheses, experiments (E0 to E4), ablations (A1 to A6), and slide facts documented in `docs/FOUR_PLAYER.md` and `results_n/slide_facts.md`.
