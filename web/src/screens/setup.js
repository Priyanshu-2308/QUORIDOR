/**
 * Setup Screen.
 * Cobalt field, opponent selector (RANDOM / GREEDY / ALPHA-BETA / MCTS),
 * strength level selector (depth 2/3/4 or iterations 200/500/1000/2000),
 * side selector (YOU START / AI STARTS), button "START".
 */
export function createSetupScreen({ onStart, onConfigChange }) {
  const el = document.createElement('div');
  el.className = 'screen screen-setup';

  const opponents = [
    { id: 'alphabeta', name: 'ALPHA-BETA', levels: [2, 3, 4], defaultLevelIdx: 1 },
    { id: 'mcts', name: 'MCTS', levels: [200, 400, 600, 1000], defaultLevelIdx: 2 },
    { id: 'greedy', name: 'GREEDY', levels: [], defaultLevelIdx: 0 },
    { id: 'random', name: 'RANDOM', levels: [], defaultLevelIdx: 0 },
  ];

  let oppIdx = 0;
  let levelIdx = opponents[0].defaultLevelIdx;
  let humanPlayer = 0; // 0 = YOU START, 1 = AI STARTS

  function getSpec() {
    const opp = opponents[oppIdx];
    if (opp.id === 'alphabeta') {
      return `alphabeta:depth=${opp.levels[levelIdx]}`;
    }
    if (opp.id === 'mcts') {
      return `mcts:iterations=${opp.levels[levelIdx]}`;
    }
    return opp.id;
  }

  function render() {
    const opp = opponents[oppIdx];
    const hasLevels = opp.levels.length > 0;
    const currentVal = hasLevels ? opp.levels[levelIdx] : '';
    const levelLabel = opp.id === 'alphabeta' ? `DEPTH ${currentVal}` : `ITERATIONS ${currentVal}`;

    el.innerHTML = `
      <div class="screen-header">
        <p class="sub-label">SELECT OPPONENT &amp; STRENGTH</p>
        <div class="row-controls">
          <button class="chevron-btn" id="btn-prev-opp">&lsaquo;</button>
          <div class="giant-label" id="opp-name">${opp.name}</div>
          <button class="chevron-btn" id="btn-next-opp">&rsaquo;</button>
        </div>

        ${hasLevels ? `
          <div class="row-controls" style="margin-top: 16px;">
            <button class="chevron-btn" id="btn-prev-lvl">&darr;</button>
            <div class="giant-number" id="lvl-val">${currentVal}</div>
            <button class="chevron-btn" id="btn-next-lvl">&uarr;</button>
          </div>
          <p class="sub-label" style="opacity: 0.7;">${levelLabel}</p>
        ` : `
          <div style="height: clamp(56px, 12vw, 180px); display: flex; align-items: center;">
            <p class="sub-label" style="opacity: 0.5;">STANDARD PROFILE</p>
          </div>
        `}
      </div>

      <div class="screen-footer">
        <div style="margin-bottom: clamp(16px, 3vw, 32px);">
          <p class="sub-label">WHO MOVES FIRST?</p>
          <button class="monolith-btn" id="btn-side" style="font-size: clamp(28px, 5vw, 64px);">
            ${humanPlayer === 0 ? 'YOU START (P0)' : 'AI STARTS (P1)'}
          </button>
        </div>

        <button class="monolith-btn" id="btn-start">START &rarr;</button>
        <div class="shortcuts-hint">USE [&larr;/&rarr;] OPPONENT &bull; [&uarr;/&darr;] DIFFICULTY &bull; [SPACE] SWITCH SIDE</div>
      </div>
    `;

    // Hook listeners
    el.querySelector('#btn-prev-opp').addEventListener('click', () => {
      oppIdx = (oppIdx - 1 + opponents.length) % opponents.length;
      levelIdx = opponents[oppIdx].defaultLevelIdx;
      updateVisual();
      render();
    });

    el.querySelector('#btn-next-opp').addEventListener('click', () => {
      oppIdx = (oppIdx + 1) % opponents.length;
      levelIdx = opponents[oppIdx].defaultLevelIdx;
      updateVisual();
      render();
    });

    if (hasLevels) {
      el.querySelector('#btn-prev-lvl').addEventListener('click', () => {
        if (levelIdx > 0) {
          levelIdx--;
          updateVisual();
          render();
        }
      });

      el.querySelector('#btn-next-lvl').addEventListener('click', () => {
        if (levelIdx < opp.levels.length - 1) {
          levelIdx++;
          updateVisual();
          render();
        }
      });
    }

    el.querySelector('#btn-side').addEventListener('click', () => {
      humanPlayer = (humanPlayer === 0) ? 1 : 0;
      render();
    });

    el.querySelector('#btn-start').addEventListener('click', () => {
      onStart({ opponent: getSpec(), humanPlayer });
    });
  }

  function updateVisual() {
    if (onConfigChange) {
      const opp = opponents[oppIdx];
      let levelNum = levelIdx + 1;
      let color = 0xEDE7DA;
      if (opp.id === 'alphabeta') color = 0xE8452C;
      if (opp.id === 'mcts') color = 0xD9A441;
      if (opp.id === 'greedy') color = 0x2441D6;
      onConfigChange(levelNum, color);
    }
  }

  // Initial render
  render();
  updateVisual();

  return el;
}

