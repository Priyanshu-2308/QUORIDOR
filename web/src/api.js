// REST API client for dynamic-board game sessions, legal moves, path calculations, and AI decision queries.

const BASE_URL = '';

async function fetchJson(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    let errorDetail = `${resp.status} ${resp.statusText}`;
    try {
      const err = await resp.json();
      if (err.detail) errorDetail = err.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return await resp.json();
}

export async function createGame(options = {}) {
  let payload = {};
  if (typeof options === 'string') {
    payload = { opponent: options, human_player: 0 };
  } else {
    payload = {
      board_size: options.boardSize || 9,
      num_players: options.numPlayers || 2,
      human_player: options.humanPlayer !== undefined ? options.humanPlayer : 0,
    };
    if (options.opponents) {
      payload.opponents = options.opponents;
    } else if (options.opponent) {
      payload.opponent = options.opponent;
    }
  }
  return await fetchJson(`${BASE_URL}/api/new`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getState(gameId) {
  return await fetchJson(`${BASE_URL}/api/state/${gameId}`);
}

export async function getLegalMoves(gameId) {
  return await fetchJson(`${BASE_URL}/api/legal/${gameId}`);
}

export async function makeMove(gameId, move) {
  return await fetchJson(`${BASE_URL}/api/move/${gameId}`, {
    method: 'POST',
    body: JSON.stringify({ move }),
  });
}

export async function getAiMove(gameId) {
  return await fetchJson(`${BASE_URL}/api/ai/${gameId}`, {
    method: 'POST',
  });
}

export async function getPaths(gameId) {
  return await fetchJson(`${BASE_URL}/api/paths/${gameId}`);
}

export async function undoMove(gameId) {
  return await fetchJson(`${BASE_URL}/api/undo/${gameId}`, {
    method: 'POST',
  });
}
