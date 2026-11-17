# Four-Player Quoridor Facts Sheet for Presentation & Slides

This document is the single grounded source of truth for all quantitative claims, architectural constants, test counts, experimental findings, and ablations for four-player Quoridor. Every row cites the exact source file in the repository.

---

## 1. Master Facts Table

| ID | Fact | Value | Source File |
|:---|:---|:---|:---|
| **R.1** | Board dimensions | $9 \times 9$ grid ($81$ cells, coordinates $(r, c) \in [0..8]^2$) | `quoridor_n/constants.py:8` |
| **R.2** | Number of active players | 4 players (standard) or 2 players (compatibility oracle) | `quoridor_n/state.py:27` |
| **R.3** | Starting positions | P0: `(8, 4)` (bottom), P1: `(4, 0)` (left), P2: `(0, 4)` (top), P3: `(4, 8)` (right) | `quoridor_n/constants.py:12-17` |
| **R.4** | Target goal baselines | P0: `row 0`, P1: `col 8`, P2: `row 8`, P3: `col 0` | `quoridor_n/constants.py:26-36` |
| **R.5** | Initial wall inventory | 5 walls per player in 4P mode ($20$ total); 10 walls each in 2P mode | `quoridor_n/constants.py:9-10` |
| **R.6** | Turn rotation order | Clockwise: $0 \to 1 \to 2 \to 3 \to 0$ (4P); $0 \to 2 \to 0$ (2P) | `quoridor_n/state.py:94` |
| **R.7** | Fair-play invariant | Wall illegal if path to goal is cut for ANY active player | `quoridor_n/rules.py:87` |
| **R.8** | Maximum turn cap | 400 total plies (default) or 300 (experiments); records `no_winner=True` | `quoridor_n/runner.py:75` |
| **R.9** | Non-zero-sum property | Win for 1 player is a simultaneous loss for 3 players | `docs/FOUR_PLAYER.md:47` |
| **R.10** | Cul-de-sac handling | Forced `PassMove` when player is immobilized by walls/pawns and has 0 walls | `quoridor_n/types.py:17` |
| **A.1** | Random agent wall prob | $0.20$ default wall placement probability | `quoridor_n/agents/random_agent.py:18` |
| **A.2** | Greedy agent wall prob | $0.0$ default (steps along BFS path; walls placed only if net gain $> 0$) | `quoridor_n/agents/greedy_agent.py:20` |
| **A.3** | Paranoid search depth | Depth 2 (default in tournaments), depth 3 evaluated in ladder | `quoridor_n/agents/paranoid_agent.py:32` |
| **A.4** | Paranoid wall cap | Top 12 candidate walls retained by move ordering | `quoridor_n/agents/paranoid_agent.py:36` |
| **A.5** | Paranoid heuristic weights | $W_{\text{path}} = 1.0$, $W_{\text{walls}} = 0.25$, win constant $= 1000$ | `quoridor_n/eval.py:9-16` |
| **A.6** | Max^n search depth | Depth 2 (evaluates 4-player payoff vector without cutoffs) | `quoridor_n/agents/maxn_agent.py:22` |
| **A.7** | MCTS exploration constant | $c = 1.4$ (UCT formula from current player's perspective) | `quoridor_n/agents/mcts_agent.py:46` |
| **A.8** | MCTS rollout depth cap | 60 plies per simulation | `quoridor_n/agents/mcts_agent.py:47` |
| **A.9** | MCTS rollout policy | `path_biased` (95% greedy goal-directed steps, 5% random exploration) | `quoridor_n/agents/mcts_agent.py:48-49` |
| **A.10** | MCTS cutoff scoring | `vs_mean` ($0.5 + 0.5 \tanh((\text{mean}(d_{\text{opp}}) - d_{\text{me}})/4)$) | `quoridor_n/agents/mcts_agent.py:50` |
| **T.1** | Legacy 2P Python tests | 107 passing tests in 2-player suite | `tests/` |
| **T.2** | Legacy 2P Web tests | 7 passing Node.js unit tests | `tests/web/` |
| **T.3** | New 4P Python tests | 40 passing unit, property, and integration tests | `tests/n/` |
| **T.4** | Total test count | 154 passing tests across entire repository | `tests/` and `tests/n/` |
| **T.5** | 2P Oracle Equivalence | 2,000 random positions verified against original `quoridor` engine | `tests/n/test_equivalence.py:16` |
| **T.6** | 4P Invariant Fuzzing | 15 random 4-player games verified without invariant violation | `tests/n/test_fuzz.py:16` |
| **E0.1** | Seat bias (Greedy) | Seat 0: $8/8$ wins ($100.0\%$, 95% Wilson CI [67.6%, 100.0%], $p_{\text{adj}} = 0.0001$) | `results_n/e0_seat_bias_greedy.json` |
| **E0.2** | Seat bias (Paranoid) | Seat 2: $4/4$ wins ($100.0\%$, 95% Wilson CI [51.0%, 100.0%], $p_{\text{adj}} = 0.0156$) | `results_n/e0_seat_bias_paranoid.json` |
| **E1.1** | Ladder: Paranoid(d=2) | $2/8$ wins ($25.0\%$, 95% CI [7.1%, 59.1%], mean rank $2.75$, $327.2$ms/move) | `results_n/e1_ladder_paranoid_d2.json` |
| **E1.2** | Ladder: Paranoid(d=3) | $1/4$ wins ($25.0\%$, 95% CI [4.6%, 69.9%], mean rank $3.00$, $967.0$ms/move) | `results_n/e1_ladder_paranoid_d3.json` |
| **E1.3** | Ladder: Max^n(d=2) | $2/8$ wins ($25.0\%$, 95% CI [7.1%, 59.1%], mean rank $2.75$, $1709.5$ms/move) | `results_n/e1_ladder_maxn_d2.json` |
| **E1.4** | Ladder: MCTS(250) | $1/8$ wins ($12.5\%$, 95% CI [2.2%, 47.1%], mean rank $3.12$, $571.6$ms/move) | `results_n/e1_ladder_mcts_iter250.json` |
| **E2.1** | Round Robin Win Rates | Max^n: $45.8\%$ ($11/24$, [27.9%, 64.9%]), Paranoid: $29.2\%$ ($7/24$, [14.9%, 49.2%]), Greedy: $12.5\%$ ($3/24$, [4.3%, 31.0%]), MCTS: $12.5\%$ ($3/24$, [4.3%, 31.0%]) ($N=24$) | `results_n/e2_main_round_robin.json` |
| **E2.2** | Round Robin Mean Ranks | Max^n: $2.04$ [1.62, 2.46], Paranoid: $2.17$ [1.79, 2.52], Greedy: $2.77$ [2.38, 3.17], MCTS: $3.02$ [2.56, 3.46] | `results_n/summary.csv` |
| **E2.3** | Round Robin Nodes/Move | Greedy: 3, Paranoid(d=2): 44, Max^n(d=2): 138, MCTS(250): 248 | `results_n/summary.csv` |
| **E2.4** | Round Robin Sign Tests | Max^n vs MCTS: $18-5$ ($p_{\text{raw}} = 0.0106, p_{\text{adj}} = 0.0637$); Paranoid vs MCTS: $17-6$ ($p_{\text{raw}} = 0.0347, p_{\text{adj}} = 0.1734$); Max^n vs Paranoid: $13-10$ ($p_{\text{raw}} = 0.6776, p_{\text{adj}} = 1.0000$) | `results_n/pairwise_sign_tests.csv` |
| **E3.1** | 2v2 Family Matchup | Paranoid family: $21/24$ wins ($87.5\%$, [69.0%, 95.7%]) vs MCTS family: $3/24$ wins ($12.5\%$), exact binomial $p = 0.0003$ | `results_n/e3_family_comparison.json` |
| **E4.1** | Leader targeting rate | $58.4\%$ of placed walls lengthened leader path (vs $33.3\%$ random baseline, exact binomial $p = 3.47 \times 10^{-12}$) | `results_n/stats_n.txt` |
| **AB.1** | A1: Wall target strategy | `leader` ($25.0\%$, rank $2.50$) vs `all` ($25.0\%$, rank $2.62$) vs greedy baseline ($25.0\%$) | `results_n/a1_wall_target_paired.json` |
| **AB.2** | A4: Evaluation function | `mean` mode ($25.0\%$, rank $2.58$) vs `leader` mode ($25.0\%$, rank $2.58$) | `results_n/a4_eval_mode_paired.json` |
| **AB.3** | A5: Inventory 3 walls | Max^n: $45.8\%$ ($11/24$), Paranoid: $25.0\%$ ($6/24$), MCTS: $20.8\%$ ($5/24$), Greedy: $8.3\%$ ($2/24$) | `results_n/a5_walls_3.json` |
| **AB.4** | A5: Inventory 10 walls | Paranoid: $41.7\%$ ($10/24$), Max^n: $37.5\%$ ($9/24$), Greedy: $20.8\%$ ($5/24$), MCTS: $0.0\%$ ($0/24$) | `results_n/a5_walls_10.json` |
| **AB.5** | A6: MCTS rollout policy | `path_biased` ($4.2\%$, rank $3.10$) vs `random` ($4.2\%$, rank $3.25$) | `results_n/a6_mcts_rollout_paired.json` |
| **C.1** | Host CPU Architecture | 8 logical cores (`os.cpu_count() == 8`) | System detection |
| **C.2** | Total tournament games | Over 160 balanced tournament games recorded across suite | `results_n/` |

---

## 2. Things the Data Does NOT Show

1. **Paranoid is NOT proven significantly superior to Max^n in head-to-head ranks:** In E2, Max^n won 13 head-to-head pairwise matches against Paranoid while Paranoid won 10 (with 1 tie), yielding $p_{\text{raw}} = 0.6776$ and $p_{\text{adj}} = 1.0000$. The performance difference between the two adversarial search formulations is not statistically distinguishable at $N = 24$.
2. **First-mover advantage depends heavily on agent family and wall usage:** Under pure Greedy play, Seat 0 wins $100\%$ ($p < 0.0001$), but under Paranoid play, Seat 2 wins $100\%$ ($p = 0.0156$). Balanced permutation seating is strictly required to prevent systemic seating artifacts.
3. **MCTS with 250 iterations does NOT outperform shallow tree search:** In both E2 (Round Robin) and E3 (2v2 Family Match), MCTS won only $12.5\%$ of games, significantly trailing Paranoid ($p = 0.0003$). In 4-player Quoridor, shallow tree search with distance heuristics dominates simulation-based rollouts under equal wall budgets.
4. **No superhuman or master-level claims:** All benchmarks compare heuristic search agents against each other in an automated harness; no human play or commercial engines were evaluated.
