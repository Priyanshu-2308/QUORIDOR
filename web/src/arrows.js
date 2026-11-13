// pick move target for arrow keys
// pawn: [r, c]; pawnMoves: array of [r, c] legal destinations; dir: 'up' | 'down' | 'left' | 'right'
// returns { kind: 'move', to: [r, c] } | { kind: 'choose', options: [[r, c], [r, c]] } | { kind: 'none' }

const DIR_DELTAS = {
  up: [-1, 0],
  down: [1, 0],
  left: [0, -1],
  right: [0, 1],
};

export function pickArrowMove(pawn, pawnMoves, dir) {
  const delta = DIR_DELTAS[dir];
  if (!delta || !pawn || !Array.isArray(pawnMoves)) {
    return { kind: 'none' };
  }

  const [r, c] = pawn;
  const [dr, dc] = delta;

  const has = (tr, tc) => pawnMoves.some(([pr, pc]) => pr === tr && pc === tc);

  // 1. Plain step
  if (has(r + dr, c + dc)) {
    return { kind: 'move', to: [r + dr, c + dc] };
  }

  // 2. Straight jump over opponent
  if (has(r + 2 * dr, c + 2 * dc)) {
    return { kind: 'move', to: [r + 2 * dr, c + 2 * dc] };
  }

  // 3. Diagonal jump when straight jump is blocked
  const diagCandidates = [];
  if (dr !== 0) {
    // vertical motion: diagonals are left and right
    if (has(r + dr, c - 1)) diagCandidates.push([r + dr, c - 1]);
    if (has(r + dr, c + 1)) diagCandidates.push([r + dr, c + 1]);
  } else {
    // horizontal motion: diagonals are up and down
    if (has(r - 1, c + dc)) diagCandidates.push([r - 1, c + dc]);
    if (has(r + 1, c + dc)) diagCandidates.push([r + 1, c + dc]);
  }

  if (diagCandidates.length === 1) {
    return { kind: 'move', to: diagCandidates[0] };
  }
  if (diagCandidates.length === 2) {
    return { kind: 'choose', options: diagCandidates };
  }

  return { kind: 'none' };
}
