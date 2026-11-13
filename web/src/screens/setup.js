// Match configuration screen: opponent selection, difficulty levels, and turn assignment.

export function createSetupScreen({ onStart, onBack }) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-surface text-on-surface font-body-md text-body-md';

  const opponents = [
    {
      id: 'random',
      badge: 'W',
      name: 'Wobbles',
      desc: 'Walks like it lost its keys.',
      levels: [],
      defaultLevelIdx: 0,
      specFn: () => 'random',
    },
    {
      id: 'greedy',
      badge: 'D',
      name: 'Dash',
      desc: 'Zero walls. All speed.',
      levels: [],
      defaultLevelIdx: 0,
      specFn: () => 'greedy',
    },
    {
      id: 'alphabeta',
      badge: 'P',
      name: 'Professor Prune',
      desc: 'Thinks first. Snips bad ideas.',
      levels: [
        { label: 'Casual', value: 1, text: 'Depth 1' },
        { label: 'Careful', value: 2, text: 'Depth 2' },
        { label: 'Sharp', value: 3, text: 'Depth 3' },
        { label: 'Ruthless', value: 4, text: 'Depth 4' },
      ],
      defaultLevelIdx: 2, // Sharp (Depth 3)
      specFn: (lvl) => `alphabeta:depth=${lvl.value}`,
    },
    {
      id: 'mcts',
      badge: 'G',
      name: 'The Gambler',
      desc: 'Rolls a thousand dice. Hopes.',
      levels: [
        { label: 'Casual', value: 200, text: '200 iter' },
        { label: 'Careful', value: 400, text: '400 iter' },
        { label: 'Sharp', value: 600, text: '600 iter' },
        { label: 'Ruthless', value: 1000, text: '1000 iter' },
      ],
      defaultLevelIdx: 2, // Sharp (600 iter)
      specFn: (lvl) => `mcts:iterations=${lvl.value}`,
    },
  ];

  let selectedOppIdx = 2; // Professor Prune
  let selectedLevelIdx = opponents[2].defaultLevelIdx;
  let humanPlayer = 0; // 0 = You, 1 = Opponent

  function getSelectedSpec() {
    const opp = opponents[selectedOppIdx];
    if (opp.levels.length > 0) {
      return opp.specFn(opp.levels[selectedLevelIdx]);
    }
    return opp.specFn();
  }

  function getOpponentDisplayName() {
    const opp = opponents[selectedOppIdx];
    if (opp.levels.length > 0) {
      return `${opp.name} (${opp.levels[selectedLevelIdx].text})`;
    }
    return opp.name;
  }

  function render() {
    const currentOpp = opponents[selectedOppIdx];
    const hasLevels = currentOpp.levels.length > 0;

    el.innerHTML = `
      <header class="fixed top-0 w-full z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div class="h-14 px-margin flex items-center justify-between max-w-[440px] mx-auto">
          <button id="btn-back" aria-label="Back" class="min-w-[44px] min-h-[44px] flex items-center justify-center text-on-surface hover:text-on-surface-variant transition-colors cursor-pointer" type="button">
            <span class="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <span class="font-label-lg text-label-lg uppercase tracking-wider text-on-surface font-semibold">QUORIDOR</span>
          <div class="w-11"></div>
        </div>
      </header>

      <main class="flex flex-col relative w-full pt-14 bg-surface min-h-screen">
        <div class="flex flex-col w-full pb-safe">
          <div class="w-full max-w-[420px] mx-auto px-margin py-space-lg flex flex-col gap-space-lg">
            
            <div class="flex flex-col gap-space-xs">
              <h2 class="font-headline-md text-headline-md text-on-surface font-medium">New game</h2>
              <p class="font-body-sm text-body-sm text-on-surface-variant">Pick your opponent</p>
            </div>

            <div class="flex flex-col gap-space-lg bg-surface-container-lowest p-space-md rounded-lg shadow-sm">
              
              <div class="flex flex-col gap-space-sm">
                <div class="flex items-center justify-between">
                  <label class="font-label-md text-label-md uppercase text-on-surface font-medium">Opponent</label>
                </div>
                <div class="flex flex-col gap-space-xs" role="radiogroup">
                  ${opponents.map((opp, idx) => {
                    const isSelected = idx === selectedOppIdx;
                    return `
                      <button type="button" data-opp-idx="${idx}" class="opp-card w-full text-left p-space-sm rounded-lg transition-all flex items-center gap-space-sm cursor-pointer ${
                        isSelected
                          ? 'bg-surface-container border-2 border-primary relative shadow-sm'
                          : 'bg-surface-container-low hover:bg-surface-container border border-transparent'
                      }">
                        <div class="w-9 h-9 rounded-full bg-surface-container-highest border border-outline-variant/40 flex items-center justify-center shrink-0">
                          <span class="font-headline-sm text-headline-sm font-semibold text-[#E5532D]">${opp.badge}</span>
                        </div>
                        <div class="flex flex-col flex-1 min-w-0">
                          <div class="flex items-center justify-between">
                            <span class="font-body-md text-body-md font-semibold text-on-surface">${opp.name}</span>
                            ${isSelected ? '<span class="material-symbols-outlined text-[18px] text-primary">check_circle</span>' : ''}
                          </div>
                          <span class="font-body-sm text-body-sm text-on-surface-variant truncate">${opp.desc}</span>
                        </div>
                      </button>
                    `;
                  }).join('')}
                </div>
              </div>

              ${hasLevels ? `
                <div class="flex flex-col gap-space-xs">
                  <div class="flex items-center justify-between">
                    <label class="font-label-md text-label-md uppercase text-on-surface font-medium">How sharp?</label>
                    <span class="font-label-sm text-label-sm text-outline">${currentOpp.name}</span>
                  </div>
                  <div class="grid grid-cols-4 gap-space-xs">
                    ${currentOpp.levels.map((lvl, idx) => {
                      const isSelected = idx === selectedLevelIdx;
                      return `
                        <button type="button" data-level-idx="${idx}" class="level-btn py-2 text-center rounded font-body-sm text-body-sm transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-primary text-on-primary font-medium'
                            : 'bg-surface-container-low text-on-surface hover:bg-surface-container-high'
                        }">
                          ${lvl.label}
                        </button>
                      `;
                    }).join('')}
                  </div>
                </div>
              ` : ''}

              <div class="flex flex-col gap-space-xs">
                <label class="font-label-md text-label-md uppercase text-on-surface font-medium">Who moves first?</label>
                <div class="grid grid-cols-2 gap-space-xs p-1 bg-surface-container rounded-lg">
                  <button type="button" id="turn-you" class="turn-opt py-2.5 px-3 rounded flex items-center justify-center gap-space-xs transition-all cursor-pointer ${
                    humanPlayer === 0
                      ? 'bg-secondary text-on-secondary font-medium shadow-sm'
                      : 'text-on-surface hover:bg-surface-container-high'
                  }">
                    <span class="w-2 h-2 rounded-full ${humanPlayer === 0 ? 'bg-surface' : 'bg-outline'}"></span>
                    <span class="font-body-md text-body-md">You</span>
                  </button>
                  <button type="button" id="turn-opp" class="turn-opt py-2.5 px-3 rounded flex items-center justify-center gap-space-xs transition-all cursor-pointer ${
                    humanPlayer === 1
                      ? 'bg-primary text-on-primary font-medium shadow-sm'
                      : 'text-on-surface hover:bg-surface-container-high'
                  }">
                    <span class="w-2 h-2 rounded-full ${humanPlayer === 1 ? 'bg-surface' : 'bg-outline'}"></span>
                    <span class="font-body-md text-body-md truncate">${currentOpp.name}</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="flex flex-col gap-space-sm pt-space-xs">
              <button id="btn-start" type="button" class="w-full py-3.5 px-space-md rounded bg-primary text-on-primary font-headline-sm text-headline-sm font-medium tracking-wide hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-space-xs cursor-pointer shadow-sm">
                <span>Start game</span>
                <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
              </button>
              
              <p class="font-body-sm text-body-sm text-outline text-center leading-relaxed">
                Reach the opposite side first. Place walls to slow your opponent.
              </p>
            </div>

          </div>
        </div>
      </main>
    `;

    el.querySelector('#btn-back')?.addEventListener('click', () => {
      if (onBack) onBack();
    });

    el.querySelectorAll('.opp-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.getAttribute('data-opp-idx'), 10);
        selectedOppIdx = idx;
        selectedLevelIdx = opponents[idx].defaultLevelIdx;
        render();
      });
    });

    el.querySelectorAll('.level-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.getAttribute('data-level-idx'), 10);
        selectedLevelIdx = idx;
        render();
      });
    });

    el.querySelector('#turn-you')?.addEventListener('click', () => {
      humanPlayer = 0;
      render();
    });

    el.querySelector('#turn-opp')?.addEventListener('click', () => {
      humanPlayer = 1;
      render();
    });

    el.querySelector('#btn-start')?.addEventListener('click', () => {
      onStart({
        opponent: getSelectedSpec(),
        humanPlayer,
        opponentInfo: {
          name: currentOpp.name,
          displayName: getOpponentDisplayName(),
          badge: currentOpp.badge,
          id: currentOpp.id,
        },
      });
    });
  }

  render();
  return el;
}
