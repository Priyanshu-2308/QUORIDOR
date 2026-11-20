import test from 'node:test';
import assert from 'node:assert/strict';
import { pickArrowMove } from '../../web/src/arrows.js';

test('plain step in all four directions', () => {
  const pawn = [4, 4];
  const legalMoves = [[3, 4], [5, 4], [4, 3], [4, 5]];

  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), { kind: 'move', to: [3, 4] });
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'down'), { kind: 'move', to: [5, 4] });
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'left'), { kind: 'move', to: [4, 3] });
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'right'), { kind: 'move', to: [4, 5] });
});

test('pawn on each board edge has blocked direction as none', () => {
  // top edge: up is off-board
  assert.deepEqual(pickArrowMove([0, 4], [[1, 4], [0, 3], [0, 5]], 'up'), { kind: 'none' });
  // bottom edge: down is off-board
  assert.deepEqual(pickArrowMove([8, 4], [[7, 4], [8, 3], [8, 5]], 'down'), { kind: 'none' });
  // left edge: left is off-board
  assert.deepEqual(pickArrowMove([4, 0], [[3, 0], [5, 0], [4, 1]], 'left'), { kind: 'none' });
  // right edge: right is off-board
  assert.deepEqual(pickArrowMove([4, 8], [[3, 8], [5, 8], [4, 7]], 'right'), { kind: 'none' });
});

test('straight jump over opponent', () => {
  const pawn = [4, 4];
  // Opponent at [3, 4], straight jump landing is [2, 4]
  const legalMoves = [[2, 4], [5, 4], [4, 3], [4, 5]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), { kind: 'move', to: [2, 4] });

  // Opponent at [4, 5], straight jump landing is [4, 6]
  const legalMovesRight = [[4, 6], [3, 4], [5, 4], [4, 3]];
  assert.deepEqual(pickArrowMove(pawn, legalMovesRight, 'right'), { kind: 'move', to: [4, 6] });
});

test('jump blocked by a wall behind opponent giving two diagonals', () => {
  const pawn = [4, 4];
  // Opponent at [3, 4], wall behind at row 2, legal diagonals [3, 3] and [3, 5]
  const legalMoves = [[3, 3], [3, 5], [5, 4], [4, 3], [4, 5]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), {
    kind: 'choose',
    options: [[3, 3], [3, 5]],
  });

  // Opponent at [4, 3], wall behind at col 2, legal diagonals [3, 3] and [5, 3]
  const legalMovesLeft = [[3, 3], [5, 3], [3, 4], [5, 4], [4, 5]];
  assert.deepEqual(pickArrowMove(pawn, legalMovesLeft, 'left'), {
    kind: 'choose',
    options: [[3, 3], [5, 3]],
  });
});

test('one diagonal only when second diagonal is blocked', () => {
  const pawn = [4, 4];
  // Only [3, 5] is open, [3, 3] is blocked by a wall
  const legalMoves = [[3, 5], [5, 4], [4, 3], [4, 5]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), {
    kind: 'move',
    to: [3, 5],
  });
});

test('nothing legal in the requested direction gives none', () => {
  const pawn = [4, 4];
  // Wall blocks up, no jump, no diagonals
  const legalMoves = [[5, 4], [4, 3], [4, 5]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), { kind: 'none' });
});

test('legal sideways step is not mistaken for a diagonal', () => {
  const pawn = [4, 4];
  // Up is blocked, but [4, 3] and [4, 5] are legal sideways steps
  const legalMoves = [[4, 3], [4, 5], [5, 4]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), { kind: 'none' });
});

test('pawn on dynamic board edges (7x7 and 12x12)', () => {
  // 7x7 board bottom edge [6, 3]
  assert.deepEqual(pickArrowMove([6, 3], [[5, 3], [6, 2], [6, 4]], 'down'), { kind: 'none' });
  assert.deepEqual(pickArrowMove([6, 3], [[5, 3], [6, 2], [6, 4]], 'up'), { kind: 'move', to: [5, 3] });

  // 12x12 board top edge [0, 5]
  assert.deepEqual(pickArrowMove([0, 5], [[1, 5], [0, 4], [0, 6]], 'up'), { kind: 'none' });
  assert.deepEqual(pickArrowMove([0, 5], [[1, 5], [0, 4], [0, 6]], 'down'), { kind: 'move', to: [1, 5] });
  // 12x12 board right edge [5, 11]
  assert.deepEqual(pickArrowMove([5, 11], [[4, 11], [6, 11], [5, 10]], 'right'), { kind: 'none' });
});

test('diagonal jump when 3rd pawn blocks straight jump in 4-player', () => {
  // Human at [5, 5], P1 at [4, 5], P2 at [3, 5]
  // Straight jump to [3, 5] is blocked by P2, diagonals [4, 4] and [4, 6] are legal
  const pawn = [5, 5];
  const legalMoves = [[4, 4], [4, 6], [6, 5], [5, 4], [5, 6]];
  assert.deepEqual(pickArrowMove(pawn, legalMoves, 'up'), {
    kind: 'choose',
    options: [[4, 4], [4, 6]],
  });
});

