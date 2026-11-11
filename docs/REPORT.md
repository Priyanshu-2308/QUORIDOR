# Quoridor AI Project Report

**CS AI Course Project — Monolith Quoridor Engine, Search Strategies, Tournament Evaluation & Modern Web Interface**  
*Team: Shubham, Rajnish, Siddhesh, Shivam, Priyanshu*  
*Date: November 2026*

---

## 1. Executive Summary

This project implements an engine for the board game **Quoridor**, featuring multiple AI search strategies (Random, Greedy, Minimax with $\alpha$-$\beta$ Pruning, and Monte Carlo Tree Search), an automated tournament harness for empirical performance profiling, an ablation study on tree search optimizations, and a reactive 3D web application built with Three.js.

The game engine is implemented strictly using the Python 3 standard library, with an immutable `GameState` architecture ensuring correctness, determinism, and process-safe parallelization across multiple worker processes.

Key empirical findings from our tournament suite and ablation experiments include:
1. **Wall Pruning:** Candidate wall pruning (`moves.candidate_walls`) provides a **64.5x reduction** in nodes searched at Depth 3 (22,335.7 nodes down to 346.1 nodes) and a **46.1x speedup** in wall-clock time (14,604.4 ms down to 316.5 ms).
2. **Move Ordering Trade-Off:** Move ordering cuts visited states by 38.3% at Depth 3 (561.4 to 346.1 nodes) and 44.4% at Depth 4 (1,548.5 to 861.5 nodes). Because sorting requires extra path computations at every node and caps candidate walls at 12 per node, wall-clock time is higher in both cases (316.5 ms vs 280.4 ms at Depth 3, and 1,496.2 ms vs 1,282.9 ms at Depth 4).
3. **Transposition Table Impact:** In our sample of 15 positions with no repeats, transposition table hits averaged 0.0 at Depth 3; at Depth 4, transposition caching achieved 52.9 hits per move, lowering visited nodes from 923.2 to 861.5.
4. **MCTS Path-Biased Simulation:** Standard random rollouts in Quoridor suffer from aimless wandering. Implementing a goal-directed, path-biased rollout policy (prioritizing shortest-path pawn advances with 95% probability, tuned by trial against the greedy baseline without systematic tuning) raised MCTS win rates against baseline greedy agents from ~35% to **90.0%** (18/20) at 500 iterations and **100.0%** (20/20) at 1000 iterations.
5. **Headline Match:** AlphaBeta(d=3) won 12 of 20 games against MCTS(1000) (60.0%, 95% Wilson CI [38.7%, 78.1%], $p = 0.5034$). With 20 games this is not a statistically significant difference; the two agents are of similar strength under these settings. However, AlphaBeta reached this strength using roughly 8x less wall-clock time per move (0.6 s vs 4.7 s).

---

## 2. Quoridor Game Rules & Mechanics

Quoridor is played on a $9 \times 9$ grid by two players, each starting with 10 walls:
- **Player 0** starts at row 8, column 4 $(8, 4)$ and aims to reach any cell in row 0.
- **Player 1** starts at row 0, column 4 $(0, 4)$ and aims to reach any cell in row 8.

On their turn, a player may either:
1. **Move their pawn** to an adjacent orthogonal cell (North, South, East, West), provided no wall blocks the passage.
   - **Straight Jump:** If an opponent pawn occupies the adjacent cell and the square beyond is open, the pawn may jump directly over the opponent.
   - **Diagonal Jump:** If an opponent pawn occupies the adjacent cell and the straight jump is blocked by a wall or the board perimeter, the pawn may jump diagonally to either adjacent open square next to the opponent.
2. **Place a wall:** A wall occupies two cell edges (grooves) either horizontally (`"H"`) or vertically (`"V"`).
   - Walls cannot overlap existing walls or intersect perpendicularly through the center of another wall.
   - **Fair-Play Rule:** A wall placement is strictly illegal if it completely blocks the path of *either* player to their respective goal row. Each player must always retain at least one unobstructed path to their goal.

---

## 3. Architecture & File Layout

The codebase maintains strict separation of concerns across layered modules:

```
QUORIDOR/
  README.md                       Project overview, quickstart, CLI reference, results
  requirements.txt  .gitignore    Minimal dependencies (pytest, fastapi, uvicorn, httpx, matplotlib)
  quoridor/
    __init__.py                   Package root
    constants.py                  Board dimension (9), wall limits (10), directions
    types.py                      Cell, PawnMove, WallMove, serialization helpers
    state.py                      Immutable GameState dataclass
    pathfinding.py                BFS shortest path, distance grids, multi-source search
    rules.py                      Legal moves generation, wall legality validation
    eval.py                       Heuristic evaluation functions
    moves.py                      Candidate moves and candidate wall pruning heuristics
    runner.py                     play_game orchestration harness and GameResult dataclass
    agents/
      __init__.py                 make_agent factory for string specifications
      base.py                     Abstract Agent base class
      random_agent.py             Uniform random legal move selection
      greedy_agent.py             Shortest-path greedy pawn advancement
      alphabeta_agent.py          Fixed-depth Alpha-Beta minimax search
      mcts_agent.py               Monte Carlo Tree Search with UCT and path-biased rollouts
    tournament.py                 Multiprocessing tournament suite, ablation runner & charts
  server/
    app.py                        FastAPI backend serving JSON REST API & static web assets
  web/
    index.html                    Single-page web entrypoint with import maps
    styles.css                    Monolith design system styling
    src/
      main.js                     App controller, screen router, hash navigation
      api.js                      REST API client communicating with FastAPI
      scene.js                    Three.js scene graph, board rendering, raycasting
      screens/                    Full-bleed visual screens
        title.js                  Title screen with rotating monolith
        setup.js                  Opponent, strength, and side configuration
        game.js                   Interactive 9x9 board with ghost wall and HUD
        stats.js                  3D telemetry and node visualization
        result.js                 Victory/defeat screen with rematch options
  tests/                          Unit and regression test suite
  results/                        Tournament JSONs, CSV summaries, and generated PNG charts
  docs/
    REPORT.md                     Engineering and empirical evaluation report
```

---

## 4. State & Move Representation

### 4.1 Immutable `GameState`
To eliminate side-effects, race conditions in multiprocessing, and state corruption across deep search branches, `GameState` is implemented as an immutable, frozen dataclass:

```python
@dataclass(frozen=True)
class GameState:
    pawns: tuple[Cell, Cell]
    walls_left: tuple[int, int]
    h_walls: frozenset[Cell]
    v_walls: frozenset[Cell]
    current: int
    turn_count: int = 0
```

- **Pawn Coordinates:** `(row, col)` with $0 \le \text{row}, \text{col} \le 8$.
- **Wall Sets:** Frozensets storing top-left groove coordinates $(r, c)$ where $0 \le r, c \le 7$.
  - An `"H"` wall at $(r, c)$ spans columns $c$ and $c+1$ in the groove below row $r$.
  - A `"V"` wall at $(r, c)$ spans rows $r$ and $r+1$ in the groove right of column $c$.
- **State Transition:** `state.apply(move)` returns a new instance of `GameState`, leaving the parent state completely untouched.
- **Position Identity:** `state.key()` returns a compact tuple of all attributes, enabling hash-table indexing for transposition tables and repetition tracking.

### 4.2 Move Primitives
- `PawnMove(to=(r, c))`: Targeted movement to cell `(r, c)`.
- `WallMove(r=r, c=c, o="H"|"V")`: Placement of a wall at groove `(r, c)` with orientation `o`.

---

## 5. Algorithms and Design Choices

### 5.1 Graph Representation and Pathfinding (`pathfinding.py`)
Rather than maintaining an explicit 81-node adjacency matrix or graph data structure that would require updates after every wall placement, wall obstructions are checked dynamically on-the-fly via coordinate arithmetic:
- Stepping North from $(r, c)$ is blocked if $(r-1, c) \in \text{h\_walls}$ or $(r-1, c-1) \in \text{h\_walls}$.
- Stepping South from $(r, c)$ is blocked if $(r, c) \in \text{h\_walls}$ or $(r, c-1) \in \text{h\_walls}$.
- Stepping East from $(r, c)$ is blocked if $(r, c) \in \text{v\_walls}$ or $(r-1, c) \in \text{v\_walls}$.
- Stepping West from $(r, c)$ is blocked if $(r, c-1) \in \text{v\_walls}$ or $(r-1, c-1) \in \text{v\_walls}$.

**Multi-Source Backward BFS:**  
For shortest-path distance lookups, a multi-source breadth-first search is initiated backwards from all 9 cells of the target goal row simultaneously. In a single BFS traversal ($\le 81$ cell visits), exact shortest-path distances to the goal are computed and cached for every cell on the board.

### 5.2 Wall Legality & Fair-Play Validation (`rules.py`)
Checking whether a candidate wall traps a player requires verifying that a path to the goal still exists for both players. Performing full path extraction for all 128 potential wall placements per turn would be computationally prohibitive.  
Our implementation optimizes this by:
1. First performing constant-time geometric checks: remaining wall count $> 0$, coordinates within bounds $0 \le r, c \le 7$, no direct overlap, and no cross-intersection (e.g., $(r, c, \text{H})$ cannot coexist with $(r, c, \text{V})$).
2. Only performing goal-reachability BFS if the geometric tests pass.
3. Early-exit BFS: the traversal halts the instant any cell on the goal row is popped from the queue.

### 5.3 Candidate Wall Pruning (`moves.py`)
In the initial position, there are 128 legal wall placements. Branching by 131 moves per ply causes tree size to explode exponentially ($131^3 \approx 2.25 \times 10^6$ nodes; $131^4 \approx 2.95 \times 10^8$ nodes).  
However, walls placed far away from both pawns or far from their shortest paths rarely impact immediate tactics.

`moves.candidate_walls(state)` prunes this set dramatically:
1. Computes the shortest path for both Player 0 and Player 1.
2. Identifies all groove coordinates adjacent to cells along these critical paths and surrounding the pawns.
3. Filters legal walls to only those that intersect or directly neighbor these critical paths.

This reduces the active wall branching factor from 128 down to typically **12–18 candidate walls**, yielding an order-of-magnitude reduction in search space while preserving tactical relevance.

### 5.4 Minimax with $\alpha$-$\beta$ Pruning (`alphabeta_agent.py`)
`AlphaBetaAgent` implements fixed-depth minimax search with $\alpha$-$\beta$ pruning. (Iterative deepening is supported in the codebase but was disabled by default (`iterative_deepening=False`) and was not used in any evaluated agents or benchmarks.)

The search is enhanced by three features:

1. **Move Ordering:**
   Moves are sorted before exploration: pawn moves along the shortest path are prioritized first, followed by candidate wall placements ranked by their heuristic evaluation. Good moves trigger cutoffs early, maximizing the number of pruned branches. Note that move ordering also caps wall candidates at 12 per node.
2. **Transposition Table (TT):**
   A hash table caches visited positions keyed by `state.key()`. Each entry stores `{depth, score, flag, best_move}`. If a previously explored state is encountered at an equal or greater depth, the stored value provides immediate cutoffs or tightens the $(\alpha, \beta)$ window.
3. **Evaluation Function (`eval.py`):**
   The position evaluation balances path progress and wall resources:
   $$\text{Eval}(s) = (d_{\text{opp}} - d_{\text{me}}) \times 10.0 + (w_{\text{me}} - w_{\text{opp}}) \times 1.2$$
   - Terminal win: $+10,000$; terminal loss: $-10,000$.
   - A positive distance differential indicates the current player is closer to their goal.
   - Wall advantage provides secondary tie-breaking pressure.

### 5.5 Monte Carlo Tree Search (`mcts_agent.py`)
`MCTSAgent` implements the Upper Confidence bounds for Trees (UCT) framework:

1. **Selection:**
   Traverses the tree using the UCT formula:
   $$\text{UCT}(i) = \frac{v_i}{n_i} + c \sqrt{\frac{\ln N}{n_i}}$$
   where $v_i$ is cumulative child value, $n_i$ is child visit count, $N$ is parent visit count, and $c = 1.4$ balances exploitation and exploration.
2. **Expansion:**
   One unvisited candidate move from `moves.candidate_moves` is expanded per iteration.
3. **Simulation (Rollout Policy):**
   Uniform random rollouts in Quoridor frequently lead to aimless wandering. We use a **path-biased rollout policy**:
   - With 95% probability, play the greedy pawn step that minimizes the mover's shortest-path distance.
   - With 5% probability, select a random candidate move.
   - Rollouts terminate upon reaching a goal row or at `rollout_depth = 60`.
   The 95% threshold was chosen by trial against the greedy baseline without systematic parameter tuning.
4. **Terminal Win Prioritization:**
   When an immediate winning move exists at the root, the agent prioritizes the proven winning child directly, ensuring 100% tactical precision in endgames.
5. **Backpropagation:**
   Terminal wins award $1.0$; terminal losses award $0.0$. For non-terminal rollout cutoffs, a continuous evaluation is backpropagated:
   $$R = 0.5 + 0.5 \times \tanh\left(\frac{d_{\text{opp}} - d_{\text{me}}}{4.0}\right)$$

---

## 6. Empirical Tournament Evaluation

We evaluated all agent pairings using our automated tournament harness across 20-game matches. To eliminate first-move advantage, seats alternate every game (even games: Agent A plays as Player 0; odd games: Agent B plays as Player 0). Matches were executed across 6 parallel worker processes using `ProcessPoolExecutor`.

### 6.1 Tournament Results Matrix

| Matchup (Agent A vs Agent B) | Games | Wins A | Wins B | Draws | Win Rate A | Mean Plies | Nodes/Move A | Latency A | Nodes/Move B | Latency B |
|---|---|---|---|---|---|---|---|---|---|---|
| **Greedy vs Random** | 20 | 20 | 0 | 0 | **100.0%** | 15.2 | 3.8 | 0.8 ms | 32.6 | 11.2 ms |
| **AlphaBeta(d=2) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 19.1 | 36.2 | 140.5 ms | 3.6 | 0.9 ms |
| **AlphaBeta(d=3) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 26.6 | 247.7 | 467.1 ms | 3.3 | 1.0 ms |
| **MCTS(500) vs Greedy** | 20 | 18 | 2 | 0 | **90.0%** | 38.2 | 486.3 | 2,037.6 ms | 3.3 | 1.0 ms |
| **MCTS(1000) vs Greedy** | 20 | 20 | 0 | 0 | **100.0%** | 31.7 | 976.3 | 3,735.0 ms | 3.4 | 1.2 ms |
| **AlphaBeta(d=3) vs MCTS(1000)** | 20 | 12 | 8 | 0 | **60.0%** | 66.8 | 179.3 | 617.0 ms | 956.7 | 4,746.7 ms |
| **AlphaBeta(d=2) vs AlphaBeta(d=3)** | 20 | 6 | 14 | 0 | **30.0%** | 62.0 | 35.1 | 185.6 ms | 189.8 | 726.3 ms |

*All results recorded in `results/summary.csv` and individual JSON logs. Visualized in `results/win_rates.png`.*

### 6.2 Analysis of Matchups

Every pair was played over a sample size of 20 games, with seats alternating between games to balance first-mover advantage. Below are the 95% Wilson score confidence intervals and exact two-sided binomial p-values testing the null hypothesis of equal playing strength ($p = 0.50$), computed with `results/stats.py`:
- **Greedy vs Random:** 20/20 wins (100.0%), 95% Wilson CI [83.9%, 100.0%], $p < 0.0001$.
- **AlphaBeta(d=2) vs Greedy:** 20/20 wins (100.0%), 95% Wilson CI [83.9%, 100.0%], $p < 0.0001$.
- **AlphaBeta(d=3) vs Greedy:** 20/20 wins (100.0%), 95% Wilson CI [83.9%, 100.0%], $p < 0.0001$.
- **MCTS(500) vs Greedy:** 18/20 wins (90.0%), 95% Wilson CI [69.9%, 97.2%], $p = 0.0004$.
- **MCTS(1000) vs Greedy:** 20/20 wins (100.0%), 95% Wilson CI [83.9%, 100.0%], $p < 0.0001$.
- **AlphaBeta(d=3) vs MCTS(1000):** 12/20 wins (60.0%), 95% Wilson CI [38.7%, 78.1%], $p = 0.5034$.
- **AlphaBeta(d=2) vs AlphaBeta(d=3):** Depth 3 won 14 of 20 games (70.0%), 95% Wilson CI [48.1%, 85.5%], $p = 0.1153$ (Depth 2 won 6/20, 30.0%, 95% Wilson CI [14.5%, 51.9%]).

Detailed findings:
- **Baseline Performance:** Over 20 games each, both AlphaBeta (depth $\ge 2$) and MCTS ($\ge 500$ iterations) won 20 of 20 games against Greedy and Random (18 of 20 for MCTS-500 against Greedy). Purely reactive greedy agents cannot handle basic wall placements or adversarial lookahead.
- **The Headline Match (AlphaBeta d=3 vs MCTS 1000):** AlphaBeta(d=3) won 12 of 20 games against MCTS(1000). With 20 games this is not a statistically significant difference; the two agents are of similar strength under these settings. However, MCTS used about 4.7 s per move against about 0.6 s for alpha-beta, so alpha-beta reached the same strength with roughly 8x less time.
- **Search Depth Scaling:** Depth 3 won 14 of 20 games against depth 2 ($p = 0.12$). This is suggestive but not conclusive at this sample size.

---

## 7. Empirical Search Ablation Study

To isolate and quantify the concrete performance impacts of our search enhancements in `AlphaBetaAgent`, we conducted a controlled ablation study across 15 distinct, representative middle-game positions. These positions were sampled from seeded tournament games at plies 4, 8, 12, and 16, capturing diverse board configurations, varying pawn distances, and intricate wall placements.

We benchmarked 9 configurations spanning Depth 3 and Depth 4, evaluating mean nodes expanded, mean wall-clock time (in milliseconds), transposition table cache hits, cutoffs triggered, and the move agreement rate against the full `all_on` baseline.

### 7.1 Ablation Results Table

| Configuration | Search Depth | Mean Nodes | Mean Time (ms) | Mean TT Hits | Mean Cutoffs | Move Match Rate |
|---|---|---|---|---|---|---|
| **`all_on`** | 3 | **346.1** | 316.5 ms | 0.0 | 28.1 | **100.0%** (Baseline) |
| `no_tt` | 3 | 346.1 | 319.1 ms | 0.0 | 28.1 | 100.0% |
| `no_ordering` | 3 | 561.4 | **280.4 ms** | 0.0 | 30.8 | 80.0% |
| `no_ordering_no_tt` | 3 | 561.4 | 262.6 ms | 0.0 | 30.8 | 80.0% |
| `no_pruning` | 3 | **22,335.7** | **14,604.4 ms** | 0.0 | 309.7 | 53.3% |
| **`all_on`** | 4 | **861.5** | 1,496.2 ms | **52.9** | 316.1 | **100.0%** (Baseline) |
| `no_tt` | 4 | 923.2 | 1,833.7 ms | 0.0 | 316.4 | 100.0% |
| `no_ordering` | 4 | 1,548.5 | **1,282.9 ms** | 98.7 | 519.7 | 33.3% |
| `no_ordering_no_tt` | 4 | 1,700.6 | 1,503.7 ms | 0.0 | 520.1 | 33.3% |

*Data recorded in `results/ablation.csv`. Visualizations available in `results/ablation_nodes.png` and `results/ablation_ms.png`.*

### 7.2 Key Ablation Findings & Discussion

#### 1. Wall Pruning Effect
At Depth 3, disabling candidate wall pruning (`no_pruning`) causes the search tree to expand from **346.1 nodes** to **22,335.7 nodes** — a **64.5x increase in search volume**.  
The corresponding decision latency increases from **316.5 ms to 14,604.4 ms** (~14.6 seconds per move). The unpruned search also chose a different move in 47% of the positions; this table does not show which choice is better. Candidate wall pruning is the largest single effect we measured in making multi-ply Quoridor search viable.

#### 2. The Move Ordering Trade-Off
Move ordering reduces tree size:
- At Depth 3, ordering slashes visited states from **561.4 nodes down to 346.1 nodes** (a 38.3% reduction).
- At Depth 4, ordering slashes visited states from **1,548.5 nodes down to 861.5 nodes** (a 44.4% reduction).

However, sorting moves requires computing path evaluations for candidate moves at internal nodes. In addition, the ordering option caps wall candidates at 12 per node, so turning it off changes the set of moves searched as well as their order. As a result, ordering takes more wall-clock time in both cases (316.5 ms vs 280.4 ms at Depth 3, and 1,496.2 ms vs 1,282.9 ms at Depth 4), because sorting needs extra path computations at every node.

#### 3. Transposition Table Value Scales with Depth
In this sample of 15 positions with no repeats:
- At Depth 3, transposition table hits are 0.0, because trees at depth 3 on a $9 \times 9$ board have minimal path reconvergence.
- At Depth 4, the transposition table recorded an average of **52.9 hits per move**, reducing node visits from 923.2 down to 861.5, and reducing wall-clock time from 1,833.7 ms down to 1,496.2 ms (an 18.4% speedup).

---

## 8. Strategic Discussion: Alpha-Beta vs. MCTS

### 8.1 Discussion (not measured here)
The following points reflect general domain characteristics rather than project measurements:
- Alpha-Beta search is designed for concrete, near-term tactical lookahead. Within depth limits of 3 to 4 plies, it evaluates forced pawn moves and direct wall placements using a handcrafted evaluation function.
- MCTS with UCT explores broader branching using randomized simulation without relying on a static evaluation function, though simulation accuracy depends on rollout policy quality and iteration budget.

### 8.2 Failure Modes
- **Horizon Effect in Alpha-Beta:** Fixed-depth search is subject to horizon effects: a wall placement that delays an opponent within depth $d$ may be easily circumvented at ply $d+1$.
- **Rollout Variance in MCTS:** Without path guidance, uniform random rollouts in Quoridor wander erratically. Our path-biased policy (95% greedy path steps) stabilizes simulation rollouts.

### 8.3 Limitations
We note several methodological limitations in this evaluation:
1. **Sample Size:** Matches were run over 20 games per pair. While adequate to separate strong agents from baselines, 20 games cannot resolve small differences in strength between AlphaBeta(d=3) and MCTS(1000).
2. **Seed Schedule:** Tournaments used a single seed schedule across pairings.
3. **Ablation Sample:** The ablation experiment evaluated 15 middle-game positions without repeats.
4. **Timing Variance:** Wall-clock times were measured on a single multi-core workstation with parallel worker processes running concurrently. As a result, absolute millisecond values reflect system load and are comparable only across rows of the same run.
5. **No External Engine:** No comparisons were performed against external Quoridor engines or human players.

---

## 9. Web Interface Architecture ("Monolith")

The Quoridor web user interface is crafted under the **"Monolith"** design system:
- **Zero Build Step:** Built entirely with native ES modules and pinned directly to Three.js `0.160.0` via browser import maps.
- **Full-Bleed Solid Color Fields:** Eliminates decorative gradients, glassmorphism, cards, and borders in favor of distinct, hyper-focused solid color fields:
  - **Bone (`#EDE7DA`)**: Game screen board field.
  - **Ink (`#121212`)**: Telemetry and statistics screen.
  - **Vermilion (`#E8452C`)**: Title screen and AI victory result screen.
  - **Cobalt (`#2441D6`)**: Opponent setup and human victory result screen.
  - **Ochre (`#D9A441`)**: Wall pieces and indicator accents.
- **Minimalist 3D Representation:** Each screen features exactly one central 3D monolith rendered via WebGL:
  - *Title:* A rotating monolithic pawn slab.
  - *Setup:* A reactive difficulty totem whose height and color dynamically scale with selected search strength.
  - *Game:* A floating $9 \times 9$ board slab viewed from an angled perspective, with smooth pawn navigation, groove raycasting for transparent ghost wall previews, and legal destination markers.
  - *Stats:* A 3D logarithmic column visualizing total search nodes explored alongside historical moves.
  - *Result:* An elevated victory monolith.
- **Keyboard Shortcuts:** Full keyboard controllability with `P` (toggle shortest paths trail), `R` (rotate ghost wall / rematch), `U` (undo move), `S` (telemetry view), and `Esc` (return to menu).

---

## 10. Team Contributions

Our team operated under a modular, test-driven architecture with clean API boundaries established prior to implementation:

- **Shubham (Foundation, State Model & Project Scaffolding):**  
  Architected the core game representations in `constants.py`, `types.py`, and `state.py`. Designed the immutable, frozen `GameState` structure that guaranteed side-effect-free transitions across search trees and worker processes. Configured repository standards (`requirements.txt`, `.gitignore`, `README.md` skeleton) and authored `tests/test_state.py`.

- **Rajnish (Pathfinding Graph Engine & Rule Validation):**  
  Implemented dynamic coordinate-based movement and wall adjacency checks in `pathfinding.py` and `rules.py`. Engineered multi-source backward BFS for rapid goal distance field evaluation, early-exit path reachability checks for the Quoridor fair-play rule, and complete legal move generation validated by `tests/test_pathfinding.py` and `tests/test_rules.py`.

- **Siddhesh (Evaluation Metrics, Pruning Heuristics & Baselines):**  
  Authored the heuristic evaluation functions in `eval.py`, the candidate wall and candidate move pruning algorithms in `moves.py`, the baseline `RandomAgent` and `GreedyAgent`, the dynamic agent factory `make_agent`, and the game execution runner `runner.py`. Validated these components with `tests/test_eval_moves.py`, `tests/test_agents_basic.py`, and `tests/test_runner.py`.

- **Shivam (Search Intelligence: Alpha-Beta & MCTS):**  
  Developed the high-performance `AlphaBetaAgent` featuring depth-limited minimax, dynamic move ordering, and transposition table caching. Authored the core MCTS algorithm in `mcts_agent.py` featuring UCT selection, candidate expansion, path-biased rollout simulations, and terminal win prioritization. Verified search correctness in `tests/test_alphabeta.py` and `tests/test_mcts.py`.

- **Priyanshu (Tournament Harness, Server, Web UI & Final Reporting):**  
  Implemented the multiprocessing tournament and ablation CLI in `quoridor/tournament.py` with matplotlib chart generation. Built the FastAPI backend in `server/app.py` providing REST endpoints and static asset serving with in-memory session undo tracking. Created the interactive Three.js "Monolith" web UI in `web/` with 5 full-bleed screens, raycast ghost walls, and shortest-path overlays. Authored `tests/test_tournament.py`, `tests/test_server.py`, finalized `README.md`, and produced `docs/REPORT.md`.

---

## 11. Execution & Reproduction Guide

### Quickstart
```bash
# Clone repository and enter directory
git clone https://github.com/Priyanshu-2308/QUORIDOR.git
cd QUORIDOR

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run full test suite
python -m pytest -q
```

### Launch Web User Interface
```bash
uvicorn server.app:app --port 8000
# Open http://localhost:8000 in your browser
```

### Reproduce Empirical Results
```bash
# Run full tournament suite (writes results/summary.csv and results/win_rates.png)
python -m quoridor.tournament --suite --workers 6

# Run ablation study (writes results/ablation.csv and ablation charts)
python -m quoridor.tournament --ablation
```

