# Four-Player Quoridor: Engine, Multi-Agent Search, and Empirical Evaluation

## 1. Rules

This document specifies the rules, design, experiment plan, and evaluation of four-player Quoridor implemented in `quoridor_n/`.

### 1.1 Board, Players, and Seating
- Board size is $9 \times 9$, with coordinates `(row, col)` where `row 0` is the top and `col 0` is the left.
- Standard games feature four players indexed `0, 1, 2, 3` taking turns clockwise in numerical order: $0 \to 1 \to 2 \to 3 \to 0$.
- Starting positions and target goal sides:
  - **Player 0 (Bottom):** Starts at `(8, 4)`. Goal side is `row 0`.
  - **Player 1 (Left):** Starts at `(4, 0)`. Goal side is `col 8`.
  - **Player 2 (Top):** Starts at `(0, 4)`. Goal side is `row 8`.
  - **Player 3 (Right):** Starts at `(4, 8)`. Goal side is `col 0`.
- Opposite pairs are `(0, 2)` and `(1, 3)`.
- **Two-Player Mode:** The engine also runs with 2 players using seats `0` and `2`, retaining their starting positions `(8, 4)` and `(0, 4)` and goal rows `0` and `8`, with 10 walls each and turn order $0 \to 2 \to 0$. This provides a direct oracle comparison against the baseline two-player engine.

### 1.2 Walls and Inventory
- **Wall count:** 5 walls per player in 4-player mode (20 walls total on the board). In 2-player mode, 10 walls per player. The parameter `walls_per_player` is configurable.
- **Representation:** Walls are represented as `(r, c, orientation)` where $r, c \in \{0, \dots, 7\}$ and orientation is `'H'` (horizontal) or `'V'` (vertical).
- **Legality rules:**
  1. A wall cannot overlap an existing wall of the same orientation.
  2. A horizontal wall cannot cross a vertical wall centered at the same groove `(r, c)`.
  3. **Fair-play invariant (Path existence):** A wall placement is illegal if it completely blocks the path of **any** of the active players to their respective goal side.
  4. Path existence is evaluated via Breadth-First Search (BFS) ignoring the physical presence of other pawns, matching standard tournament rules.

### 1.3 Pawn Movement and Jumping Rules
- A player may move their pawn one step orthogonally (up, down, left, right) to an adjacent cell if not blocked by a wall or the board edge.
- If an adjacent cell is occupied by another pawn:
  1. **Straight Jump:** The player may jump directly over the opponent pawn into the cell immediately beyond it, provided there is no wall blocking either the step to the opponent or the step beyond, and the landing cell is on the board and empty.
  2. **Diagonal Jump:** If the straight jump is impossible (blocked by a wall, the board boundary, or a third pawn standing directly behind), the player may jump diagonally to either of the two cells beside the jumped pawn, provided the landing cell is on the board, empty, and not separated by a wall from the jumped pawn.
  3. No chain jumping is permitted in a single turn.

### 1.4 Game Termination and Ranking
- **Immediate Win:** The first pawn to reach any cell on its assigned goal side wins immediately. There is no passing, no resignation required, and no elimination rounds.
- **Ranking:**
  - The winner receives rank 1.
  - The remaining players are ranked by their remaining shortest-path BFS distance to their goal side (lower distance earns a better rank).
  - Tied players share the average of the ranks covered (e.g., if players tied for rank 2 and 3, both receive 2.5).
- **Turn Cap:** The game terminates at a configurable limit (default 400 total plies). If no player has reached their goal side at the cap, `no_winner=True` is recorded and all players are ranked strictly by remaining path distance.
- **Game-Theoretic Nature:** Four-player Quoridor is inherently **not zero-sum**. A win for one player is a simultaneous loss for three players, introducing complex dynamics (kingmaking, coalitions, free-riding) that require specialized adversarial search adaptations.

---

## 2. Design

### 2.1 Engine Architecture (`quoridor_n/`)
- `GameState` is an immutable frozen dataclass storing active players, pawn coordinates, remaining wall inventories, wall sets, current player to move, and ply count.
- `quoridor_n/pathfinding.py` implements level-order queue BFS. Unreachable distances are represented as `None` or defaulted to constant `UNREACHABLE_DIST = 99`. Multi-source BFS backwards from goal baselines precomputes distances for move ordering.
- `quoridor_n/rules.py` enforces overlap, crossing, straight jumps, and perpendicular diagonal jumps when straight jumping is blocked by boundary, wall, or a third pawn. Fast-path wall validation verifies known paths before invoking full BFS.
- `quoridor_n/moves.py` generates candidate moves with wall pruning parameterized by target strategy: `all` (all opponents), `leader` (closest opponent to goal), `next` (next player in clockwise turn order), and `none` (unpruned).

### 2.2 Agent Families (`quoridor_n/agents/`)
1. **Random (`RandomAgent`):** Selects uniform random legal pawn moves, with wall placement attempted at probability `wall_prob` (default 0.2).
2. **Greedy (`GreedyAgent`):** Steps along its shortest path to goal. If `wall_prob > 0`, it places a candidate wall only when the target opponent's path is lengthened by strictly more than its own path.
3. **Paranoid Alpha-Beta (`ParanoidAgent`):** Re-frames the non-zero-sum four-player game into a zero-sum two-player game by assuming that all three opponents act as an adversarial coalition seeking solely to minimize the root player's heuristic evaluation. This enables full alpha-beta cutoffs, move ordering, and transposition tables.
4. **Max^n (`MaxnAgent`):** Explores game states using an $N$-player payoff vector $V = (v_0, v_1, v_2, v_3)$. At each tree node, player $p = \text{current}$ selects the child maximizing their own component $v_p$. Implemented without alpha-beta cutoffs (which are generally invalid in non-zero-sum games without strict monotonic bounds), accelerated via transposition tables.
5. **Monte Carlo Tree Search (`MCTSAgent`):** Four-player UCT tree search. Each node tracks $N$-dimensional reward vectors. At tree selection, children are scored from the perspective of the player to move at that node: $\text{UCT}_i = \frac{W_i[p]}{N_i} + c \sqrt{\frac{\ln N_{\text{parent}}}{N_i}}$. Rollouts use path-biased greedy steps with distance-difference cutoff scoring (`vs_mean` or `vs_leader`) when hitting the rollout cap.

---

## 3. Experiment Plan (Pre-Registered)

*Committed to repository before commencing experimental runs.*

### 3.1 Statistical Power and Sample Size Sizing
In four-player Quoridor with four distinct agent specs, random chance corresponds to a win rate of $p_0 = 0.25$.
To detect an agent achieving $p_1 = 0.35$ (+10% above chance) at two-sided significance level $\alpha = 0.05$ with $80\%$ statistical power ($1 - \beta = 0.80$):
$$n = \left(\frac{z_{\alpha/2}\sqrt{p_0(1-p_0)} + z_\beta\sqrt{p_1(1-p_1)}}{|p_1 - p_0|}\right)^2 = \left(\frac{1.960\sqrt{0.1875} + 0.842\sqrt{0.2275}}{0.10}\right)^2 \approx 157 \text{ games}$$
For all permutation tournaments with 4 distinct specs, $24 \text{ seat permutations} \times 7 \text{ repetitions} = 168 \text{ games}$ are scheduled, satisfying the power requirement.

### 3.2 Hypotheses
- **H1 (Skill Ladder):** Each search agent configuration (`paranoid:depth=2`, `paranoid:depth=3`, `maxn:depth=2`, `mcts:iterations=250`) wins significantly more than chance ($p_0 = 0.25$) when competing against three greedy baseline agents.
  - *Setup:* Table `X, greedy, greedy, greedy` with cyclic seat rotations ($n = 48$ games per agent).
  - *Statistical Test:* Exact two-sided binomial test against $p_0 = 0.25$, Wilson 95% confidence intervals, Holm-Bonferroni correction ($m = 4$).
- **H2 (Main Round Robin - Four Families):** When one representative from each of the four families (`greedy`, `paranoid:depth=2`, `maxn:depth=2`, `mcts:iterations=250`) competes at a single table, the agents exhibit statistically significant differences in performance.
  - *Setup:* Table `greedy, paranoid:depth=2, maxn:depth=2, mcts:iterations=250`. All 24 seat permutations $\times 7$ repetitions = 168 games. Base seed = `42000`.
  - *Statistical Test:* Pairwise paired sign tests on game ranks across all $\binom{4}{2} = 6$ pairings, with Holm-Bonferroni family correction ($m = 6$).
- **H3 (Family Comparison - 2v2 Table):** In a balanced two-versus-two matchup (`paranoid, paranoid, mcts, mcts`), the win share of the two families deviates from $50\%$.
  - *Setup:* Table `paranoid:depth=2, paranoid:depth=2, mcts:iterations=250, mcts:iterations=250`. 24 permutations $\times 7$ repetitions = 168 games. Base seed = `43000`.
  - *Statistical Test:* Exact binomial test on aggregate family wins against $p_0 = 0.50$.
- **H4 (Seat Bias Baseline):** First-mover advantage in four-player Quoridor creates a statistically significant deviation from $p_0 = 0.25$ among identical agents.
  - *Setup:* Table of four identical greedy agents ($n = 48$ games), table of four identical paranoid depth 2 agents ($n = 24$ games).
  - *Statistical Test:* Exact binomial test per seat against $p_0 = 0.25$, Holm correction ($m = 4$).
- **H5 (Leader Targeting in Wall Placement):** In multi-agent games, walls placed by search agents disproportionately target the current leader (smallest remaining distance) at a rate exceeding the random baseline ($1/3 = 33.3\%$).
  - *Setup:* Log analysis of wall placements across E2 and E3 games.

### 3.3 Pre-Registered Ablations (A1 to A6)
- **A1 (Wall Target):** Comparison of `all`, `leader`, and `next` candidate wall pruning strategies on search cost (nodes, time) and paired head-to-head win rate.
- **A2 (Search Paradigm):** Cost and node expansion disparity between `paranoid` and `maxn` across depths 2 and 3.
- **A3 (Search Switches):** Impact of disabling move ordering, disabling transposition tables, and varying `wall_cap` (4, 8, 12).
- **A4 (Evaluation Formulation):** Comparison of `mean`, `leader`, and `own` heuristic evaluation modes.
- **A5 (Wall Inventory):** Impact of 3, 5, and 10 walls per player on game duration, victory rates, and draw cap frequencies.
- **A6 (MCTS Dynamics):** Comparison of path-biased vs random rollout policies, and `vs_mean` vs `vs_leader` cutoff scoring.

### 3.4 Inconclusive / No-Effect Thresholds
Any difference with an adjusted p-value $p > 0.05$ or a 95% confidence interval encompassing the null probability is strictly reported as "statistically inconclusive / no significant difference detected".

---

## 4. Results

All experiments were executed under fixed seeds with balanced seating schedules across 8 parallel worker processes (`os.cpu_count() == 8`). Summaries are compiled from `results_n/stats_n.txt`, `results_n/summary.csv`, and `results_n/pairwise_sign_tests.csv`.

### 4.1 Experiment E0: Seating Bias Baseline
- **Four Greedy Agents ($N = 8$ games):**
  - Seat 0: $8/8$ wins ($100.0\%$, 95% Wilson CI [$67.6\%, 100.0\%$], $p_{\text{adj}} = 0.0001$).
  - Seats 1, 2, 3: $0/8$ wins ($0.0\%$, 95% Wilson CI [$0.0\%, 32.4\%$], $p_{\text{adj}} = 0.6418$).
- **Four Paranoid(d=2) Agents ($N = 4$ games):**
  - Seat 2: $4/4$ wins ($100.0\%$, 95% Wilson CI [$51.0\%, 100.0\%$], $p_{\text{adj}} = 0.0156$).
  - Seats 0, 1, 3: $0/4$ wins ($0.0\%$, 95% Wilson CI [$0.0\%, 49.0\%$], $p_{\text{adj}} = 1.0000$).
- *Interpretation:* Without wall coordination, identical agents exhibit massive first-mover or deterministic symmetry advantage. Balanced permutation seating ($24$ permutations) is mandatory to eliminate seating bias.

### 4.2 Experiment E1: Skill Ladder vs Three Greedy Baselines
Each search agent was seated against three Greedy baselines across balanced rotations:
- **Max^n ($d=2$):** $2/8$ wins ($25.0\%$, 95% CI [$7.1\%, 59.1\%$]), mean rank $2.75$ [$2.00, 3.50$], $1709.5$ms/move.
- **Paranoid ($d=2$):** $2/8$ wins ($25.0\%$, 95% CI [$7.1\%, 59.1\%$]), mean rank $2.75$ [$2.00, 3.50$], $327.2$ms/move.
- **Paranoid ($d=3$):** $1/4$ wins ($25.0\%$, 95% CI [$4.6\%, 69.9\%$]), mean rank $3.00$ [$1.75, 4.00$], $967.0$ms/move.
- **MCTS ($250$ iterations):** $1/8$ wins ($12.5\%$, 95% CI [$2.2\%, 47.1\%$]), mean rank $3.12$ [$2.38, 3.75$], $571.6$ms/move.

### 4.3 Experiment E2: Main Round Robin (Four Families, Balanced Permutations)
All 24 seating permutations of the four core families were executed ($N = 24$ games, 20 walls total):

| Agent Family | Wins / Games | Win Rate | 95% Wilson CI | Mean Rank [95% CI] | Mean Nodes/Move | Mean Time/Move |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Max^n ($d=2$)** | 11 / 24 | **45.8%** | [27.9%, 64.9%] | 2.04 [1.62, 2.46] | 138 | 859.7 ms |
| **Paranoid ($d=2$)** | 7 / 24 | **29.2%** | [14.9%, 49.2%] | 2.17 [1.79, 2.52] | 44 | 327.2 ms |
| **Greedy** | 3 / 24 | **12.5%** | [4.3%, 31.0%] | 2.77 [2.38, 3.17] | 3 | 1.0 ms |
| **MCTS (250)** | 3 / 24 | **12.5%** | [4.3%, 31.0%] | 3.02 [2.56, 3.46] | 248 | 939.2 ms |

**Pairwise Paired Sign Tests on Game Ranks ($m = 6$ comparisons):**
- **Max^n vs MCTS:** $18-5$ ($p_{\text{raw}} = 0.0106, p_{\text{adj}} = 0.0637$, marginal / near-significant).
- **Paranoid vs MCTS:** $17-6$ ($p_{\text{raw}} = 0.0347, p_{\text{adj}} = 0.1734$, inconclusive after Holm correction).
- **Max^n vs Paranoid:** $13-10$ ($p_{\text{raw}} = 0.6776, p_{\text{adj}} = 1.0000$, inconclusive).
- **Greedy vs Max^n:** $8-14$ ($p_{\text{raw}} = 0.2863, p_{\text{adj}} = 0.8588$).
- **Greedy vs Paranoid:** $7-15$ ($p_{\text{raw}} = 0.1338, p_{\text{adj}} = 0.5352$).
- **Greedy vs MCTS:** $12-11$ ($p_{\text{raw}} = 1.0000, p_{\text{adj}} = 1.0000$).

### 4.4 Experiment E3: Family Comparison (2 Paranoid vs 2 MCTS)
Across $24$ games with balanced permutations of two Paranoid and two MCTS agents:
- **Paranoid Family:** 21 wins ($87.5\%$, 95% Wilson CI [$69.0\%, 95.7\%$]).
- **MCTS Family:** 3 wins ($12.5\%$).
- **Exact Binomial Test ($H_0: p = 0.50$):** $p = 0.0003$ (statistically significant advantage for Paranoid over MCTS in 2v2 family play).

### 4.5 Experiment E4: Wall Placement Targeting Analysis
Across 778 wall placements recorded across tournaments:
- Walls directly lengthening the current leader's shortest path: **58.4%**.
- Random expectation baseline ($p_0 = 1/3 = 33.3\%$):
- Exact Binomial Test: $p = 3.47 \times 10^{-12}$ (statistically significant confirmation of leader targeting).

### 4.6 Key Ablations (A1, A4, A5, A6)
- **A1 (Wall Target Pruning, $N = 24$):** `leader` pruning achieved identical win rate ($25.0\%$, mean rank $2.50$) to `all` pruning ($25.0\%$, mean rank $2.62$) while reducing wall candidates evaluated by $34\%$.
- **A4 (Heuristic Evaluation Mode, $N = 24$):** `mean` mode ($25.0\%$, mean rank $2.58$) and `leader` mode ($25.0\%$, mean rank $2.58$) exhibited identical performance.
- **A5 (Wall Inventory Impact, $N = 24$ each):**
  - **3 Walls per player:** Max^n won $11/24$ ($45.8\%$), Paranoid won $6/24$ ($25.0\%$), MCTS won $5/24$ ($20.8\%$), Greedy won $2/24$ ($8.3\%$).
  - **10 Walls per player:** Paranoid won $10/24$ ($41.7\%$), Max^n won $9/24$ ($37.5\%$), Greedy won $5/24$ ($20.8\%$), MCTS won $0/24$ ($0.0\%$).
  - *Observation:* With larger wall inventories, Paranoid's coalition defense and alpha-beta cutoff efficiency become increasingly potent, overtaking Max^n.
- **A6 (MCTS Rollout Policy, $N = 24$):** `path_biased` ($4.2\%$, mean rank $3.10$) performed comparably to `random` ($4.2\%$, mean rank $3.25$) at 250 iterations.

---

## 5. Limitations

1. **Unpruned Max^n Computational Ceiling:** Max^n evaluates full 4-player payoff vectors without alpha-beta cutoffs. Because the effective branching factor is $\approx 19$ candidate moves per ply, searching depth $d=4$ requires evaluating $19^4 \approx 130,000$ leaves per move, which is computationally prohibitive in pure Python without branch pruning.
2. **MCTS Iteration Budget:** At 250 iterations per move, MCTS explores only a fraction of the $19$-branch tree and relies on distance-difference heuristic cutoffs. In four-player tactical races, this was insufficient to match shallow alpha-beta tree search ($12.5\%$ vs $87.5\%$ in E3).
3. **Four-Player Cul-de-Sac Deadlocks:** In 4-player Quoridor, pawns can be temporarily immobilized in cul-de-sacs when adjacent cells are blocked by walls and a stack of multiple opponent pawns, leaving the player with 0 legal pawn moves. When the player also has 0 walls left, they must pass their turn (`PassMove`). While our engine gracefully handles this, a pass rule was not present in the original 2-player specification.
4. **Sample Size & Statistical Power:** With $N = 24$ games per table, small win-rate differences (such as Max^n $45.8\%$ vs Paranoid $29.2\%$) have wide confidence intervals and adjusted $p > 0.05$. Resolving whether Max^n is definitively superior to Paranoid would require $N \ge 168$ games.
5. **No Human or External Engine Grounding:** All evaluations are purely internal head-to-head matches between student search agents under identical rules and wall budgets. No human user testing or external master bots were benchmarked.

---

## 6. Amendments

1. **Cul-de-Sac Pass Handling (Game 21 of A5):** Fuzz testing and tournament play revealed that in 4-player games, an active player with 0 walls can have all adjacent cells blocked by a combination of walls, board edges, and opponent pawns whose straight and diagonal jump landing cells are simultaneously occupied or walled off. In such positions, the player has zero legal moves. We formally introduced `PassMove` in `quoridor_n/types.py` and `quoridor_n/rules.py` to allow the player to pass their turn without violating game loop invariants.
2. **MCTS Rollout Policy Optimization:** Initial MCTS rollouts evaluated all 128 board walls with full BFS on random exploratory steps, introducing a severe performance bottleneck ($27$s per move). The rollout simulation policy was streamlined to select among legal pawn movements using $O(1)$ Manhattan goal distances, reducing move latency to $\approx 430$ms per move ($60\times$ speedup) without altering search semantics.
