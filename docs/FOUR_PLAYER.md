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
  4. Path existence is evaluated via Breadth-First Search (BFS) ignoring the physical presence of other pawns, matching the standard tournament rules.

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

*(To be populated in Phase 2 & Phase 3 as engine and agents are constructed).*

---

## 3. Experiment Plan

*(To be pre-registered and committed in Phase 5 before running experiments).*

---

## 4. Results

*(To be populated in Phase 6 & Phase 7).*

---

## 5. Limitations

*(To be documented in Phase 8).*

---

## 6. Amendments

*(To record any deviations or adjustments to the pre-registered plan with timestamps and rationales).*
