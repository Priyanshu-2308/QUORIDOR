# Dynamic-Board Quoridor: Verified Slide Facts

This document compiles all experimental results, rule parameters, agent configurations, tests, and limitations for the dynamic-board ($N \in [7, 12]$, 2 or 4 players) Quoridor implementation. Every factual statement is backed by an existing file in the repository.

---

## 1. Verified Facts Table

| ID | Fact | Value | Source file |
|---|---|---|---|
| **R.1** | Selectable board dimension range | $N \in [7, 12]$ (7x7 to 12x12) | `quoridor_n/config.py` |
| **R.2** | Selectable player modes | 2 players or 4 players | `quoridor_n/config.py` |
| **R.3** | Initial wall inventory formula | $\lfloor 20 / K \rfloor$ (10 walls for 2P, 5 walls for 4P) | `quoridor_n/config.py` |
| **R.4** | Wall segment dimensions | Exactly 2 board units long, spanning 2 adjacent segments | `quoridor_n/rules.py` |
| **R.5** | Game turn limit formula | $T = 16 \cdot N$ plies (112 at $N=7$, 144 at $N=9$, 192 at $N=12$) | `quoridor_n/config.py` |
| **R.6** | Fair-start rule for even $N$ | Seats 0/1 start at $(N-1, \lfloor(N-1)/2\rfloor)$, Seats 2/3 at $(0, N-1-\lfloor(N-1)/2\rfloor)$ | `quoridor_n/state.py` |
| **R.7** | Goal side orientations | Seat 0: row 0; Seat 1: col $N-1$; Seat 2: row $N-1$; Seat 3: col 0 | `quoridor_n/rules.py` |
| **R.8** | Complete path blockage prohibition | Every pawn must retain at least one unblocked path to its goal side | `quoridor_n/rules.py` |
| **R.9** | Pawn jump mechanics | Straight jump if clear; diagonal jumps if behind-pawn square is blocked | `quoridor_n/rules.py` |
| **R.10** | Explicit pass rule | Player passes if and only if legal pawn moves = 0 and walls = 0 | `quoridor_n/rules.py` |
| **A.1** | Random agent selection | Uniform random choice among legal candidate moves | `quoridor_n/agents/random_agent.py` |
| **A.2** | Greedy baseline logic | 1-ply BFS minimizing shortest path to goal without placing walls | `quoridor_n/agents/greedy_agent.py` |
| **A.3** | Paranoid agent search depth | Depth 2 (or 3), assuming all $K-1$ opponents collude against root | `quoridor_n/agents/paranoid_agent.py` |
| **A.4** | Paranoid evaluation function | $d_{\text{leader}} - d_{\text{self}} + 0.1 \cdot (w_{\text{self}} - w_{\text{leader}})$ | `quoridor_n/agents/paranoid_agent.py` |
| **A.5** | Maxn agent search depth | Depth 2, computing $K$-tuple utility vectors without pruning | `quoridor_n/agents/maxn_agent.py` |
| **A.6** | MCTS matched compute iterations | 35 iterations, calibrated to match Paranoid(d=2) move latency | `quoridor_n/agents/mcts_agent.py` |
| **A.7** | MCTS rollout policy | 85% greedy shortest path step, 15% candidate move, cached BFS tables | `quoridor_n/agents/mcts_agent.py` |
| **A.8** | MCTS tree policy constant | UCB1 exploration constant $C = \sqrt{2} \approx 1.414$ | `quoridor_n/agents/mcts_agent.py` |
| **A.9** | Candidate wall pruning | Walls generated only adjacent to shortest paths of target opponents | `quoridor_n/moves.py` |
| **A.10** | Transposition table caching | Zobrist hashing storing search depth, bound, and optimal move | `quoridor_n/agents/paranoid_agent.py` |
| **T.1** | Total automated pytest test count | 199 tests (107 reference 2P tests + 92 dynamic board tests) | `tests/` |
| **T.2** | Pytest test execution time | ~4.5 seconds across all 199 tests | `tests/` |
| **T.3** | Web UI node test count | 9 unit tests passing in ~110ms | `tests/web/arrows.test.mjs` |
| **T.4** | 2-Player N=9 equivalence check | 100 random positions identical between `quoridor` and `quoridor_n` | `tests/n/test_equivalence.py` |
| **T.5** | Root evaluation equivalence | Paranoid root value equals 2P alpha-beta root value on matching states | `tests/n/test_equivalence.py` |
| **T.6** | Fuzzing robustness test | 12 size/mode combinations ($N \in [7, 12] \times \{2, 4\}$), 50 games each, 0 errors | `tests/n/test_fuzz.py` |
| **E0.1** | 4P Greedy Seat 0 win rate | 100.0% (4/4, 95% CI [51.0%, 100.0%], exact $p = 0.0039$, profile: quick) | `results_n/raw/e0_seat_bias_4p_greedy.json` |
| **E0.2** | 4P Paranoid Seat 0 win rate | 0.0% (0/4, 95% CI [0.0%, 49.0%], exact $p = 0.5781$, profile: quick) | `results_n/raw/e0_seat_bias_4p_paranoid.json` |
| **E0.3** | 2P Greedy Seat 2 win rate | 100.0% (2/2, 95% CI [34.2%, 100.0%], exact $p = 0.5000$, profile: quick) | `results_n/raw/e0_seat_bias_2p_greedy.json` |
| **E0.4** | 2P Paranoid Seat 2 win rate | 100.0% (2/2, 95% CI [34.2%, 100.0%], exact $p = 0.5000$, profile: quick) | `results_n/raw/e0_seat_bias_2p_paranoid.json` |
| **E1.1** | 4P Paranoid win rate vs 3x Greedy | 25.0% (1/4, 95% CI [4.6%, 69.9%], raw $p = 1.0000$, adj $p = 1.0000$, profile: quick) | `results_n/raw/e1_ladder_4p_paranoid.json` |
| **E1.2** | 4P Maxn win rate vs 3x Greedy | 25.0% (1/4, 95% CI [4.6%, 69.9%], raw $p = 1.0000$, adj $p = 1.0000$, profile: quick) | `results_n/raw/e1_ladder_4p_maxn.json` |
| **E1.3** | 4P MCTS win rate vs 3x Greedy | 0.0% (0/4, 95% CI [0.0%, 49.0%], raw $p = 0.5781$, adj $p = 1.0000$, profile: quick) | `results_n/raw/e1_ladder_4p_mcts.json` |
| **E1.4** | 2P Paranoid win rate vs Greedy | 100.0% (2/2, 95% CI [34.2%, 100.0%], raw $p = 0.5000$, adj $p = 1.0000$, profile: quick) | `results_n/raw/e1_ladder_2p_paranoid.json` |
| **E1.5** | 2P MCTS win rate vs Greedy | 100.0% (2/2, 95% CI [34.2%, 100.0%], raw $p = 0.5000$, adj $p = 1.0000$, profile: quick) | `results_n/raw/e1_ladder_2p_mcts.json` |
| **E2.1** | 4P Round Robin Greedy win rate | 8.3% (2/24, 95% CI [2.3%, 25.8%], $p = 0.0611$, mean rank 2.69, profile: quick) | `results_n/raw/e2_main_round_robin.json` |
| **E2.2** | 4P Round Robin Paranoid win rate | 37.5% (9/24, 95% CI [21.2%, 57.3%], $p = 0.1611$, mean rank 2.00, profile: quick) | `results_n/raw/e2_main_round_robin.json` |
| **E2.3** | 4P Round Robin Maxn win rate | 45.8% (11/24, 95% CI [27.9%, 64.9%], $p = 0.0304$, mean rank 2.02, profile: quick) | `results_n/raw/e2_main_round_robin.json` |
| **E2.4** | 4P Round Robin MCTS win rate | 8.3% (2/24, 95% CI [2.3%, 25.8%], $p = 0.0611$, mean rank 3.29, profile: quick) | `results_n/raw/e2_main_round_robin.json` |
| **E2.5** | Paired sign test: Paranoid vs MCTS | 20 vs 4 decisive games, raw $p = 0.0015$, Holm-adjusted $p = 0.0093$ (significant) | `results_n/raw/e2_main_round_robin.json` |
| **E2.6** | Paired sign test: Maxn vs MCTS | 18 vs 5 decisive games, raw $p = 0.0106$, Holm-adjusted $p = 0.0531$ | `results_n/raw/e2_main_round_robin.json` |
| **E2.7** | Paired sign test: Paranoid vs Maxn | 11 vs 13 decisive games, raw $p = 0.8388$, Holm-adjusted $p = 0.8388$ | `results_n/raw/e2_main_round_robin.json` |
| **E3.1** | 4P Family match (2 Paranoid vs 2 MCTS) | Paranoid family wins 91.7% (22/24, 95% CI [74.2%, 97.7%], $p < 0.0001$, profile: quick) | `results_n/raw/e3_family_comparison.json` |
| **E3b.1** | 2P Alpha-Beta vs MCTS head-to-head | Alpha-Beta wins 100.0% (4/4, 95% CI [51.0%, 100.0%], $p = 0.1250$, profile: quick) | `results_n/raw/e3b_two_player_match.json` |
| **E4.1** | Leader targeting wall placement share | 57.3% of walls lengthened leader's path (173/302, clustered bootstrap CI [50.0%, 64.3%]) | `results_n/raw/e4_targeting.json` |
| **E4.2** | Random candidate wall placebo baseline | 37.8% of random candidate walls hit leader (3189/8443) | `results_n/raw/e4_targeting.json` |
| **E4.3** | Leader targeting advantage over placebo | +19.5 percentage points above random legal placement | `results_n/raw/e4_targeting.json` |
| **E4.4** | Leader sole target share | 38.1% of walls lengthened exclusively the leader's path | `results_n/raw/e4_targeting.json` |
| **E5.1** | 4P Game plies scaling by board size | $N=7 \to 46.5$, $N=8 \to 55.8$, $N=9 \to 60.0$, $N=10 \to 75.0$, $N=11 \to 77.2$, $N=12 \to 87.0$ | `results_n/stats_n.txt` |
| **E5.2** | 2P Game plies scaling by board size | $N=7 \to 37.5$, $N=8 \to 48.5$, $N=9 \to 45.5$, $N=10 \to 74.5$, $N=11 \to 54.5$, $N=12 \to 68.5$ | `results_n/stats_n.txt` |
| **E5.3** | Seat 0 win rate scaling in 4P | $N=7 \to 29.2\%$ (7/24), $N=12 \to 20.8\%$ (5/24) | `results_n/stats_n.txt` |
| **AB1.1** | Wall target pruning win rate (A1) | `leader` achieves identical win rate to `all` (25.0% vs 25.0%, 6/24 each, rank 2.50 vs 2.62) | `results_n/raw/a1_wall_target_paired.json` |
| **AB2.1** | Search paradigm paired tournament (A2) | `paranoid` and `maxn` tie in paired tournament (25.0% vs 25.0%, 6/24 wins each, rank 2.58) | `results_n/raw/a2_paradigm_paired.json` |
| **AB3.1** | Move ordering node reduction (A3) | Move ordering reduces expanded nodes from 269.8 to 54.9 (4.91x reduction) | `results_n/raw/a3_position_benchmark.json` |
| **AB3.2** | Move ordering move agreement (A3) | Unordered search matches ordered search move on only 58.3% (35/60) of positions | `results_n/raw/a3_position_benchmark.json` |
| **AB3.3** | Wall candidate cap cost scaling (A3) | Baseline (`cap=12`) takes 401.1ms; uncapped (`cap=None`) takes 998.5ms (2.49x slower) | `results_n/raw/a3_position_benchmark.json` |
| **AB3.4** | Wall cap agreement rate (A3) | `cap=4` agrees on 88.3%; `cap=8` agrees on 96.7% of benchmark positions | `results_n/raw/a3_position_benchmark.json` |
| **AB4.1** | Evaluation function comparison (A4) | `eval_mode=leader` and `eval_mode=mean` tie (25.0% vs 25.0%, 6/24 wins each, rank 2.58) | `results_n/raw/a4_eval_mode_paired.json` |
| **AB5.1** | Wall inventory game length impact (A5) | 3 walls yields mean 45.9 plies; 10 walls yields mean 92.2 plies (2.01x game duration) | `results_n/raw/a5_walls_3.json`, `results_n/raw/a5_walls_10.json` |
| **AB5.2** | Wall inventory agent win rate shift (A5)| Paranoid win rate is 41.7% with 3 walls vs 29.2% with 10 walls | `results_n/ablation.csv` |
| **AB6.1** | MCTS rollout policy comparison (A6) | Both path-biased and random rollouts (35 iter) lost to Greedy (0/24 wins) | `results_n/raw/a6_mcts_rollout_paired.json` |
| **L.1** | Sample size resolution | Quick profile (24 games) resolves large effects ($\Delta > 30\%$), wide CIs for smaller shifts | `docs/DYNAMIC_BOARD.md` |
| **L.2** | Fixed heuristic weights | Hand-tuned weights (1.0 distance difference, 0.1 wall inventory) without reinforcement learning | `quoridor_n/agents/paranoid_agent.py` |
| **L.3** | Paranoid assumption pessimism | Assumes full 3-player coalition against root player; ignores kingmaking dynamics | `quoridor_n/agents/paranoid_agent.py` |
| **L.4** | Maxn depth constraints | Inability to prune alpha-beta bounds in Maxn restricts search depth to 2 in real-time | `quoridor_n/agents/maxn_agent.py` |
| **L.5** | MCTS rollout budget limits | 35 iterations matched Paranoid CPU time, but provides sparse tree coverage in 4P | `quoridor_n/agents/mcts_agent.py` |
| **L.6** | Baseline opponent simplicity | Greedy baseline follows shortest path without placing walls, serving as lower-bound baseline | `quoridor_n/tournament.py` |
| **L.7** | Execution environment | Single 8-core CPU workstation, pure Python without C extensions | `quoridor_n/tournament.py` |
| **S.1** | Interval estimation standard | Wilson score 95% confidence intervals used for all proportions | `quoridor_n/stats.py` |
| **S.2** | Hypothesis significance tests | Exact two-sided binomial tests against theoretical chance baselines | `quoridor_n/stats.py` |
| **S.3** | Multiple testing control | Step-down Holm-Bonferroni correction applied across hypothesis families | `quoridor_n/stats.py` |
| **S.4** | Cluster-robust inference | 1000-iteration clustered bootstrap over games for behavioral wall statistics | `quoridor_n/stats.py` |
| **C.1** | Workstation hardware | 8-core host CPU running Windows | `server/app.py` |
| **C.2** | Worker allocation | Multiprocessing with 6 concurrent worker processes (`cores - 2`) | `quoridor_n/tournament.py` |
| **C.3** | Experiment suite duration | E0-E5 battery: 835.43s (13.92m); Ablations A1-A6: 950.83s (15.85m) | `quoridor_n/experiments.py` |
| **C.4** | Mean move calculation latency | Greedy ~0.2ms, Paranoid(d=2) ~233ms, Maxn(d=2) ~585ms, MCTS(35) ~237ms | `results_n/summary.csv` |

---

## 2. Things the Data Does Not Show

1. **The data does NOT show that MCTS outperforms adversarial search in Quoridor at matched compute budgets.** In fact, under matched time per move (~0.24s), Paranoid search significantly defeated MCTS in paired round-robin games ($p = 0.0093$ adjusted) and swept the head-to-head family tournament (22/24 wins, $p < 0.0001$).
2. **The data does NOT show a significant performance difference between Paranoid and Maxn search at depth 2.** In paired tournament competition (A2), both agents achieved identical 25.0% win rates (6/24 wins) and identical mean ranks (2.58).
3. **The data does NOT show that evaluating all candidate walls provides a performance advantage over leader-targeted pruning.** In paired ablation A1, targeting only the current leader achieved the exact same 25.0% win rate as evaluating all candidate walls, while substantially reducing the branching factor.
4. **The data does NOT show that first-mover advantage increases with larger board sizes.** On $7 \times 7$ boards in 4-player mode, Seat 0 won 29.2% of games, whereas on $12 \times 12$ boards Seat 0 won 20.8% of games, showing that larger board space dilutes initial move order advantages.
5. **The data does NOT show human or superhuman play.** All evaluations were conducted against algorithmic baselines within controlled synthetic tournaments.
