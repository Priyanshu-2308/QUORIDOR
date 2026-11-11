/**
 * Game Over Screen & Modal Overlay - Quiet Bastion Design System.
 * Stitch Project 6777394393065907640 (Screen: Quoridor - Game Over).
 */

export function createResultScreen({ onRematch, onReview, onNewGame }) {
  const el = document.createElement('div');
  el.className = 'fixed inset-0 z-50 flex items-center justify-center p-margin bg-surface/60 backdrop-blur-sm fade-in';

  let currentResult = {
    winner: 0,
    humanPlayer: 0,
    opponentInfo: { name: 'Professor Prune', displayName: 'Professor Prune (Depth 3)' },
    turnCount: 24,
    wallsPlaced: 8,
    durationSeconds: 184,
    lastNotation: 'e9#',
  };

  function formatDuration(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  }

  function render() {
    const isHumanWin = (currentResult.winner === currentResult.humanPlayer);
    const resultTitle = isHumanWin ? 'You won' : `${currentResult.opponentInfo.name} won`;
    const themeColor = isHumanWin ? '#2E4BDB' : '#E5532D';

    el.innerHTML = `
      <!-- Modal Card: Grounded dual-plane elevation, pure white surface, flat discipline -->
      <div class="w-full max-w-sm bg-surface-container-lowest rounded-xl p-space-lg flex flex-col relative shadow-xl modal-enter" style="outline: 1px solid #D9D7D0;">
        
        <!-- Top Monogram & Victory Status -->
        <div class="flex items-center justify-between pb-space-md mb-space-md bg-surface-container-low -mx-space-lg -mt-space-lg px-space-lg pt-space-md rounded-t-xl border-b border-surface-container-highest">
          <div class="flex items-center gap-space-xs">
            <span class="w-2 h-2 rounded-full inline-block" style="background-color: ${themeColor};"></span>
            <span class="font-label-sm text-label-sm uppercase text-on-surface-variant tracking-wider">Match Concluded</span>
          </div>
          <span class="font-label-sm text-label-sm text-outline font-mono">Notation: ${currentResult.lastNotation}</span>
        </div>

        <!-- Result Headline & Editorial Subtext -->
        <div class="mb-space-lg">
          <div class="flex items-center gap-space-sm mb-1">
            <h2 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface tracking-tight font-semibold">${resultTitle}</h2>
            ${isHumanWin ? '<span class="material-symbols-outlined text-secondary text-[24px]">verified</span>' : '<span class="material-symbols-outlined text-on-tertiary-container text-[24px]">smart_toy</span>'}
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant">
            ${currentResult.turnCount} plies, ${currentResult.wallsPlaced} walls placed
          </p>
        </div>

        <!-- Match Stats Breakdown -->
        <div class="bg-surface-container-low rounded-lg p-space-md mb-space-lg flex flex-col gap-space-sm border border-surface-container-highest">
          <div class="flex items-center justify-between">
            <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Duration</span>
            <span class="font-label-md text-label-md text-on-surface font-medium font-mono">${formatDuration(currentResult.durationSeconds)}</span>
          </div>
          <div class="h-[1px] bg-surface-variant w-full"></div>
          <div class="flex items-center justify-between">
            <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Opponent</span>
            <span class="font-label-md text-label-md text-on-surface font-medium truncate max-w-[180px]">${currentResult.opponentInfo.displayName || currentResult.opponentInfo.name}</span>
          </div>
          <div class="h-[1px] bg-surface-variant w-full"></div>
          <div class="flex items-center justify-between">
            <span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Result</span>
            <span class="font-label-md text-label-md font-semibold" style="color: ${themeColor};">
              ${isHumanWin ? 'Victory (Corridor Mastered)' : 'Defeat (Opponent Reached Goal)'}
            </span>
          </div>
        </div>

        <!-- Buttons Stack (Editorial hierarchy) -->
        <div class="flex flex-col gap-space-sm w-full">
          <!-- Rematch: The ONLY solid black (#151515) primary button on the viewport -->
          <button id="btn-rematch" class="w-full min-h-[44px] bg-primary text-on-primary font-label-md text-label-md py-space-sm px-space-md rounded transition-colors active:bg-neutral-800 flex items-center justify-center gap-space-xs cursor-pointer shadow-sm" type="button">
            <span class="material-symbols-outlined text-[18px]">replay</span>
            <span>Rematch</span>
          </button>

          <!-- Secondary Outlined Action: Review Match -->
          <button id="btn-review" class="w-full min-h-[44px] bg-surface-container-lowest text-on-surface font-label-md text-label-md py-space-sm px-space-md rounded transition-colors hover:bg-surface-container-low active:bg-surface-container flex items-center justify-center gap-space-xs cursor-pointer" type="button" style="outline: 1px solid #D9D7D0;">
            <span class="material-symbols-outlined text-[18px] text-on-surface-variant">history_edu</span>
            <span>Review match</span>
          </button>

          <!-- Tertiary Outlined Action: New Game -->
          <button id="btn-newgame" class="w-full min-h-[44px] bg-surface-container-lowest text-on-surface font-label-md text-label-md py-space-sm px-space-md rounded transition-colors hover:bg-surface-container-low active:bg-surface-container flex items-center justify-center gap-space-xs cursor-pointer" type="button" style="outline: 1px solid #D9D7D0;">
            <span class="material-symbols-outlined text-[18px] text-on-surface-variant">add_circle_outline</span>
            <span>New game</span>
          </button>
        </div>
      </div>
    `;

    // Listeners
    el.querySelector('#btn-rematch')?.addEventListener('click', () => {
      if (onRematch) onRematch();
    });

    el.querySelector('#btn-review')?.addEventListener('click', () => {
      el.classList.add('hidden');
      if (onReview) onReview();
    });

    el.querySelector('#btn-newgame')?.addEventListener('click', () => {
      if (onNewGame) onNewGame();
    });
  }

  el.showResult = function (data) {
    currentResult = { ...currentResult, ...data };
    el.classList.remove('hidden');
    render();
  };

  el.hide = function () {
    el.classList.add('hidden');
  };

  render();
  return el;
}
