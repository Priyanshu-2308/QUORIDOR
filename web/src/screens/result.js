// Post-match summary dialog for 2P and 4P modes, supporting decisive victories, turn limit draws, and 1-4 rank lists.

export function createResultScreen({ onRematch, onReview, onNewGame }) {
  const el = document.createElement('div');
  el.id = 'result-modal';
  el.className = 'fixed inset-0 z-50 flex items-center justify-center p-margin bg-surface/60 backdrop-blur-sm fade-in';

  let currentResult = {
    winner: 0,
    noWinner: false,
    ranks: null, // e.g. { "0": 1, "1": 3, "2": 2, "3": 4 }
    distances: null, // e.g. { "0": 0, "1": 4, "2": 2, "3": 7 }
    numPlayers: 2,
    humanPlayer: 0,
    turnCount: 24,
    wallsPlaced: 8,
    durationSeconds: 184,
    playerNames: { 0: 'You', 2: 'Professor Prune' },
    playerColors: {
      0: { fill: '#2E4BDB', marker: '●' },
      1: { fill: '#C05621', marker: '▲' },
      2: { fill: '#E5532D', marker: '■' },
      3: { fill: '#7C3AED', marker: '◆' },
    },
  };

  function formatDuration(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  }

  function render() {
    const { winner, noWinner, ranks, distances, numPlayers, humanPlayer, turnCount, wallsPlaced, durationSeconds, playerNames, playerColors } = currentResult;
    const isHumanWin = winner === humanPlayer;

    let headerHtml = '';
    let bodyHtml = '';

    if (numPlayers === 4 && ranks) {
      // 4-Player Mode: 1-4 Ranking Leaderboard
      const isDraw = noWinner || winner === null;
      headerHtml = `
        <div class="flex flex-col text-center mb-space-md">
          <div class="flex items-center justify-center gap-space-xs ${isDraw ? 'text-on-surface-variant' : 'text-secondary'} mb-1">
            <span class="material-symbols-outlined text-[20px]">${isDraw ? 'hourglass_bottom' : 'emoji_events'}</span>
            <span class="font-label-sm text-label-sm tracking-widest uppercase">${isDraw ? 'Pace Terminated' : 'Match Concluded'}</span>
          </div>
          <h2 class="font-headline-lg text-headline-lg text-primary tracking-tight">
            ${isDraw ? 'Draw · Turn limit reached' : isHumanWin ? 'You won' : `${playerNames[winner] || 'Opponent'} won`}
          </h2>
          <p class="font-label-md text-label-md text-on-surface-variant mt-1">
            ${turnCount} plies · ${wallsPlaced} walls placed · ${formatDuration(durationSeconds)}
          </p>
        </div>
      `;

      // Sort seats by rank ascending
      const sortedSeats = Object.keys(ranks)
        .map((k) => parseInt(k, 10))
        .sort((a, b) => ranks[a] - ranks[b]);

      bodyHtml = `
        <div class="flex flex-col gap-space-xs mb-space-lg">
          ${sortedSeats
            .map((seat) => {
              const rnk = ranks[seat];
              const pColor = playerColors[seat] || { fill: '#888', marker: '●' };
              const pName = playerNames[seat] || `Player ${seat}`;
              const dist = distances ? distances[seat] : null;
              const isWinnerSeat = !isDraw && seat === winner;

              return `
              <div class="flex items-center justify-between p-space-sm rounded ${
                rnk === 1 ? 'bg-surface-container-low border border-primary/20' : 'bg-surface-container-lowest'
              }">
                <div class="flex items-center gap-space-sm">
                  <span class="font-label-md text-label-md font-bold text-primary w-4 text-center">${rnk}</span>
                  <div class="w-7 h-7 rounded flex items-center justify-center font-bold text-[13px]" style="background: ${pColor.fill}20; color: ${pColor.fill}">
                    ${pColor.marker}
                  </div>
                  <div class="flex flex-col">
                    <span class="font-body-md text-body-md font-medium text-primary">${pName}</span>
                    <span class="font-label-sm text-label-sm text-on-surface-variant">
                      ${isWinnerSeat ? 'Reached goal rim' : dist !== null ? `${dist} steps to go` : ''}
                    </span>
                  </div>
                </div>
                ${
                  isWinnerSeat
                    ? '<span class="font-label-sm text-label-sm px-2 py-0.5 rounded bg-surface-container-highest text-primary font-semibold uppercase">Winner</span>'
                    : ''
                }
              </div>
            `;
            })
            .join('')}
        </div>
      `;
    } else {
      // 2-Player Mode: Direct Victory Summary
      const resultTitle = noWinner ? 'Draw · Turn limit reached' : isHumanWin ? 'You won' : `${playerNames[winner] || 'Opponent'} won`;
      const themeColor = isHumanWin ? '#2E4BDB' : '#E5532D';

      headerHtml = `
        <div class="flex flex-col mb-space-md">
          <div class="flex items-center gap-space-xs mb-1">
            <span class="w-2.5 h-2.5 rounded-full inline-block" style="background-color: ${themeColor};"></span>
            <span class="font-label-sm text-label-sm uppercase text-on-surface-variant tracking-wider">Match Concluded</span>
          </div>
          <h2 class="font-headline-lg text-headline-lg text-primary tracking-tight font-semibold">${resultTitle}</h2>
          <p class="font-body-md text-body-md text-on-surface-variant">
            ${turnCount} plies · ${wallsPlaced} walls placed · ${formatDuration(durationSeconds)}
          </p>
        </div>
      `;

      bodyHtml = `
        <div class="bg-surface-container-low rounded-lg p-space-md mb-space-lg flex flex-col gap-space-sm border border-surface-container-highest">
          <div class="flex items-center justify-between">
            <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Opponent</span>
            <span class="font-label-md text-label-md text-on-surface font-medium">${playerNames[2] || 'Opponent'}</span>
          </div>
          <div class="h-[1px] bg-surface-variant w-full"></div>
          <div class="flex items-center justify-between">
            <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Outcome</span>
            <span class="font-label-md text-label-md font-semibold" style="color: ${themeColor};">
              ${noWinner ? 'Draw (Turn cap reached)' : isHumanWin ? 'Victory (Goal rim reached)' : 'Defeat'}
            </span>
          </div>
        </div>
      `;
    }

    el.innerHTML = `
      <div class="w-full max-w-md bg-surface-container-lowest rounded-xl p-space-lg flex flex-col relative shadow-xl modal-enter border border-outline-variant/60">
        ${headerHtml}
        ${bodyHtml}
        <div class="flex flex-col gap-space-xs w-full">
          <button id="btn-rematch" class="w-full min-h-[44px] bg-primary text-on-primary font-label-md text-label-md py-space-sm px-space-md rounded transition-colors hover:opacity-90 flex items-center justify-center gap-space-xs cursor-pointer shadow-sm" type="button">
            <span class="material-symbols-outlined text-[18px]">replay</span>
            <span>Play again</span>
          </button>
          <button id="btn-newgame" class="w-full min-h-[44px] bg-surface-container-lowest text-on-surface font-label-md text-label-md py-space-sm px-space-md rounded transition-colors hover:bg-surface-container border border-outline-variant/50 flex items-center justify-center gap-space-xs cursor-pointer" type="button">
            <span class="material-symbols-outlined text-[18px] text-on-surface-variant">add_circle_outline</span>
            <span>New game</span>
          </button>
        </div>
      </div>
    `;

    el.querySelector('#btn-rematch')?.addEventListener('click', () => {
      el.classList.add('hidden');
      if (onRematch) onRematch();
    });

    el.querySelector('#btn-newgame')?.addEventListener('click', () => {
      el.classList.add('hidden');
      if (onNewGame) onNewGame();
    });
  }

  el.showResult = function (res) {
    currentResult = { ...currentResult, ...res };
    render();
    el.classList.remove('hidden');
  };

  render();
  return el;
}
