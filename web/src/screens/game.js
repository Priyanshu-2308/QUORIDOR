// Game arena screen: dynamic board scaling for N in 7..12, 2 or 4 players, SVG rendering, touch/keyboard controls.

import { pickArrowMove } from '../arrows.js';

export function createGameScreen({
  onPawnMove,
  onWallMove,
  onUndo,
  onTogglePaths,
  onQuit,
}) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-background text-on-surface font-body-md text-body-md select-none';

  let gameState = null;
  let humanPlayer = 0;
  let opponentInfo = { name: 'Professor Prune', displayName: 'Professor Prune (Depth 3)', badge: '■' };
  let opponentInfos = [];
  let legalMoves = [];
  let shortestPaths = [];
  let showPaths = true;
  let wallOrientation = 'H'; // 'H' or 'V'
  let hoveredSlot = null;
  let touchStagedSlot = null;
  let pendingChoice = null;
  let isThinking = false;
  let isRequestInFlight = false;
  let moveHistory = [];
  let passNoticeTimer = null;
  let elapsedSeconds = 0;
  let timerInterval = null;

  const PLAYER_COLORS = {
    0: { fill: '#2E4BDB', text: '#FFFFFF', marker: '●', name: 'You (South)' },
    1: { fill: '#C05621', text: '#FFFFFF', marker: '▲', name: 'Dash (West)' },
    2: { fill: '#E5532D', text: '#FFFFFF', marker: '■', name: 'Prune (North)' },
    3: { fill: '#7C3AED', text: '#FFFFFF', marker: '◆', name: 'Pat (East)' },
  };

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    elapsedSeconds = 0;
    timerInterval = setInterval(() => {
      if (gameState && gameState.winner === null && !gameState.no_winner) {
        elapsedSeconds++;
        updateTimerDisplay();
      }
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function formatTime(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  function updateTimerDisplay() {
    const timerEl = el.querySelector('#match-timer');
    if (timerEl) {
      timerEl.textContent = formatTime(elapsedSeconds);
    }
  }

  function showPassNotice(text = 'No legal move, turn skipped.') {
    const noticeEl = el.querySelector('#pass-alert');
    const msgEl = el.querySelector('#pass-alert-msg');
    if (!noticeEl || !msgEl) return;
    if (passNoticeTimer) clearTimeout(passNoticeTimer);
    msgEl.textContent = text;
    noticeEl.classList.remove('hidden');
    passNoticeTimer = setTimeout(() => {
      noticeEl.classList.add('hidden');
    }, 3500);
  }

  function isMoveLegal(move) {
    if (!legalMoves || legalMoves.length === 0) return false;
    if (move.type === 'pawn') {
      return legalMoves.some(
        (m) => m.type === 'pawn' && m.to[0] === move.to[0] && m.to[1] === move.to[1]
      );
    }
    if (move.type === 'wall') {
      const oNorm = move.o.toUpperCase();
      return legalMoves.some(
        (m) => m.type === 'wall' && m.r === move.r && m.c === move.c && m.o.toUpperCase() === oNorm
      );
    }
    return false;
  }

  function toggleWallOrientation() {
    wallOrientation = wallOrientation === 'H' ? 'V' : 'H';
    updatePreview();
  }

  function updatePreview() {
    const previewEl = el.querySelector('#ghost-wall');
    if (!previewEl) return;

    if (
      !hoveredSlot ||
      isThinking ||
      isRequestInFlight ||
      !gameState ||
      gameState.current !== humanPlayer ||
      gameState.winner !== null ||
      gameState.no_winner
    ) {
      previewEl.setAttribute('opacity', '0');
      return;
    }

    const { r, c } = hoveredSlot;
    const isH = wallOrientation === 'H';
    const legal = isMoveLegal({ type: 'wall', r, c, o: wallOrientation });

    const pad = 12;
    const pitch = 44;
    const wallLen = 80;
    const wallThick = 8;

    let wx, wy, ww, wh;
    if (isH) {
      wx = pad + c * pitch;
      wy = pad + r * pitch + 36;
      ww = wallLen;
      wh = wallThick;
    } else {
      wx = pad + c * pitch + 36;
      wy = pad + r * pitch;
      ww = wallThick;
      wh = wallLen;
    }

    previewEl.setAttribute('x', wx);
    previewEl.setAttribute('y', wy);
    previewEl.setAttribute('width', ww);
    previewEl.setAttribute('height', wh);
    previewEl.setAttribute('fill', legal ? '#1C1B1B' : '#BA1A1A');
    previewEl.setAttribute('opacity', legal ? '0.45' : '0.8');
  }

  function clearPendingChoice() {
    if (pendingChoice) {
      if (pendingChoice.timer) clearTimeout(pendingChoice.timer);
      pendingChoice = null;
    }
    el.querySelectorAll('.legal-choice-dot').forEach((d) => d.remove());
  }

  function cancelChoice() {
    if (pendingChoice) {
      clearPendingChoice();
      return true;
    }
    return false;
  }

  function moveByArrow(dir) {
    if (
      !gameState ||
      isThinking ||
      isRequestInFlight ||
      gameState.current !== humanPlayer ||
      gameState.winner !== null ||
      gameState.no_winner
    ) {
      return;
    }

    const humanPawn = gameState.pawns[0];
    const legalPawnMoves = legalMoves.filter((m) => m.type === 'pawn').map((m) => m.to);

    if (pendingChoice) {
      const orig = pendingChoice.originalDir;
      const opts = pendingChoice.options;
      let chosen = null;

      if (orig === 'up' || orig === 'down') {
        if (dir === 'left') chosen = opts.reduce((a, b) => (a[1] < b[1] ? a : b));
        else if (dir === 'right') chosen = opts.reduce((a, b) => (a[1] > b[1] ? a : b));
      } else if (orig === 'left' || orig === 'right') {
        if (dir === 'up') chosen = opts.reduce((a, b) => (a[0] < b[0] ? a : b));
        else if (dir === 'down') chosen = opts.reduce((a, b) => (a[0] > b[0] ? a : b));
      }

      if (chosen) {
        clearPendingChoice();
        onPawnMove(chosen[0], chosen[1]);
        return;
      }
      clearPendingChoice();
      return;
    }

    const res = pickArrowMove(humanPawn, legalPawnMoves, dir);
    if (res.kind === 'move') {
      onPawnMove(res.to[0], res.to[1]);
    } else if (res.kind === 'choose') {
      pendingChoice = {
        originalDir: dir,
        options: res.options,
        timer: setTimeout(() => clearPendingChoice(), 3000),
      };
      renderBoard();
    }
  }

  function getPlayerName(seat) {
    if (seat === humanPlayer) return 'You';
    if (opponentInfos && opponentInfos.length > 0) {
      const match = opponentInfos.find((o) => o.seat === seat);
      if (match) return match.name;
    }
    if (opponentInfo && seat === 2) return opponentInfo.name;
    return PLAYER_COLORS[seat]?.name || `Player ${seat}`;
  }

  function renderBoard() {
    const boardContainer = el.querySelector('#board-svg-container');
    if (!boardContainer || !gameState) return;

    const N = gameState.config.board_size;
    const numP = gameState.config.num_players;
    const pad = 12;
    const pitch = 44;
    const gridDim = N * 44 - 8;
    const VB = gridDim + 2 * pad;

    let cellsHtml = '';
    let legalDotsHtml = '';
    let groovesHtml = '';
    let wallsHtml = '';
    let pathsHtml = '';
    let pawnsHtml = '';
    let rimsHtml = '';

    // Goal Rims
    // Seat 0 (South): goal row 0 (top rim)
    rimsHtml += `<line x1="${pad}" y1="${pad - 4}" x2="${pad + gridDim}" y2="${pad - 4}" stroke="#2E4BDB" stroke-width="3" stroke-linecap="round" opacity="0.8" />`;
    // Seat 2 (North): goal row N-1 (bottom rim)
    rimsHtml += `<line x1="${pad}" y1="${pad + gridDim + 4}" x2="${pad + gridDim}" y2="${pad + gridDim + 4}" stroke="#E5532D" stroke-width="3" stroke-linecap="round" opacity="0.8" />`;

    if (numP === 4) {
      // Seat 1 (West): goal col N-1 (right rim)
      rimsHtml += `<line x1="${pad + gridDim + 4}" y1="${pad}" x2="${pad + gridDim + 4}" y2="${pad + gridDim}" stroke="#C05621" stroke-width="3" stroke-linecap="round" opacity="0.8" />`;
      // Seat 3 (East): goal col 0 (left rim)
      rimsHtml += `<line x1="${pad - 4}" y1="${pad}" x2="${pad - 4}" y2="${pad + gridDim}" stroke="#7C3AED" stroke-width="3" stroke-linecap="round" opacity="0.8" />`;
    }

    // Cells
    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        const cx = pad + c * pitch;
        const cy = pad + r * pitch;
        cellsHtml += `<rect class="cell-bg" data-r="${r}" data-c="${c}" x="${cx}" y="${cy}" width="36" height="36" rx="4" fill="#FFFFFF" stroke="#E5E2DB" stroke-width="1" />`;
      }
    }

    // Legal pawn move dots
    if (!isThinking && gameState.current === humanPlayer && gameState.winner === null && !gameState.no_winner) {
      legalMoves
        .filter((m) => m.type === 'pawn')
        .forEach((m) => {
          const [r, c] = m.to;
          const cx = pad + c * pitch + 18;
          const cy = pad + r * pitch + 18;
          const isPending = pendingChoice && pendingChoice.options.some((o) => o[0] === r && o[1] === c);
          legalDotsHtml += `
            <circle class="legal-move-dot cursor-pointer" data-r="${r}" data-c="${c}" cx="${cx}" cy="${cy}" r="${isPending ? 8 : 6}" fill="${isPending ? '#E5532D' : '#2E4BDB'}" opacity="${isPending ? 0.9 : 0.6}" />
          `;
        });
    }

    // Wall Grooves (interactive hover zones)
    for (let r = 0; r < N - 1; r++) {
      for (let c = 0; c < N - 1; c++) {
        const gx = pad + c * pitch;
        const gy = pad + r * pitch;

        // Horizontal groove
        groovesHtml += `
          <rect class="wall-groove cursor-pointer" data-r="${r}" data-c="${c}" data-o="H" x="${gx}" y="${gy + 36}" width="80" height="8" fill="transparent" />
        `;
        // Vertical groove
        groovesHtml += `
          <rect class="wall-groove cursor-pointer" data-r="${r}" data-c="${c}" data-o="V" x="${gx + 36}" y="${gy}" width="8" height="80" fill="transparent" />
        `;
      }
    }

    // Placed Horizontal Walls
    if (gameState.h_walls) {
      gameState.h_walls.forEach(([r, c]) => {
        const wx = pad + c * pitch;
        const wy = pad + r * pitch + 36;
        wallsHtml += `<rect x="${wx}" y="${wy}" width="80" height="8" rx="3" fill="#1C1B1B" class="shadow-sm" />`;
      });
    }

    // Placed Vertical Walls
    if (gameState.v_walls) {
      gameState.v_walls.forEach(([r, c]) => {
        const wx = pad + c * pitch + 36;
        const wy = pad + r * pitch;
        wallsHtml += `<rect x="${wx}" y="${wy}" width="8" height="80" rx="3" fill="#1C1B1B" class="shadow-sm" />`;
      });
    }

    // Shortest Paths
    if (showPaths && shortestPaths && shortestPaths.length > 0) {
      const activeSeats = numP === 4 ? [0, 1, 2, 3] : [0, 2];
      activeSeats.forEach((seat, idx) => {
        const pList = shortestPaths[idx] || [];
        if (pList.length > 1) {
          const color = PLAYER_COLORS[seat]?.fill || '#888888';
          const points = pList.map(([r, c]) => `${pad + c * pitch + 18},${pad + r * pitch + 18}`).join(' L ');
          pathsHtml += `<path d="M ${points}" stroke="${color}" stroke-dasharray="4 4" stroke-width="2.5" fill="none" opacity="0.45" stroke-linecap="round" />`;
        }
      });
    }

    // Pawns
    const activeSeats = numP === 4 ? [0, 1, 2, 3] : [0, 2];
    activeSeats.forEach((seat, pawnIdx) => {
      const pawnPos = gameState.pawns[pawnIdx];
      if (!pawnPos) return;
      const [r, c] = pawnPos;
      const cx = pad + c * pitch + 18;
      const cy = pad + r * pitch + 18;
      const info = PLAYER_COLORS[seat];

      if (seat === 0) {
        // Seat 0: Blue circle
        pawnsHtml += `
          <g class="pawn-group cursor-pointer" data-seat="${seat}">
            <circle cx="${cx}" cy="${cy}" r="12" fill="${info.fill}" stroke="#FFFFFF" stroke-width="2" class="shadow-md" />
            <circle cx="${cx}" cy="${cy}" r="4" fill="#FFFFFF" />
          </g>
        `;
      } else if (seat === 1) {
        // Seat 1: Amber triangle
        pawnsHtml += `
          <g class="pawn-group" data-seat="${seat}">
            <polygon points="${cx},${cy - 12} ${cx - 11},${cy + 9} ${cx + 11},${cy + 9}" fill="${info.fill}" stroke="#FFFFFF" stroke-width="1.5" class="shadow-md" />
          </g>
        `;
      } else if (seat === 2) {
        // Seat 2: Vermilion square
        pawnsHtml += `
          <g class="pawn-group" data-seat="${seat}">
            <rect x="${cx - 10}" y="${cy - 10}" width="20" height="20" rx="3" fill="${info.fill}" stroke="#FFFFFF" stroke-width="1.5" class="shadow-md" />
          </g>
        `;
      } else if (seat === 3) {
        // Seat 3: Plum diamond
        pawnsHtml += `
          <g class="pawn-group" data-seat="${seat}">
            <polygon points="${cx},${cy - 12} ${cx + 11},${cy} ${cx},${cy + 12} ${cx - 11},${cy}" fill="${info.fill}" stroke="#FFFFFF" stroke-width="1.5" class="shadow-md" />
          </g>
        `;
      }
    });

    boardContainer.innerHTML = `
      <svg class="w-full h-full max-w-[560px] max-h-[560px] aspect-square" viewBox="0 0 ${VB} ${VB}">
        <g id="rims">${rimsHtml}</g>
        <g id="cells">${cellsHtml}</g>
        <g id="paths">${pathsHtml}</g>
        <g id="walls">${wallsHtml}</g>
        <rect id="ghost-wall" opacity="0" rx="3" pointer-events="none" />
        <g id="grooves">${groovesHtml}</g>
        <g id="legal-dots">${legalDotsHtml}</g>
        <g id="pawns">${pawnsHtml}</g>
      </svg>
    `;

    // Attach Groove and Dot Listeners
    boardContainer.querySelectorAll('.wall-groove').forEach((g) => {
      g.addEventListener('mouseenter', (e) => {
        const r = parseInt(e.currentTarget.getAttribute('data-r'), 10);
        const c = parseInt(e.currentTarget.getAttribute('data-c'), 10);
        const o = e.currentTarget.getAttribute('data-o');
        wallOrientation = o;
        hoveredSlot = { r, c };
        updatePreview();
      });

      g.addEventListener('mouseleave', () => {
        hoveredSlot = null;
        updatePreview();
      });

      g.addEventListener('click', (e) => {
        e.preventDefault();
        const r = parseInt(e.currentTarget.getAttribute('data-r'), 10);
        const c = parseInt(e.currentTarget.getAttribute('data-c'), 10);
        const o = wallOrientation;

        if (isMoveLegal({ type: 'wall', r, c, o })) {
          onWallMove(r, c, o);
        }
      });

      // Mobile Touch Handling: 1st tap previews, 2nd tap confirms
      g.addEventListener('touchstart', (e) => {
        const r = parseInt(e.currentTarget.getAttribute('data-r'), 10);
        const c = parseInt(e.currentTarget.getAttribute('data-c'), 10);
        const o = e.currentTarget.getAttribute('data-o');
        wallOrientation = o;
        hoveredSlot = { r, c };
        updatePreview();

        if (touchStagedSlot && touchStagedSlot.r === r && touchStagedSlot.c === c && touchStagedSlot.o === o) {
          if (isMoveLegal({ type: 'wall', r, c, o })) {
            touchStagedSlot = null;
            onWallMove(r, c, o);
          }
        } else {
          touchStagedSlot = { r, c, o };
        }
      });
    });

    boardContainer.querySelectorAll('.legal-move-dot').forEach((dot) => {
      dot.addEventListener('click', (e) => {
        const r = parseInt(e.currentTarget.getAttribute('data-r'), 10);
        const c = parseInt(e.currentTarget.getAttribute('data-c'), 10);
        clearPendingChoice();
        onPawnMove(r, c);
      });
    });

    boardContainer.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      toggleWallOrientation();
    });
  }

  function renderPlayerPanels() {
    const panelsContainer = el.querySelector('#player-panels');
    if (!panelsContainer || !gameState) return;

    const numP = gameState.config.num_players;
    const activeSeats = numP === 4 ? [0, 1, 2, 3] : [0, 2];

    panelsContainer.innerHTML = activeSeats
      .map((seat, idx) => {
        const isCurrent = gameState.current === seat && gameState.winner === null && !gameState.no_winner;
        const colorInfo = PLAYER_COLORS[seat];
        const name = getPlayerName(seat);
        const wallsLeft = gameState.walls_left ? gameState.walls_left[idx] : 0;

        return `
        <div class="flex items-center justify-between p-space-sm rounded ${
          isCurrent ? 'bg-surface-container border border-primary/40 shadow-sm' : 'bg-surface-container-lowest border border-transparent'
        }">
          <div class="flex items-center gap-space-xs">
            <span class="w-6 h-6 rounded flex items-center justify-center font-bold text-[12px]" style="background: ${colorInfo.fill}20; color: ${colorInfo.fill}">${colorInfo.marker}</span>
            <span class="font-body-md text-body-md ${isCurrent ? 'font-semibold text-primary' : 'text-on-surface'}">${name}</span>
          </div>
          <div class="flex items-center gap-space-xs font-label-sm text-label-sm">
            <span class="text-on-surface-variant">${wallsLeft} walls</span>
            ${isCurrent ? '<span class="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>' : ''}
          </div>
        </div>
      `;
      })
      .join('');
  }

  function render() {
    el.innerHTML = `
      <!-- Header / Toolbar -->
      <header class="w-full bg-background/90 backdrop-blur-md border-b border-outline-variant px-margin py-space-sm">
        <div class="max-w-[700px] mx-auto flex items-center justify-between">
          <div class="flex items-center gap-space-sm">
            <button id="btn-quit" type="button" class="p-1.5 rounded hover:bg-surface-container transition-colors text-on-surface-variant hover:text-primary cursor-pointer" title="Back to Setup">
              <span class="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
            <span class="font-label-lg text-label-lg tracking-wider text-primary font-semibold uppercase">QUORIDOR</span>
          </div>
          <div class="flex items-center gap-space-md font-label-md text-label-md text-on-surface-variant">
            <span id="match-timer">00:00</span>
            <span id="turn-badge" class="px-2 py-0.5 rounded bg-surface-container font-label-sm text-label-sm uppercase"></span>
          </div>
        </div>
      </header>

      <!-- Main Game View -->
      <main class="flex-1 w-full max-w-[700px] mx-auto p-margin flex flex-col items-center gap-space-md">
        
        <!-- Pass Alert Notice -->
        <div id="pass-alert" class="hidden w-full bg-surface-container-high border border-outline-variant px-space-md py-space-xs rounded text-center text-primary font-label-md text-label-md shadow-sm">
          <span id="pass-alert-msg">No legal move, turn skipped.</span>
        </div>

        <!-- Player Cards Row -->
        <div id="player-panels" class="w-full grid grid-cols-2 ${gameState?.config?.num_players === 4 ? 'sm:grid-cols-4' : ''} gap-space-xs"></div>

        <!-- Board Arena -->
        <div id="board-arena" class="w-full flex justify-center items-center py-space-xs">
          <div id="board-svg-container" class="w-full max-w-[560px] aspect-square flex items-center justify-center relative touch-manipulation"></div>
        </div>

        <!-- In-game Controls Toolbar -->
        <div class="w-full flex items-center justify-between border-t border-outline-variant/30 pt-space-sm">
          <div class="flex items-center gap-space-xs">
            <button id="btn-undo" type="button" class="px-3 py-1.5 rounded bg-surface-container-lowest hover:bg-surface-container border border-outline-variant/50 text-on-surface font-label-sm text-label-sm flex items-center gap-1 cursor-pointer transition-colors shadow-sm">
              <span class="material-symbols-outlined text-[16px]">undo</span>
              <span>Undo (U)</span>
            </button>
            <button id="btn-rotate" type="button" class="px-3 py-1.5 rounded bg-surface-container-lowest hover:bg-surface-container border border-outline-variant/50 text-on-surface font-label-sm text-label-sm flex items-center gap-1 cursor-pointer transition-colors shadow-sm">
              <span class="material-symbols-outlined text-[16px]">sync</span>
              <span id="rotate-label">Rotate (R: H)</span>
            </button>
            <button id="btn-paths" type="button" class="px-3 py-1.5 rounded ${showPaths ? 'bg-primary text-on-primary' : 'bg-surface-container-lowest text-on-surface'} border border-outline-variant/50 font-label-sm text-label-sm flex items-center gap-1 cursor-pointer transition-colors shadow-sm">
              <span class="material-symbols-outlined text-[16px]">alt_route</span>
              <span>Paths (P)</span>
            </button>
          </div>

          <div class="flex items-center gap-space-xs">
            <span id="thinking-indicator" class="hidden text-on-surface-variant font-label-sm text-label-sm italic flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
              <span>thinking...</span>
            </span>
          </div>
        </div>

      </main>
    `;

    el.querySelector('#btn-quit')?.addEventListener('click', () => {
      stopTimer();
      onQuit();
    });

    el.querySelector('#btn-undo')?.addEventListener('click', () => {
      onUndo();
    });

    el.querySelector('#btn-rotate')?.addEventListener('click', () => {
      toggleWallOrientation();
      const rLabel = el.querySelector('#rotate-label');
      if (rLabel) rLabel.textContent = `Rotate (R: ${wallOrientation})`;
    });

    el.querySelector('#btn-paths')?.addEventListener('click', () => {
      showPaths = !showPaths;
      const pBtn = el.querySelector('#btn-paths');
      if (pBtn) {
        if (showPaths) {
          pBtn.className = pBtn.className.replace('bg-surface-container-lowest text-on-surface', 'bg-primary text-on-primary');
        } else {
          pBtn.className = pBtn.className.replace('bg-primary text-on-primary', 'bg-surface-container-lowest text-on-surface');
        }
      }
      renderBoard();
      if (onTogglePaths) onTogglePaths();
    });

    renderPlayerPanels();
    renderBoard();
  }

  // Public Interface Methods
  el.initGame = function (state, human, oppInfo, oppList) {
    gameState = state;
    humanPlayer = human;
    if (oppInfo) opponentInfo = oppInfo;
    if (oppList) opponentInfos = oppList;
    moveHistory = [];
    shortestPaths = [];
    startTimer();
    render();
  };

  el.updateState = function (state, human, thinking, legal) {
    gameState = state;
    humanPlayer = human;
    isThinking = thinking;
    if (legal) legalMoves = legal;

    const thinkingEl = el.querySelector('#thinking-indicator');
    if (thinkingEl) {
      if (isThinking) thinkingEl.classList.remove('hidden');
      else thinkingEl.classList.add('hidden');
    }

    const turnBadge = el.querySelector('#turn-badge');
    if (turnBadge && gameState) {
      const isHuman = gameState.current === humanPlayer;
      turnBadge.textContent = isHuman ? 'Your turn' : `${getPlayerName(gameState.current)}'s turn`;
    }

    renderPlayerPanels();
    renderBoard();
  };

  el.setPaths = function (paths) {
    shortestPaths = paths || [];
    renderBoard();
  };

  el.showPassAlert = function (text) {
    showPassNotice(text);
  };

  el.toggleWallOrientation = toggleWallOrientation;
  el.togglePaths = function () {
    showPaths = !showPaths;
    renderBoard();
  };
  el.moveByArrow = moveByArrow;
  el.cancelChoice = cancelChoice;
  el.setRequestInFlight = function (v) {
    isRequestInFlight = v;
  };
  el.addHistoryMove = function (seat, move) {
    moveHistory.push({ seat, move });
  };
  el.getMoveHistory = function () {
    return moveHistory;
  };
  el.getElapsedSeconds = function () {
    return elapsedSeconds;
  };

  render();
  return el;
}
