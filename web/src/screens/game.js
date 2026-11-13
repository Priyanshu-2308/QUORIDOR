// game arena screen
import { pickArrowMove } from '../arrows.js';

export function createGameScreen({
  onPawnMove,
  onWallMove,
  onUndo,
  onTogglePaths,
  onQuit,
}) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-surface text-on-surface font-body-md text-body-md';

  let gameState = null;
  let humanPlayer = 0;
  let opponentInfo = { name: 'Professor Prune', displayName: 'Professor Prune (Depth 3)', badge: 'P' };
  let legalMoves = [];
  let shortestPaths = [[], []];
  let showPaths = true;
  let wallOrientation = 'H';
  let manualOrientationLocked = false;
  let hoveredSlot = null;
  let pendingChoice = null;
  let isThinking = false;
  let isRequestInFlight = false;
  let lastStats = null;
  let moveHistory = [];
  let toastTimer = null;
  let elapsedSeconds = 0;
  let timerInterval = null;

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
    if (toastTimer) clearTimeout(toastTimer);
    const toastEl = el.querySelector('#illegal-toast');
    const toastMsgEl = el.querySelector('#illegal-toast-msg');
    if (toastEl && toastMsgEl) {
      toastMsgEl.textContent = msg;
      toastEl.classList.remove('hidden');
      toastTimer = setTimeout(() => {
        toastEl.classList.add('hidden');
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
    manualOrientationLocked = true;
    updatePreview();
  }

  function updatePreview() {
    const previewRect = el.querySelector('#staged-wall');
    const statusText = el.querySelector('#turn-status-text');
    const turnIndicator = el.querySelector('#turn-indicator');
    const boardArena = el.querySelector('#board-arena');

    if (!previewRect || !boardArena) return;

    if (!hoveredSlot || isThinking || (gameState && gameState.current !== humanPlayer) || (gameState && gameState.winner !== null)) {
      previewRect.setAttribute('opacity', '0');
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

    let wx, wy, ww, wh;
    if (isH) {
      wx = c * 40 + 3;
      wy = r * 40 + 37;
      ww = 74;
      wh = 6;
    } else {
      wx = c * 40 + 37;
      wy = r * 40 + 3;
      ww = 6;
      wh = 74;
    }

    previewRect.setAttribute('x', wx);
    previewRect.setAttribute('y', wy);
    previewRect.setAttribute('width', ww);
    previewRect.setAttribute('height', wh);
    previewRect.setAttribute('fill', legal ? '#1C1B1B' : '#BA1A1A');
    previewRect.setAttribute('opacity', legal ? '0.4' : '0.8');

    if (statusText) {
      statusText.textContent = legal
        ? `Placing wall (${isH ? 'horizontal' : 'vertical'})`
        : 'Illegal attempt';
    }
    if (turnIndicator) turnIndicator.className = `w-2.5 h-2.5 rounded-full ${legal ? 'bg-primary' : 'bg-error'}`;
  }

  function clearPendingChoice() {
    if (pendingChoice) {
      if (pendingChoice.timer) clearTimeout(pendingChoice.timer);
      pendingChoice = null;
    }
    el.querySelectorAll('.legal-dot-choice').forEach((dot) => {
      dot.classList.remove('legal-dot-choice', 'legal-dot-pulse');
    });
    const statusText = el.querySelector('#turn-status-text');
    if (statusText && !isThinking && gameState && gameState.winner === null) {
      statusText.textContent = (gameState.current === humanPlayer) ? 'Your move' : `${opponentInfo.name} thinking...`;
    }
  }

  function cancelChoice() {
    if (pendingChoice) {
      clearPendingChoice();
      return true;
    }
    return false;
  }

  function moveByArrow(dir) {
    if (!gameState || isThinking || isRequestInFlight || gameState.current !== humanPlayer || gameState.winner !== null) {
      return;
    }

    const humanPawn = (humanPlayer === 0) ? gameState.pawns[0] : gameState.pawns[1];
    const legalPawnMoves = legalMoves.filter((m) => m.type === 'pawn').map((m) => m.to);

    if (pendingChoice) {
      const orig = pendingChoice.originalDir;
      const opts = pendingChoice.options;
      let chosen = null;

      if (orig === 'up' || orig === 'down') {
        if (dir === 'left') {
          chosen = opts.reduce((a, b) => (a[1] < b[1] ? a : b));
        } else if (dir === 'right') {
          chosen = opts.reduce((a, b) => (a[1] > b[1] ? a : b));
        }
      } else if (orig === 'left' || orig === 'right') {
        if (dir === 'up') {
          chosen = opts.reduce((a, b) => (a[0] < b[0] ? a : b));
        } else if (dir === 'down') {
          chosen = opts.reduce((a, b) => (a[0] > b[0] ? a : b));
        }
      }

      if (chosen) {
        isRequestInFlight = true;
        clearPendingChoice();
        onPawnMove(chosen[0], chosen[1]);
        return;
      }
      clearPendingChoice();
      return;
    }

    const res = pickArrowMove(humanPawn, legalPawnMoves, dir);

    if (res.kind === 'move') {
      isRequestInFlight = true;
      onPawnMove(res.to[0], res.to[1]);
    } else if (res.kind === 'choose') {
      res.options.forEach(([r, c]) => {
        const dot = el.querySelector(`.cell-square[data-cell-r="${r}"][data-cell-c="${c}"] .legal-dot`);
        if (dot) {
          dot.classList.add('legal-dot-choice', 'legal-dot-pulse');
        }
      });
      const statusText = el.querySelector('#turn-status-text');
      if (statusText) statusText.textContent = 'Pick a side';

      const timer = setTimeout(() => {
        clearPendingChoice();
      }, 3000);

      pendingChoice = { originalDir: dir, options: res.options, timer };
    } else if (res.kind === 'none') {
      const pawnEl = el.querySelector(`.cell-square[data-cell-r="${humanPawn[0]}"][data-cell-c="${humanPawn[1]}"] .pawn-marker`);
      if (pawnEl) {
        pawnEl.classList.remove('pawn-shake');
        void pawnEl.offsetWidth;
        pawnEl.classList.add('pawn-shake');
        setTimeout(() => {
          pawnEl.classList.remove('pawn-shake');
        }, 150);
      }
    }
  }

  function renderNotationLog() {
    const listEl = el.querySelector('#notation-list');
    if (!listEl) return;

    if (moveHistory.length === 0) {
      listEl.innerHTML = `<span class="text-outline text-label-sm">No moves recorded yet</span>`;
      return;
    }

    const rows = [];
    for (let i = 0; i < moveHistory.length; i += 2) {
      const round = Math.floor(i / 2) + 1;
      const m1 = moveHistory[i];
      const m2 = moveHistory[i + 1] || null;
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

    const p0Distance = (shortestPaths[0] && shortestPaths[0].length > 1) ? (shortestPaths[0].length - 1) : '-';
    const p1Distance = (shortestPaths[1] && shortestPaths[1].length > 1) ? (shortestPaths[1].length - 1) : '-';
    const humanDistance = (humanPlayer === 0) ? p0Distance : p1Distance;
    const oppDistance = (humanPlayer === 0) ? p1Distance : p0Distance;

    const makeSvgPath = (pts) => {
      if (!pts || pts.length < 2) return '';
      return pts.map((pt, i) => {
        const cx = pt[1] * 40 + 20;
        const cy = pt[0] * 40 + 20;
        return `${i === 0 ? 'M' : 'L'} ${cx} ${cy}`;
      }).join(' ');
    };
    const p0PathD = makeSvgPath(shortestPaths[0]);
    const p1PathD = makeSvgPath(shortestPaths[1]);

    const allCommittedWalls = [
      ...(gameState.h_walls || []).map(([r, c]) => [r, c, 'H']),
      ...(gameState.v_walls || []).map(([r, c]) => [r, c, 'V']),
    ];
    const placedWallsSvg = allCommittedWalls.map(([r, c, o]) => {
      const isH = o.toUpperCase() === 'H';
      let wx, wy, ww, wh;
      if (isH) {
        wx = c * 40 + 3;
        wy = r * 40 + 37;
        ww = 74;
        wh = 6;
      } else {
        wx = c * 40 + 37;
        wy = r * 40 + 3;
        ww = 6;
        wh = 74;
      }
      return `<rect fill="#1C1B1B" height="${wh}" rx="3" width="${ww}" x="${wx}" y="${wy}"></rect>`;
    }).join('');

    const cellsHtml = [];
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        const isGoalRow0 = (r === 0);
        const isGoalRow8 = (r === 8);
        const isP0 = (p0Pawn[0] === r && p0Pawn[1] === c);
        const isP1 = (p1Pawn[0] === r && p1Pawn[1] === c);
        const isLegalPawn = isHumanTurn && isMoveLegal({ type: 'pawn', to: [r, c] });

        let bgClass = 'bg-surface-container-lowest';
        if (isGoalRow0) bgClass = 'bg-secondary/10';
        else if (isGoalRow8) bgClass = 'bg-on-tertiary-container/10';

        let innerContent = '';
        if (isP0) {
          innerContent = `
            <div class="pawn-marker w-[62%] aspect-square rounded-full bg-secondary shadow-sm flex items-center justify-center">
              <span class="w-1.5 h-1.5 rounded-full bg-surface-container-lowest opacity-75"></span>
            </div>
          `;
        } else if (isP1) {
          innerContent = `
            <div class="pawn-marker w-[62%] aspect-square rounded-full bg-on-tertiary-container shadow-sm flex items-center justify-center">
              <span class="w-1.5 h-1.5 rounded-full bg-surface-container-lowest opacity-60"></span>
            </div>
          `;
        } else if (isLegalPawn) {
          innerContent = `
            <div class="w-3 h-3 rounded-full bg-secondary/20 flex items-center justify-center legal-dot cursor-pointer">
              <div class="w-1.5 h-1.5 rounded-full bg-secondary"></div>
            </div>
          `;
        }

        cellsHtml.push(`
          <div data-cell-r="${r}" data-cell-c="${c}" class="cell-square ${bgClass} rounded-sm flex items-center justify-center relative cursor-pointer hover:bg-surface-container transition-colors">
            ${innerContent}
          </div>
        `);
      }
    }

    el.innerHTML = `
      <header class="fixed top-0 w-full z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div class="h-14 px-margin flex items-center justify-between max-w-[440px] mx-auto">
          <div class="flex items-center">
            <span class="font-label-lg text-label-lg uppercase tracking-wider text-on-surface font-semibold">Quoridor</span>
          </div>
          <div class="flex items-center gap-space-sm">
            <span class="font-label-sm text-label-sm text-on-surface-variant font-medium tracking-wide">Move ${Math.floor(gameState.turn_count / 2) + 1}</span>
            <div class="flex items-center gap-1 font-mono text-label-sm px-2 py-0.5 rounded bg-surface-container-high text-on-surface">
              <span class="material-symbols-outlined text-[13px] text-outline">timer</span>
              <span id="match-timer">${formatTime(elapsedSeconds)}</span>
            </div>
          </div>
        </div>
      </header>

      <main class="flex flex-col relative w-full pt-14 bg-surface min-h-screen">
        <div class="flex flex-col w-full px-margin pb-space-xl max-w-[440px] mx-auto">
          
          <div class="w-full flex items-center justify-between py-space-xs mb-space-sm">
            <div class="flex items-center gap-space-sm">
              <span class="w-2.5 h-2.5 rounded-full ${indicatorClass} transition-all" id="turn-indicator"></span>
              <span class="font-label-lg text-label-lg tracking-wider uppercase text-on-surface font-semibold" id="turn-status-text">${statusText}</span>
            </div>
            <div class="flex items-center gap-space-xs font-label-sm text-on-surface-variant">
              <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-secondary' : 'bg-on-tertiary-container'}"></span>
              <span>You: ${humanPlayer === 0 ? 'Cobalt' : 'Vermilion'}</span>
            </div>
          </div>

          <div class="hidden w-full mb-space-sm bg-error-container text-on-error-container px-space-md py-space-xs rounded flex items-center justify-between text-body-sm font-body-sm shadow-sm" id="illegal-toast">
            <div class="flex items-center gap-space-sm">
              <span class="material-symbols-outlined text-[18px]">error</span>
              <span id="illegal-toast-msg">Illegal attempt</span>
            </div>
            <button id="btn-close-toast" class="text-on-error-container hover:opacity-75 cursor-pointer" type="button">
              <span class="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>

          <div id="board-arena" class="relative w-full aspect-square max-w-[420px] mx-auto select-none bg-surface-container-low rounded-lg p-2.5 shadow-sm">
            
            <div class="absolute top-1 left-0 right-0 flex justify-center items-center pointer-events-none z-20">
              <span class="font-label-sm text-[9px] uppercase tracking-widest ${humanPlayer === 0 ? 'text-secondary' : 'text-on-tertiary-container'} font-semibold bg-surface-container-low px-1.5 py-0.2 rounded-full">
                ${humanPlayer === 0 ? 'Your goal (Row 1)' : `${opponentInfo.name}'s goal (Row 1)`}
              </span>
            </div>

            <div class="absolute bottom-1 left-0 right-0 flex justify-center items-center pointer-events-none z-20">
              <span class="font-label-sm text-[9px] uppercase tracking-widest ${humanPlayer === 1 ? 'text-secondary' : 'text-on-tertiary-container'} font-semibold bg-surface-container-low px-1.5 py-0.2 rounded-full">
                ${humanPlayer === 1 ? 'Your goal (Row 9)' : `${opponentInfo.name}'s goal (Row 9)`}
              </span>
            </div>

            <svg class="absolute inset-2.5 w-[calc(100%-20px)] h-[calc(100%-20px)] pointer-events-none z-10" id="board-svg" viewbox="0 0 360 360">
              <g class="transition-opacity duration-300" id="shortest-paths" style="opacity: ${showPaths ? '0.85' : '0'};">
                ${p0PathD ? `<path d="${p0PathD}" fill="none" opacity="0.85" stroke="#2E4BDB" stroke-dasharray="3 3" stroke-linecap="round" stroke-width="2"></path>` : ''}
                ${p1PathD ? `<path d="${p1PathD}" fill="none" opacity="0.85" stroke="#E5532D" stroke-dasharray="3 3" stroke-linecap="round" stroke-width="2"></path>` : ''}
              </g>

              <g id="placed-walls-group">
                ${placedWallsSvg}
              </g>

              <g class="transition-opacity" id="wall-preview-group">
                <rect fill="#1C1B1B" height="6" id="staged-wall" opacity="0" rx="3" width="74" x="0" y="0"></rect>
              </g>
            </svg>

            <div class="grid grid-cols-9 grid-rows-9 gap-1.5 w-full h-full" id="grid-cells">
              ${cellsHtml.join('')}
            </div>

          </div>

          <div class="w-full flex justify-between px-space-md pt-1 text-label-sm font-label-sm text-outline-variant max-w-[420px] mx-auto">
            <span>a</span><span>b</span><span>c</span><span>d</span><span>e</span><span>f</span><span>g</span><span>h</span><span>i</span>
          </div>

          <div id="side-panel" class="w-full mt-space-md flex flex-col">
            
            <div class="py-space-sm border-t border-surface-container-highest">
              <div class="flex items-center justify-between py-1">
                <div class="flex items-center gap-space-sm w-24">
                  <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-secondary' : 'bg-on-tertiary-container'}"></span>
                  <span class="font-body-sm text-body-sm font-medium text-on-surface">You</span>
                </div>
                <div class="flex items-center gap-1">
                  ${Array.from({ length: 10 }).map((_, i) => `
                    <span class="w-4 h-1.5 rounded-full ${i < (humanPlayer === 0 ? p0Walls : p1Walls) ? 'bg-primary' : 'bg-surface-container-highest'}"></span>
                  `).join('')}
                </div>
                <span class="font-label-sm text-label-sm text-on-surface-variant w-12 text-right font-medium">
                  ${humanPlayer === 0 ? p0Walls : p1Walls} left
                </span>
              </div>
              <div class="flex items-center justify-between py-1">
                <div class="flex items-center gap-space-sm w-24">
                  <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-on-tertiary-container' : 'bg-secondary'}"></span>
                  <span class="font-body-sm text-body-sm font-medium text-on-surface truncate">${opponentInfo.name}</span>
                </div>
                <div class="flex items-center gap-1">
                  ${Array.from({ length: 10 }).map((_, i) => `
                    <span class="w-4 h-1.5 rounded-full ${i < (humanPlayer === 0 ? p1Walls : p0Walls) ? 'bg-primary' : 'bg-surface-container-highest'}"></span>
                  `).join('')}
                </div>
                <span class="font-label-sm text-label-sm text-on-surface-variant w-12 text-right font-medium">
                  ${humanPlayer === 0 ? p1Walls : p0Walls} left
                </span>
              </div>
            </div>

            <div class="py-space-sm border-t border-surface-container-highest flex items-center justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Path Distance</span>
              <div class="flex items-center gap-space-lg font-label-md text-label-md">
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

            <div class="py-space-sm border-t border-surface-container-highest flex flex-col gap-space-xs">
              <div class="flex items-center justify-between">
                <span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Move Notation</span>
                <span class="font-label-sm text-label-sm text-outline">${moveHistory.length} plies</span>
              </div>
              <div id="notation-list" class="max-h-20 overflow-y-auto bg-surface-container-lowest p-space-xs rounded border border-surface-container-highest font-mono text-label-sm">
              </div>
            </div>

            <div class="py-space-md border-t border-surface-container-highest flex items-center justify-between">
              <button id="btn-undo" class="px-space-md py-1.5 rounded bg-surface-container hover:bg-surface-variant text-on-surface font-body-sm text-body-sm transition-colors flex items-center gap-1 cursor-pointer" type="button">
                <span class="material-symbols-outlined text-[16px]">undo</span>
                <span>Undo</span>
              </button>

              <label class="flex items-center gap-space-xs cursor-pointer select-none">
                <input type="checkbox" id="path-toggle" ${showPaths ? 'checked' : ''} class="sr-only">
                <span class="font-body-sm text-body-sm text-on-surface-variant">Show paths</span>
                <span id="toggle-track" class="w-8 h-4 rounded-full relative transition-colors flex items-center px-0.5 ${showPaths ? 'bg-secondary' : 'bg-surface-variant'}">
                  <span id="toggle-knob" class="w-3 h-3 bg-surface rounded-full transition-transform transform ${showPaths ? 'translate-x-4' : 'translate-x-0'}"></span>
                </span>
              </label>

              <button id="btn-newgame" class="font-label-sm text-label-sm text-on-surface-variant hover:text-on-surface uppercase tracking-wider underline underline-offset-4 cursor-pointer" type="button">
                [New game]
              </button>
            </div>

            <div class="pt-space-xs text-center">
              <p class="font-label-sm text-label-sm text-outline">Arrows move  ·  R rotate wall  ·  U undo  ·  P paths</p>
            </div>

          </div>

        </div>
      </main>
    `;

    renderNotationLog();

    el.querySelector('#btn-close-toast')?.addEventListener('click', () => {
      const toastEl = el.querySelector('#illegal-toast');
      if (toastEl) toastEl.classList.add('hidden');
    });

    el.querySelectorAll('.cell-square').forEach((cell) => {
      cell.addEventListener('click', (e) => {
        if (!isHumanTurn || isThinking || isRequestInFlight) return;
        const r = parseInt(cell.getAttribute('data-cell-r'), 10);
        const c = parseInt(cell.getAttribute('data-cell-c'), 10);
        if (isMoveLegal({ type: 'pawn', to: [r, c] })) {
          isRequestInFlight = true;
          clearPendingChoice();
          onPawnMove(r, c);
        }
      });
    });

    const sidePanel = el.querySelector('#side-panel');
    if (sidePanel) {
      sidePanel.addEventListener('mouseenter', () => {
        if (hoveredSlot !== null) {
          hoveredSlot = null;
          manualOrientationLocked = false;
          updatePreview();
        }
      });
    }

    const boardArena = el.querySelector('#board-arena');
    if (boardArena) {
      boardArena.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        if (!isHumanTurn || isThinking || !hoveredSlot) return;
        toggleOrientation();
      });

      boardArena.addEventListener('mousemove', (e) => {
        if (!isHumanTurn || isThinking) return;
        const rect = boardArena.getBoundingClientRect();
        const pad = 10;
        const contentW = rect.width - 2 * pad;
        const contentH = rect.height - 2 * pad;

        const gridX = ((e.clientX - rect.left - pad) / contentW) * 360;
        const gridY = ((e.clientY - rect.top - pad) / contentH) * 360;

        const c = Math.round((gridX - 40) / 40);
        const r = Math.round((gridY - 40) / 40);

        if (r >= 0 && r < 8 && c >= 0 && c < 8) {
          const ix = (c + 1) * 40;
          const iy = (r + 1) * 40;
          const dist = Math.hypot(gridX - ix, gridY - iy);

          if (dist < 26) {
            const isNewSlot = (!hoveredSlot || hoveredSlot.r !== r || hoveredSlot.c !== c);
            if (isNewSlot) {
              hoveredSlot = { r, c };
              manualOrientationLocked = false;
            }
            if (!manualOrientationLocked) {
              const autoH = Math.abs(gridX - ix) >= Math.abs(gridY - iy);
              const nextOrient = autoH ? 'H' : 'V';
              if (isNewSlot || wallOrientation !== nextOrient) {
                wallOrientation = nextOrient;
              }
            }
            updatePreview();
            return;
          }
        }

        if (hoveredSlot !== null) {
          hoveredSlot = null;
          manualOrientationLocked = false;
          updatePreview();
        }
      });

      boardArena.addEventListener('mouseleave', () => {
        hoveredSlot = null;
        manualOrientationLocked = false;
        updatePreview();
      });

      boardArena.addEventListener('click', (e) => {
        if (!isHumanTurn || !hoveredSlot || isThinking || isRequestInFlight) return;
        // the pawn-move dots deal with their own clicks
        const target = e.target;
        if (target.closest('.legal-dot')) return;

        const { r, c } = hoveredSlot;
        const wallMove = { type: 'wall', r, c, o: wallOrientation };

        if (isMoveLegal(wallMove)) {
          isRequestInFlight = true;
          const placedR = r;
          const placedC = c;
          const placedO = wallOrientation;
          hoveredSlot = null;
          manualOrientationLocked = false;
          updatePreview();
          onWallMove(placedR, placedC, placedO);
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

    el.querySelector('#btn-undo')?.addEventListener('click', () => {
      if (onUndo) onUndo();
    });

    el.querySelector('#btn-newgame')?.addEventListener('click', () => {
      if (onQuit) onQuit();
    });
  }

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
    isRequestInFlight = false;
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

  el.toggleOrientation = function () {
    toggleOrientation();
  };

  el.moveByArrow = moveByArrow;
  el.cancelChoice = cancelChoice;
  el.setRequestInFlight = function (val) {
    isRequestInFlight = val;
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
