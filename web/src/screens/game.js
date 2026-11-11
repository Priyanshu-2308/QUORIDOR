/**
 * Match Arena Screen - Quiet Bastion Design System.
 * Stitch Project 6777394393065907640 (Screen: Quoridor - Simplified Match).
 */

export function createGameScreen({
  onPawnMove,
  onWallMove,
  onUndo,
  onTogglePaths,
  onQuit,
}) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-surface text-on-surface';

  // Local Arena State
  let gameState = null;
  let humanPlayer = 0;
  let opponentInfo = { name: 'Professor Prune', displayName: 'Professor Prune (Depth 3)', badge: 'P' };
  let legalMoves = [];
  let shortestPaths = [[], []];
  let showPaths = true;
  let wallOrientation = 'H'; // 'H' or 'V'
  let hoveredSlot = null; // { r, c }
  let isThinking = false;
  let lastStats = null;
  let moveHistory = [];
  let toastMessage = null;
  let toastTimer = null;
  let elapsedSeconds = 0;
  let timerInterval = null;

  // Geometry constants: 9 cells (36px) + 8 gaps (8px) = 388px total
  const CELL_SIZE = 36;
  const GAP_SIZE = 8;
  const STEP = CELL_SIZE + GAP_SIZE; // 44px
  const BOARD_SIZE = 9 * CELL_SIZE + 8 * GAP_SIZE; // 388px

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    elapsedSeconds = 0;
    timerInterval = setInterval(() => {
      if (gameState && gameState.winner === null) {
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

  function showToast(msg) {
    toastMessage = msg;
    if (toastTimer) clearTimeout(toastTimer);
    const toastEl = el.querySelector('#illegal-toast');
    const toastMsgEl = el.querySelector('#illegal-toast-msg');
    if (toastEl && toastMsgEl) {
      toastMsgEl.textContent = msg;
      toastEl.classList.remove('hidden');
      toastTimer = setTimeout(() => {
        toastEl.classList.add('hidden');
        toastMessage = null;
      }, 3500);
    }
  }

  function isMoveLegal(move) {
    if (!legalMoves || legalMoves.length === 0) return false;
    if (move.type === 'pawn') {
      return legalMoves.some(m => m.type === 'pawn' && m.to[0] === move.to[0] && m.to[1] === move.to[1]);
    }
    if (move.type === 'wall') {
      const oNorm = move.o.toUpperCase();
      return legalMoves.some(m => m.type === 'wall' && m.r === move.r && m.c === move.c && m.o.toUpperCase() === oNorm);
    }
    return false;
  }

  function toAlgebraicCell(r, c) {
    const cols = 'abcdefghi';
    return `${cols[c]}${9 - r}`;
  }

  function toAlgebraicWall(r, c, o) {
    const cols = 'abcdefgh';
    const rank = 8 - r;
    return `W:${cols[c]}${rank}${o.toLowerCase()}`;
  }

  function toggleOrientation() {
    wallOrientation = (wallOrientation === 'H') ? 'V' : 'H';
    updatePreview();
  }

  function updatePreview() {
    const previewRect = el.querySelector('#staged-wall');
    const rotateBubble = el.querySelector('#rotate-bubble');
    const bubbleText = el.querySelector('#rotate-bubble-text');
    const statusText = el.querySelector('#turn-status-text');
    const turnIndicator = el.querySelector('#turn-indicator');

    if (!previewRect || !rotateBubble) return;

    if (!hoveredSlot || isThinking || (gameState && gameState.current !== humanPlayer) || (gameState && gameState.winner !== null)) {
      previewRect.setAttribute('opacity', '0');
      rotateBubble.classList.add('hidden');
      if (!isThinking && gameState && gameState.winner === null) {
        if (statusText) statusText.textContent = (gameState.current === humanPlayer) ? 'Your move' : `${opponentInfo.name} thinking...`;
        if (turnIndicator) turnIndicator.className = `w-2.5 h-2.5 rounded-full ${gameState.current === humanPlayer ? 'bg-secondary' : 'bg-on-tertiary-container animate-pulse'}`;
      }
      return;
    }

    const { r, c } = hoveredSlot;
    const isH = wallOrientation === 'H';
    const wallMove = { type: 'wall', r, c, o: wallOrientation };
    const legal = isMoveLegal(wallMove);

    // Wall coordinates in 388x388 SVG space
    let wx, wy, ww, wh;
    if (isH) {
      wx = c * STEP;
      wy = r * STEP + CELL_SIZE;
      ww = 2 * CELL_SIZE + GAP_SIZE; // 80px
      wh = GAP_SIZE; // 8px
    } else {
      wx = c * STEP + CELL_SIZE;
      wy = r * STEP;
      ww = GAP_SIZE; // 8px
      wh = 2 * CELL_SIZE + GAP_SIZE; // 80px
    }

    previewRect.setAttribute('x', wx);
    previewRect.setAttribute('y', wy);
    previewRect.setAttribute('width', ww);
    previewRect.setAttribute('height', wh);
    previewRect.setAttribute('fill', legal ? '#1C1B1B' : '#BA1A1A');
    previewRect.setAttribute('opacity', legal ? '0.45' : '0.75');

    // Tooltip position in percentage
    const boardEl = el.querySelector('#board-wrapper');
    if (boardEl) {
      const leftPct = ((wx + ww / 2) / BOARD_SIZE) * 100;
      const topPct = ((wy + wh / 2) / BOARD_SIZE) * 100;
      rotateBubble.style.left = `${leftPct}%`;
      rotateBubble.style.top = `${topPct}%`;
      rotateBubble.classList.remove('hidden');
      if (bubbleText) bubbleText.textContent = `R to rotate (${wallOrientation})`;
    }

    if (statusText) statusText.textContent = legal ? 'Placing wall' : 'Illegal attempt';
    if (turnIndicator) turnIndicator.className = `w-2.5 h-2.5 rounded-full ${legal ? 'bg-primary' : 'bg-error'}`;
  }

  function renderNotationLog() {
    const listEl = el.querySelector('#notation-list');
    if (!listEl) return;

    if (moveHistory.length === 0) {
      listEl.innerHTML = `<span class="text-outline text-label-sm">No moves recorded yet</span>`;
      return;
    }

    // Pair up moves by round
    const rows = [];
    for (let i = 0; i < moveHistory.length; i += 2) {
      const round = Math.floor(i / 2) + 1;
      const m1 = moveHistory[i];
      const m2 = moveHistory[i + 1] || '';
      rows.push(`
        <div class="flex items-center gap-space-sm py-0.5">
          <span class="w-6 text-outline font-label-sm">${round}.</span>
          <span class="w-20 font-label-sm font-medium ${m1.player === 0 ? 'text-secondary' : 'text-on-tertiary-container'}">${m1.notation}</span>
          ${m2 ? `<span class="w-20 font-label-sm font-medium ${m2.player === 0 ? 'text-secondary' : 'text-on-tertiary-container'}">${m2.notation}</span>` : ''}
        </div>
      `);
    }

    listEl.innerHTML = rows.join('');
    listEl.scrollTop = listEl.scrollHeight;
  }

  function render() {
    if (!gameState) {
      el.innerHTML = `
        <div class="flex-1 flex items-center justify-center min-h-screen">
          <div class="flex items-center gap-space-sm text-outline font-label-md">
            <span class="material-symbols-outlined animate-spin text-[20px]">sync</span>
            <span>INITIALIZING ARENA...</span>
          </div>
        </div>
      `;
      return;
    }

    const p0Pawn = gameState.pawns[0];
    const p1Pawn = gameState.pawns[1];
    const p0Walls = gameState.walls_left[0];
    const p1Walls = gameState.walls_left[1];
    const isHumanTurn = (gameState.current === humanPlayer) && (gameState.winner === null) && !isThinking;

    let statusText = 'Your move';
    let indicatorClass = 'bg-secondary';
    if (gameState.winner !== null) {
      statusText = (gameState.winner === humanPlayer) ? 'Victory' : 'Defeat';
      indicatorClass = (gameState.winner === humanPlayer) ? 'bg-secondary' : 'bg-on-tertiary-container';
    } else if (isThinking || gameState.current !== humanPlayer) {
      statusText = `${opponentInfo.name} thinking...`;
      indicatorClass = 'bg-on-tertiary-container animate-pulse';
    }

    // Distance in steps from shortest paths
    const p0Distance = (shortestPaths[0] && shortestPaths[0].length > 1) ? (shortestPaths[0].length - 1) : '-';
    const p1Distance = (shortestPaths[1] && shortestPaths[1].length > 1) ? (shortestPaths[1].length - 1) : '-';
    const humanDistance = (humanPlayer === 0) ? p0Distance : p1Distance;
    const oppDistance = (humanPlayer === 0) ? p1Distance : p0Distance;

    // SVG paths generation
    const makeSvgPath = (pts) => {
      if (!pts || pts.length < 2) return '';
      return pts.map((pt, i) => {
        const cx = pt[1] * STEP + CELL_SIZE / 2;
        const cy = pt[0] * STEP + CELL_SIZE / 2;
        return `${i === 0 ? 'M' : 'L'} ${cx} ${cy}`;
      }).join(' ');
    };
    const p0PathD = makeSvgPath(shortestPaths[0]);
    const p1PathD = makeSvgPath(shortestPaths[1]);

    // Committed walls in SVG (from gameState.h_walls and gameState.v_walls)
    const allCommittedWalls = [
      ...(gameState.h_walls || []).map(([r, c]) => [r, c, 'H']),
      ...(gameState.v_walls || []).map(([r, c]) => [r, c, 'V']),
    ];
    const placedWalls = allCommittedWalls.map(([r, c, o]) => {
      const isH = o.toUpperCase() === 'H';
      let wx, wy, ww, wh;
      if (isH) {
        wx = c * STEP;
        wy = r * STEP + CELL_SIZE;
        ww = 2 * CELL_SIZE + GAP_SIZE;
        wh = GAP_SIZE;
      } else {
        wx = c * STEP + CELL_SIZE;
        wy = r * STEP;
        ww = GAP_SIZE;
        wh = 2 * CELL_SIZE + GAP_SIZE;
      }
      return `<rect x="${wx}" y="${wy}" width="${ww}" height="${wh}" rx="3" fill="#1C1B1B" />`;
    }).join('');

    // Cells with legal dot highlights
    const cellsSvg = [];
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        const cx = c * STEP;
        const cy = r * STEP;
        const isGoalRow0 = (r === 0);
        const isGoalRow8 = (r === 8);
        const cellFill = isGoalRow0 ? 'rgba(46,75,219,0.10)' : (isGoalRow8 ? 'rgba(229,83,45,0.10)' : '#FFFFFF');
        const isLegalPawn = isHumanTurn && isMoveLegal({ type: 'pawn', to: [r, c] });

        cellsSvg.push(`
          <rect data-cell-r="${r}" data-cell-c="${c}" x="${cx}" y="${cy}" width="${CELL_SIZE}" height="${CELL_SIZE}" rx="3" fill="${cellFill}" stroke="#E5E2DB" stroke-width="1" class="board-cell cursor-pointer" />
          ${isLegalPawn ? `
            <g class="pointer-events-none legal-dot-pulse">
              <circle cx="${cx + CELL_SIZE / 2}" cy="${cy + CELL_SIZE / 2}" r="8" fill="rgba(46,75,219,0.2)" />
              <circle cx="${cx + CELL_SIZE / 2}" cy="${cy + CELL_SIZE / 2}" r="4" fill="#2E4BDB" />
            </g>
          ` : ''}
        `);
      }
    }

    // Pawn coordinates
    const p0Cx = p0Pawn[1] * STEP + CELL_SIZE / 2;
    const p0Cy = p0Pawn[0] * STEP + CELL_SIZE / 2;
    const p1Cx = p1Pawn[1] * STEP + CELL_SIZE / 2;
    const p1Cy = p1Pawn[0] * STEP + CELL_SIZE / 2;

    el.innerHTML = `
      <!-- Fixed Header Bar -->
      <header class="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-md pt-safe border-b border-surface-container-highest">
        <div class="h-14 max-w-[480px] mx-auto px-margin flex items-center justify-between">
          <div class="flex items-center gap-space-xs">
            <span class="font-label-lg text-label-lg uppercase tracking-wider text-on-surface font-semibold">QUORIDOR</span>
          </div>
          <div class="flex items-center gap-space-md">
            <span class="font-label-sm text-label-sm text-on-surface-variant font-medium tracking-wide">Move ${gameState.turn_count}</span>
            <div class="flex items-center gap-1 font-mono text-label-sm px-2 py-0.5 rounded bg-surface-container-high text-on-surface">
              <span class="material-symbols-outlined text-[13px] text-outline">timer</span>
              <span id="match-timer">${formatTime(elapsedSeconds)}</span>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Game Arena -->
      <main class="flex flex-col relative w-full pt-16 bg-surface min-h-screen pb-safe">
        <div class="w-full max-w-[440px] mx-auto px-margin py-space-xs flex flex-col gap-space-sm">
          
          <!-- Turn Indicator & Status -->
          <div class="w-full flex items-center justify-between py-space-xs">
            <div class="flex items-center gap-space-sm">
              <span class="w-2.5 h-2.5 rounded-full ${indicatorClass} transition-all" id="turn-indicator"></span>
              <span class="font-label-lg text-label-lg tracking-wider uppercase text-on-surface font-semibold" id="turn-status-text">${statusText}</span>
            </div>
            <div class="flex items-center gap-space-xs font-label-sm text-on-surface-variant">
              <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-secondary' : 'bg-on-tertiary-container'}"></span>
              <span>You: ${humanPlayer === 0 ? 'Cobalt' : 'Vermilion'}</span>
            </div>
          </div>

          <!-- Illegal Warning Toast -->
          <div class="hidden w-full bg-error-container text-on-error-container px-space-md py-space-xs rounded-lg flex items-center justify-between text-body-sm font-body-sm shadow-sm transition-all" id="illegal-toast">
            <div class="flex items-center gap-space-xs">
              <span class="material-symbols-outlined text-[18px]">error</span>
              <span id="illegal-toast-msg">Illegal wall placement!</span>
            </div>
            <button id="btn-close-toast" class="text-on-error-container hover:opacity-75 cursor-pointer">
              <span class="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>

          <!-- Quoridor 9x9 Arena Matrix Canvas -->
          <div id="board-wrapper" class="relative w-full aspect-square max-w-[420px] mx-auto select-none bg-surface-container-low rounded-xl p-2.5 shadow-sm border border-surface-container-highest">
            
            <!-- Goal Label: Top -->
            <div class="absolute top-1 left-0 right-0 flex justify-center items-center pointer-events-none z-20">
              <span class="font-label-sm text-[9px] uppercase tracking-widest ${humanPlayer === 0 ? 'text-secondary bg-secondary-fixed/50' : 'text-on-tertiary-container bg-tertiary-fixed/50'} px-2 py-0.5 rounded-full font-semibold shadow-xs">
                ${humanPlayer === 0 ? 'Your goal (Row 1)' : `${opponentInfo.name}'s goal (Row 1)`}
              </span>
            </div>

            <!-- Goal Label: Bottom -->
            <div class="absolute bottom-1 left-0 right-0 flex justify-center items-center pointer-events-none z-20">
              <span class="font-label-sm text-[9px] uppercase tracking-widest ${humanPlayer === 1 ? 'text-secondary bg-secondary-fixed/50' : 'text-on-tertiary-container bg-tertiary-fixed/50'} px-2 py-0.5 rounded-full font-semibold shadow-xs">
                ${humanPlayer === 1 ? 'Your goal (Row 9)' : `${opponentInfo.name}'s goal (Row 9)`}
              </span>
            </div>

            <!-- Interactive Wall Rotation Bubble Tooltip -->
            <div id="rotate-bubble" class="hidden absolute z-30 pointer-events-auto transform -translate-x-1/2 -translate-y-full mb-1 cursor-pointer">
              <div class="bg-primary text-on-primary px-2 py-0.5 rounded shadow-md flex items-center gap-1 font-label-sm text-[10px] uppercase tracking-wider hover:bg-neutral-800">
                <span id="rotate-bubble-text">R to rotate (${wallOrientation})</span>
                <span class="material-symbols-outlined text-[12px]">sync</span>
              </div>
            </div>

            <!-- Single High-Precision SVG Board Overlay (388x388) -->
            <svg id="board-svg" viewBox="0 0 ${BOARD_SIZE} ${BOARD_SIZE}" class="w-full h-full block">
              
              <!-- 81 Cells with Goal Row Washes -->
              <g id="cells-group">
                ${cellsSvg.join('')}
              </g>

              <!-- Shortest Paths (Dashed Trails) -->
              <g id="shortest-paths" class="transition-opacity duration-300 pointer-events-none" style="opacity: ${showPaths ? '0.85' : '0'};">
                ${p0PathD ? `<path d="${p0PathD}" fill="none" stroke="#2E4BDB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="4 4" />` : ''}
                ${p1PathD ? `<path d="${p1PathD}" fill="none" stroke="#E5532D" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="4 4" />` : ''}
              </g>

              <!-- Committed Solid Walls -->
              <g id="committed-walls" class="pointer-events-none">
                ${placedWalls}
              </g>

              <!-- Pawns: P0 (Cobalt) and P1 (Vermilion) -->
              <g id="pawns-group" class="pointer-events-none">
                <!-- P0 (Cobalt) Pawn -->
                <circle cx="${p0Cx}" cy="${p0Cy}" r="12" fill="#2E4BDB" filter="drop-shadow(0px 2px 3px rgba(0,0,0,0.25))" />
                <circle cx="${p0Cx}" cy="${p0Cy}" r="4" fill="#FFFFFF" opacity="0.6" />

                <!-- P1 (Vermilion) Pawn -->
                <circle cx="${p1Cx}" cy="${p1Cy}" r="12" fill="#E5532D" filter="drop-shadow(0px 2px 3px rgba(0,0,0,0.25))" />
                <circle cx="${p1Cx}" cy="${p1Cy}" r="4" fill="#FFFFFF" opacity="0.6" />
              </g>

              <!-- Staged Ghost Wall Preview -->
              <g id="wall-preview-group" class="pointer-events-none transition-opacity">
                <rect id="staged-wall" x="0" y="0" width="0" height="0" rx="3" fill="#1C1B1B" opacity="0" />
              </g>

              <!-- 64 Interactive Wall Groove Intersection Hit Areas (8x8) -->
              <g id="wall-slots-group">
                ${Array.from({ length: 8 }).flatMap((_, r) =>
                  Array.from({ length: 8 }).map((_, c) => {
                    const sx = c * STEP + CELL_SIZE - 2;
                    const sy = r * STEP + CELL_SIZE - 2;
                    return `
                      <rect data-slot-r="${r}" data-slot-c="${c}" x="${sx}" y="${sy}" width="${GAP_SIZE + 4}" height="${GAP_SIZE + 4}" fill="transparent" class="cursor-pointer wall-slot-intersection" />
                    `;
                  })
                ).join('')}
              </g>
            </svg>
          </div>

          <!-- Board Algebraic Axis Subtitle (a - i) -->
          <div class="w-full flex justify-between px-space-md pt-0.5 text-label-sm font-label-sm text-outline-variant max-w-[420px] mx-auto">
            <span>a</span><span>b</span><span>c</span><span>d</span><span>e</span><span>f</span><span>g</span><span>h</span><span>i</span>
          </div>

          <!-- Editorial Hairline Divided Panels -->
          <div class="w-full mt-space-xs flex flex-col max-w-[440px] mx-auto">
            
            <!-- Panel 1: Wall Inventory -->
            <div class="py-space-sm border-t border-surface-container-highest">
              <!-- You -->
              <div class="flex items-center justify-between py-1">
                <div class="flex items-center gap-space-sm w-24">
                  <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-secondary' : 'bg-on-tertiary-container'}"></span>
                  <span class="font-body-sm text-body-sm font-medium text-on-surface">You</span>
                </div>
                <div class="flex items-center gap-1">
                  ${Array.from({ length: 10 }).map((_, i) => `
                    <span class="w-3.5 h-1.5 rounded-full ${i < (humanPlayer === 0 ? p0Walls : p1Walls) ? 'bg-primary' : 'bg-surface-container-highest'}"></span>
                  `).join('')}
                </div>
                <span class="font-label-sm text-label-sm text-on-surface-variant w-12 text-right font-medium">
                  ${humanPlayer === 0 ? p0Walls : p1Walls} left
                </span>
              </div>
              <!-- Opponent -->
              <div class="flex items-center justify-between py-1">
                <div class="flex items-center gap-space-sm w-24">
                  <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-on-tertiary-container' : 'bg-secondary'}"></span>
                  <span class="font-body-sm text-body-sm font-medium text-on-surface truncate">${opponentInfo.name}</span>
                </div>
                <div class="flex items-center gap-1">
                  ${Array.from({ length: 10 }).map((_, i) => `
                    <span class="w-3.5 h-1.5 rounded-full ${i < (humanPlayer === 0 ? p1Walls : p0Walls) ? 'bg-primary' : 'bg-surface-container-highest'}"></span>
                  `).join('')}
                </div>
                <span class="font-label-sm text-label-sm text-on-surface-variant w-12 text-right font-medium">
                  ${humanPlayer === 0 ? p1Walls : p0Walls} left
                </span>
              </div>
            </div>

            <!-- Panel 2: Path Distance to Goal -->
            <div class="py-space-sm border-t border-surface-container-highest flex items-center justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Path Distance</span>
              <div class="flex items-center gap-space-md font-label-md text-label-md">
                <div class="flex items-center gap-space-xs">
                  <span class="text-on-surface-variant">You</span>
                  <span class="text-secondary font-semibold">${humanDistance} steps</span>
                </div>
                <span class="text-outline-variant">·</span>
                <div class="flex items-center gap-space-xs">
                  <span class="text-on-surface-variant">${opponentInfo.name}</span>
                  <span class="text-on-tertiary-container font-semibold">${oppDistance} steps</span>
                </div>
              </div>
            </div>

            <!-- Panel 3: Engine Telemetry -->
            <div class="py-space-sm border-t border-surface-container-highest flex items-center justify-between font-mono text-label-sm">
              <span class="uppercase tracking-wider text-on-surface-variant font-sans">Telemetry</span>
              <div class="flex items-center gap-space-sm text-outline">
                <span>nodes: <strong class="text-on-surface font-medium">${lastStats ? (lastStats.nodes || lastStats.iterations || 0) : '-'}</strong></span>
                <span>·</span>
                <span>time: <strong class="text-on-surface font-medium">${lastStats && lastStats.time_ms !== undefined ? lastStats.time_ms : '-'}ms</strong></span>
                <span>·</span>
                <span>eval: <strong class="text-on-surface font-medium">${lastStats && lastStats.eval !== undefined ? lastStats.eval : '-'}</strong></span>
              </div>
            </div>

            <!-- Panel 4: Notation Log (Collapsible or Scrollable) -->
            <div class="py-space-sm border-t border-surface-container-highest flex flex-col gap-space-xs">
              <div class="flex items-center justify-between">
                <span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Move Notation</span>
                <span class="font-label-sm text-label-sm text-outline">${moveHistory.length} plies</span>
              </div>
              <div id="notation-list" class="max-h-20 overflow-y-auto bg-surface-container-lowest p-space-xs rounded border border-surface-container-highest font-mono text-label-sm">
                <!-- Move entries populated here -->
              </div>
            </div>

            <!-- Panel 5: Interaction Controls Bar -->
            <div class="py-space-md border-t border-surface-container-highest flex items-center justify-between">
              <button id="btn-undo" class="px-space-md py-1.5 rounded bg-surface-container hover:bg-surface-variant text-on-surface font-body-sm text-body-sm transition-colors flex items-center gap-1 cursor-pointer">
                <span class="material-symbols-outlined text-[16px]">undo</span>
                <span>Undo (U)</span>
              </button>

              <!-- Toggle Show Paths -->
              <label class="flex items-center gap-space-xs cursor-pointer select-none">
                <input type="checkbox" id="path-toggle" ${showPaths ? 'checked' : ''} class="sr-only">
                <span class="font-body-sm text-body-sm text-on-surface-variant">Show paths</span>
                <span id="toggle-track" class="w-8 h-4 rounded-full relative transition-colors flex items-center px-0.5 ${showPaths ? 'bg-secondary' : 'bg-surface-variant'}">
                  <span id="toggle-knob" class="w-3 h-3 bg-surface rounded-full transition-transform transform ${showPaths ? 'translate-x-4' : 'translate-x-0'}"></span>
                </span>
              </label>

              <button id="btn-newgame" class="font-label-sm text-label-sm text-on-surface-variant hover:text-on-surface uppercase tracking-wider underline underline-offset-4 cursor-pointer">
                [New game]
              </button>
            </div>

            <!-- Panel 6: Shortcuts Guide -->
            <div class="pt-space-xs text-center">
              <p class="font-label-sm text-label-sm text-outline">R rotate wall · U undo · P paths · Esc menu</p>
            </div>
          </div>
        </div>
      </main>
    `;

    // Hook listeners
    renderNotationLog();

    el.querySelector('#btn-close-toast')?.addEventListener('click', () => {
      const toastEl = el.querySelector('#illegal-toast');
      if (toastEl) toastEl.classList.add('hidden');
    });

    el.querySelector('#rotate-bubble')?.addEventListener('click', () => {
      toggleOrientation();
    });

    // Cell Clicks (Pawn Moves)
    el.querySelectorAll('.board-cell').forEach((cell) => {
      cell.addEventListener('click', () => {
        if (!isHumanTurn) return;
        const r = parseInt(cell.getAttribute('data-cell-r'), 10);
        const c = parseInt(cell.getAttribute('data-cell-c'), 10);
        if (isMoveLegal({ type: 'pawn', to: [r, c] })) {
          onPawnMove(r, c);
        }
      });
    });

    // Wall Slot Hover & Clicks
    const boardSvg = el.querySelector('#board-svg');
    if (boardSvg) {
      boardSvg.addEventListener('mousemove', (e) => {
        if (!isHumanTurn) return;
        const rect = boardSvg.getBoundingClientRect();
        const svgX = ((e.clientX - rect.left) / rect.width) * BOARD_SIZE;
        const svgY = ((e.clientY - rect.top) / rect.height) * BOARD_SIZE;

        // Find closest intersection in 8x8 grid
        let closestR = -1;
        let closestC = -1;
        let minDistance = Infinity;

        for (let r = 0; r < 8; r++) {
          for (let c = 0; c < 8; c++) {
            const ix = c * STEP + CELL_SIZE + GAP_SIZE / 2;
            const iy = r * STEP + CELL_SIZE + GAP_SIZE / 2;
            const dist = Math.hypot(svgX - ix, svgY - iy);
            if (dist < minDistance) {
              minDistance = dist;
              closestR = r;
              closestC = c;
            }
          }
        }

        if (minDistance < 32 && closestR >= 0 && closestC >= 0) {
          if (!hoveredSlot || hoveredSlot.r !== closestR || hoveredSlot.c !== closestC) {
            hoveredSlot = { r: closestR, c: closestC };
            updatePreview();
          }
        } else {
          if (hoveredSlot !== null) {
            hoveredSlot = null;
            updatePreview();
          }
        }
      });

      boardSvg.addEventListener('mouseleave', () => {
        hoveredSlot = null;
        updatePreview();
      });

      boardSvg.addEventListener('click', (e) => {
        if (!isHumanTurn || !hoveredSlot) return;
        const { r, c } = hoveredSlot;
        const wallMove = { type: 'wall', r, c, o: wallOrientation };

        if (isMoveLegal(wallMove)) {
          onWallMove(r, c, wallOrientation);
        } else {
          showToast('Invalid wall: overlaps existing wall or blocks all paths to goal!');
          const staged = el.querySelector('#staged-wall');
          if (staged) {
            staged.setAttribute('fill', '#BA1A1A');
            staged.setAttribute('opacity', '0.9');
          }
        }
      });
    }

    // Toggle Paths
    const pathToggle = el.querySelector('#path-toggle');
    if (pathToggle) {
      pathToggle.addEventListener('change', (e) => {
        showPaths = e.target.checked;
        const pathsG = el.querySelector('#shortest-paths');
        const track = el.querySelector('#toggle-track');
        const knob = el.querySelector('#toggle-knob');
        if (pathsG) pathsG.style.opacity = showPaths ? '0.85' : '0';
        if (track) {
          track.className = `w-8 h-4 rounded-full relative transition-colors flex items-center px-0.5 ${showPaths ? 'bg-secondary' : 'bg-surface-variant'}`;
        }
        if (knob) {
          knob.className = `w-3 h-3 bg-surface rounded-full transition-transform transform ${showPaths ? 'translate-x-4' : 'translate-x-0'}`;
        }
        if (onTogglePaths) onTogglePaths(showPaths);
      });
    }

    // Undo
    el.querySelector('#btn-undo')?.addEventListener('click', () => {
      if (onUndo) onUndo();
    });

    // New Game / Quit
    el.querySelector('#btn-newgame')?.addEventListener('click', () => {
      if (onQuit) onQuit();
    });
  }

  // Public methods called by controller
  el.initGame = function (state, humanPl, oppInfo) {
    gameState = state;
    humanPlayer = humanPl;
    opponentInfo = oppInfo || opponentInfo;
    moveHistory = [];
    lastStats = null;
    hoveredSlot = null;
    isThinking = false;
    startTimer();
    render();
  };

  el.updateState = function (state, humanPl, thinking = false, legal = []) {
    gameState = state;
    humanPlayer = humanPl;
    isThinking = thinking;
    legalMoves = legal || [];
    render();
  };

  el.setPaths = function (paths) {
    shortestPaths = paths || [[], []];
    render();
  };

  el.setStats = function (stats) {
    lastStats = stats;
    render();
  };

  el.addHistoryMove = function (player, move) {
    let notation = '';
    if (move.type === 'pawn') {
      notation = toAlgebraicCell(move.to[0], move.to[1]);
    } else if (move.type === 'wall') {
      notation = toAlgebraicWall(move.r, move.c, move.o);
    }
    moveHistory.push({ player, move, notation });
    renderNotationLog();
  };

  el.toggleWallOrientation = function () {
    toggleOrientation();
  };

  el.togglePaths = function () {
    showPaths = !showPaths;
    const pt = el.querySelector('#path-toggle');
    if (pt) pt.checked = showPaths;
    const pathsG = el.querySelector('#shortest-paths');
    if (pathsG) pathsG.style.opacity = showPaths ? '0.85' : '0';
    return showPaths;
  };

  el.getElapsedSeconds = function () {
    return elapsedSeconds;
  };

  el.getMoveHistory = function () {
    return moveHistory;
  };

  render();
  return el;
}
