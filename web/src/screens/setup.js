// Setup screen: dynamic board size (7-12), player count (2 or 4), miniature preview, and opponent configuration.

export function createSetupScreen({ onStart, onBack }) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-surface text-on-surface font-body-md text-body-md';

  let boardSize = 9;
  let numPlayers = 4;
  let firstMover = 0; // human is seat 0 (South)

  // 2-player available opponents
  const twoPlayerOpponents = [
    {
      id: 'alphabeta',
      badge: '■',
      color: '#E5532D',
      name: 'Professor Prune',
      tagline: 'Thinks first. Snips bad ideas.',
      tiers: [
        { label: 'Easy', spec: 'alphabeta:depth=1' },
        { label: 'Medium', spec: 'alphabeta:depth=2' },
        { label: 'Hard', spec: 'alphabeta:depth=3' },
      ],
      defaultTier: 1,
    },
    {
      id: 'greedy',
      badge: '▲',
      color: '#C05621',
      name: 'Dash',
      tagline: 'Zero walls. All speed.',
      tiers: [{ label: 'Normal', spec: 'greedy' }],
      defaultTier: 0,
    },
    {
      id: 'mcts',
      badge: 'G',
      color: '#2E4BDB',
      name: 'The Gambler',
      tagline: 'Rolls a thousand dice. Hopes.',
      tiers: [
        { label: 'Easy', spec: 'mcts:iterations=50' },
        { label: 'Medium', spec: 'mcts:iterations=200' },
        { label: 'Hard', spec: 'mcts:iterations=600' },
      ],
      defaultTier: 1,
    },
    {
      id: 'random',
      badge: 'W',
      color: '#858383',
      name: 'Wobbles',
      tagline: 'Walks like it lost its keys.',
      tiers: [{ label: 'Normal', spec: 'random' }],
      defaultTier: 0,
    },
  ];

  let selected2pOppIdx = 0; // Professor Prune
  let selected2pTierIdx = 1; // Medium

  // 4-player seat opponents (seats 1, 2, 3)
  const fourPlayerSeats = [
    {
      seat: 1,
      direction: 'West',
      marker: '▲',
      color: '#C05621',
      defaultAgent: 'greedy',
      options: [
        { id: 'greedy', name: 'Dash', tagline: 'Zero walls. All speed.', spec: 'greedy' },
        { id: 'random', name: 'Wobbles', tagline: 'Walks like it lost its keys.', spec: 'random' },
      ],
      selectedIdx: 0,
      tier: 'medium',
    },
    {
      seat: 2,
      direction: 'North',
      marker: '■',
      color: '#E5532D',
      defaultAgent: 'paranoid',
      options: [
        {
          id: 'paranoid',
          name: 'Professor Prune',
          tagline: 'Thinks first. Snips bad ideas.',
          tiers: {
            easy: 'paranoid:depth=1',
            medium: 'paranoid:depth=2',
            hard: 'paranoid:depth=3',
          },
        },
        {
          id: 'maxn',
          name: 'Lone Wolf Lou',
          tagline: 'Everyone for themselves.',
          tiers: {
            easy: 'maxn:depth=1',
            medium: 'maxn:depth=2',
            hard: 'maxn:depth=2',
          },
        },
      ],
      selectedIdx: 0,
      tier: 'medium',
    },
    {
      seat: 3,
      direction: 'East',
      marker: '◆',
      color: '#7C3AED',
      defaultAgent: 'paranoid',
      options: [
        {
          id: 'paranoid',
          name: 'Paranoid Pat',
          tagline: 'Trusts nobody at the table.',
          tiers: {
            easy: 'paranoid:depth=1',
            medium: 'paranoid:depth=2',
            hard: 'paranoid:depth=3',
          },
        },
        {
          id: 'maxn',
          name: 'Lone Wolf Lou',
          tagline: 'Everyone for themselves.',
          tiers: {
            easy: 'maxn:depth=1',
            medium: 'maxn:depth=2',
            hard: 'maxn:depth=2',
          },
        },
        {
          id: 'mcts',
          name: 'The Gambler',
          tagline: 'Rolls a thousand dice. Hopes.',
          tiers: {
            easy: 'mcts:iterations=50',
            medium: 'mcts:iterations=200',
            hard: 'mcts:iterations=600',
          },
        },
      ],
      selectedIdx: 0,
      tier: 'medium',
    },
  ];

  function getWallsPerPlayer(n, p) {
    if (p === 2) return n + 1;
    return Math.ceil((n + 1) / 2);
  }

  function renderMiniatureSvg(n, p) {
    const size = 96;
    const padding = 10;
    const step = (size - 2 * padding) / (n - 1);
    const c0 = Math.floor((n - 1) / 2);

    let dots = '';
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const x = padding + c * step;
        const y = padding + r * step;
        dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="1.5" class="fill-surface-container-highest" />`;
      }
    }

    // Pawn start positions:
    // Seat 0 (South): (N - 1, c0)
    const s0x = padding + c0 * step;
    const s0y = padding + (n - 1) * step;
    let markers = `<circle cx="${s0x.toFixed(1)}" cy="${s0y.toFixed(1)}" r="4" fill="#2E4BDB" />`;

    // Seat 2 (North): (0, N - 1 - c0)
    const s2x = padding + (n - 1 - c0) * step;
    const s2y = padding;
    markers += `<rect x="${(s2x - 3.5).toFixed(1)}" y="${(s2y - 3.5).toFixed(1)}" width="7" height="7" fill="#E5532D" rx="1" />`;

    if (p === 4) {
      // Seat 1 (West): (c0, 0)
      const s1x = padding;
      const s1y = padding + c0 * step;
      markers += `<polygon points="${s1x.toFixed(1)},${(s1y - 4).toFixed(1)} ${(s1x - 3.5).toFixed(1)},${(s1y + 3.5).toFixed(1)} ${(s1x + 3.5).toFixed(1)},${(s1y + 3.5).toFixed(1)}" fill="#C05621" />`;

      // Seat 3 (East): (N - 1 - c0, N - 1)
      const s3x = padding + (n - 1) * step;
      const s3y = padding + (n - 1 - c0) * step;
      markers += `<polygon points="${s3x.toFixed(1)},${(s3y - 4).toFixed(1)} ${(s3x + 4).toFixed(1)},${s3y.toFixed(1)} ${s3x.toFixed(1)},${(s3y + 4).toFixed(1)} ${(s3x - 4).toFixed(1)},${s3y.toFixed(1)}" fill="#7C3AED" />`;
    }

    return `
      <svg class="w-full h-full" viewBox="0 0 ${size} ${size}">
        <g>${dots}</g>
        <g>${markers}</g>
      </svg>
    `;
  }

  function get4pSpec(seatCfg) {
    const opt = seatCfg.options[seatCfg.selectedIdx];
    if (opt.tiers) {
      return opt.tiers[seatCfg.tier] || opt.tiers.medium;
    }
    return opt.spec;
  }

  function render() {
    const walls = getWallsPerPlayer(boardSize, numPlayers);
    const summaryText = `${boardSize}×${boardSize} · ${numPlayers} players · ${walls} walls each`;

    el.innerHTML = `
      <header class="fixed top-0 w-full z-50 bg-background/90 backdrop-blur-md border-b border-outline-variant">
        <div class="h-16 w-full max-w-[700px] mx-auto px-margin flex items-center justify-between">
          <div class="flex items-center gap-space-md">
            <span class="font-label-lg text-label-lg tracking-widest text-primary font-semibold uppercase select-none">QUORIDOR</span>
          </div>
          <div class="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm">
            <span>Dynamic Matrix</span>
          </div>
        </div>
      </header>

      <main class="w-full pt-20 pb-16 bg-background min-h-screen">
        <div class="w-full max-w-[700px] mx-auto px-margin flex flex-col gap-space-xl">
          
          <div class="flex flex-col gap-space-xs">
            <span class="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">Match Protocol</span>
            <h1 class="font-headline-lg text-headline-lg text-primary tracking-tight">New game</h1>
            <p class="font-body-md text-body-md text-on-surface-variant">Configure board dimensions, player count, and strategic opponents.</p>
          </div>

          <!-- Board Size & Player Count -->
          <section class="bg-surface-container-lowest p-space-lg rounded shadow-sm flex flex-col gap-space-lg">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
              <div>
                <h2 class="font-headline-sm text-headline-sm text-primary">Board size</h2>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Custom matrix from 7×7 to 12×12</p>
              </div>
              <div class="inline-flex p-1 bg-surface-container rounded gap-1" id="board-size-group">
                ${[7, 8, 9, 10, 11, 12]
                  .map(
                    (s) => `
                  <button type="button" data-size="${s}" class="size-btn px-3 py-1 font-label-md text-label-md rounded transition-colors ${
                      s === boardSize ? 'bg-primary text-on-primary font-medium' : 'text-on-surface-variant hover:text-primary hover:bg-surface-bright'
                    }">${s}</button>
                `
                  )
                  .join('')}
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pt-space-xs border-t border-outline-variant/30">
              <div>
                <span class="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">Player Count</span>
                <p class="font-body-sm text-body-sm text-on-surface-variant">Bilateral duel or quadrilateral cross</p>
              </div>
              <div class="inline-flex p-1 bg-surface-container rounded gap-1">
                <button type="button" id="btn-2p" class="px-4 py-1.5 font-label-md text-label-md rounded transition-colors ${
                  numPlayers === 2 ? 'bg-primary text-on-primary font-medium' : 'text-on-surface-variant hover:text-primary'
                }">2 players</button>
                <button type="button" id="btn-4p" class="px-4 py-1.5 font-label-md text-label-md rounded transition-colors ${
                  numPlayers === 4 ? 'bg-primary text-on-primary font-medium' : 'text-on-surface-variant hover:text-primary'
                }">4 players</button>
              </div>
            </div>

            <!-- Miniature Board & Spec Summary -->
            <div class="bg-surface-container-low p-space-md rounded flex items-center justify-between gap-space-md">
              <div class="flex items-center gap-space-md">
                <div class="w-24 h-24 bg-surface-container-lowest p-1 rounded shadow-sm flex items-center justify-center">
                  ${renderMiniatureSvg(boardSize, numPlayers)}
                </div>
                <div class="flex flex-col">
                  <span class="font-label-lg text-label-lg font-medium text-primary">${summaryText}</span>
                  <span class="font-body-sm text-body-sm text-on-surface-variant">Inventory balanced according to official formula</span>
                </div>
              </div>
              <div class="font-label-sm text-label-sm text-on-surface-variant text-right hidden sm:block">
                <span>Goal: Opposite Rim</span>
              </div>
            </div>
          </section>

          <!-- Opponents Configuration -->
          <section class="flex flex-col gap-space-md">
            <div class="flex items-center justify-between">
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Seats &amp; Opponents</span>
              <span class="font-body-sm text-body-sm text-on-surface-variant">${numPlayers === 4 ? '3 automatons active' : '1 automaton active'}</span>
            </div>

            ${
              numPlayers === 2
                ? `
              <!-- 2-Player Opponent Selection -->
              <div class="flex flex-col gap-space-xs bg-surface-container-lowest p-space-md rounded shadow-sm">
                <div class="flex flex-col gap-space-sm">
                  ${twoPlayerOpponents
                    .map((opp, idx) => {
                      const isSel = idx === selected2pOppIdx;
                      return `
                      <div class="p-space-sm rounded border cursor-pointer transition-all ${
                        isSel ? 'border-primary bg-surface-container' : 'border-outline-variant/40 bg-surface-container-low hover:bg-surface-container'
                      } opp-card-2p" data-idx="${idx}">
                        <div class="flex items-center justify-between">
                          <div class="flex items-center gap-space-sm">
                            <span class="w-7 h-7 rounded flex items-center justify-center font-bold text-[14px]" style="background: ${opp.color}20; color: ${opp.color}">${opp.badge}</span>
                            <div class="flex flex-col">
                              <span class="font-body-md text-body-md font-medium text-primary">${opp.name}</span>
                              <span class="font-body-sm text-body-sm text-on-surface-variant">${opp.tagline}</span>
                            </div>
                          </div>
                          ${
                            isSel && opp.tiers.length > 1
                              ? `
                            <div class="inline-flex p-1 bg-surface-container-lowest rounded gap-1 tier-group-2p">
                              ${opp.tiers
                                .map(
                                  (t, tIdx) => `
                                <button type="button" data-tier="${tIdx}" class="px-2.5 py-0.5 font-label-sm text-label-sm rounded transition-colors ${
                                    tIdx === selected2pTierIdx ? 'bg-primary text-on-primary font-medium' : 'text-on-surface-variant hover:text-primary'
                                  }">${t.label}</button>
                              `
                                )
                                .join('')}
                            </div>
                          `
                              : ''
                          }
                        </div>
                      </div>
                    `;
                    })
                    .join('')}
                </div>
              </div>
            `
                : `
              <!-- 4-Player Seats -->
              <div class="grid grid-cols-1 gap-space-sm">
                ${fourPlayerSeats
                  .map((s, sIdx) => {
                    const opt = s.options[s.selectedIdx];
                    const hasTiers = !!opt.tiers;
                    return `
                    <div class="bg-surface-container-lowest p-space-md rounded shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
                      <div class="flex items-start sm:items-center gap-space-md">
                        <div class="w-8 h-8 rounded bg-surface-container flex items-center justify-center shrink-0">
                          <span class="text-[14px] font-bold" style="color: ${s.color}">${s.marker}</span>
                        </div>
                        <div class="flex flex-col">
                          <div class="flex items-center gap-space-sm">
                            <span class="font-body-md text-body-md font-medium text-primary">${opt.name}</span>
                            <span class="font-label-sm text-label-sm text-on-surface-variant">${s.direction}</span>
                          </div>
                          <span class="font-body-sm text-body-sm text-on-surface-variant">${opt.tagline}</span>
                        </div>
                      </div>
                      ${
                        hasTiers
                          ? `
                        <div class="inline-flex p-1 bg-surface-container rounded gap-1 self-end sm:self-center tier-group-4p" data-seat-idx="${sIdx}">
                          ${['easy', 'medium', 'hard']
                            .map(
                              (t) => `
                            <button type="button" data-tier="${t}" class="px-2.5 py-0.5 font-label-sm text-label-sm rounded capitalize transition-colors ${
                                s.tier === t ? 'bg-primary text-on-primary font-medium' : 'text-on-surface-variant hover:text-primary'
                              }">${t}</button>
                          `
                            )
                            .join('')}
                        </div>
                      `
                          : `
                        <span class="font-label-sm text-label-sm text-on-surface-variant px-2 py-1 bg-surface-container rounded self-end sm:self-center">Fixed Pace</span>
                      `
                      }
                    </div>
                  `;
                  })
                  .join('')}
              </div>
            `
            }
          </section>

          <!-- Who Moves First -->
          <section class="bg-surface-container-lowest p-space-lg rounded shadow-sm flex flex-col gap-space-md">
            <div class="flex items-center justify-between">
              <span class="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">Who moves first?</span>
              <span class="font-label-sm text-label-sm text-on-surface-variant">Rotation follows standard clockwise rules</span>
            </div>
            <div class="grid grid-cols-2 ${numPlayers === 4 ? 'sm:grid-cols-4' : ''} gap-space-sm">
              <button type="button" class="first-mover-btn p-space-sm rounded flex items-center justify-center gap-space-xs transition-colors ${
                firstMover === 0 ? 'bg-primary text-on-primary font-medium' : 'bg-surface-container text-on-surface hover:bg-surface-container-high'
              }" data-mover="0">
                <span class="text-[12px] font-bold text-secondary">●</span>
                <span class="font-label-md text-label-md">You (South)</span>
              </button>
              ${
                numPlayers === 4
                  ? `
                <button type="button" class="first-mover-btn p-space-sm rounded flex items-center justify-center gap-space-xs transition-colors ${
                  firstMover === 1 ? 'bg-primary text-on-primary font-medium' : 'bg-surface-container text-on-surface hover:bg-surface-container-high'
                }" data-mover="1">
                  <span class="text-[12px] font-bold" style="color: #C05621">▲</span>
                  <span class="font-label-md text-label-md">Dash</span>
                </button>
                <button type="button" class="first-mover-btn p-space-sm rounded flex items-center justify-center gap-space-xs transition-colors ${
                  firstMover === 2 ? 'bg-primary text-on-primary font-medium' : 'bg-surface-container text-on-surface hover:bg-surface-container-high'
                }" data-mover="2">
                  <span class="text-[12px] font-bold text-on-tertiary-container">■</span>
                  <span class="font-label-md text-label-md">Prune</span>
                </button>
                <button type="button" class="first-mover-btn p-space-sm rounded flex items-center justify-center gap-space-xs transition-colors ${
                  firstMover === 3 ? 'bg-primary text-on-primary font-medium' : 'bg-surface-container text-on-surface hover:bg-surface-container-high'
                }" data-mover="3">
                  <span class="text-[12px] font-bold" style="color: #7C3AED">◆</span>
                  <span class="font-label-md text-label-md">Pat</span>
                </button>
              `
                  : `
                <button type="button" class="first-mover-btn p-space-sm rounded flex items-center justify-center gap-space-xs transition-colors ${
                  firstMover === 2 ? 'bg-primary text-on-primary font-medium' : 'bg-surface-container text-on-surface hover:bg-surface-container-high'
                }" data-mover="2">
                  <span class="text-[12px] font-bold text-on-tertiary-container">■</span>
                  <span class="font-label-md text-label-md">${twoPlayerOpponents[selected2pOppIdx].name}</span>
                </button>
              `
              }
            </div>
          </section>

          <!-- Launch Button -->
          <div class="flex flex-col items-center gap-space-sm pt-space-xs">
            <button id="btn-start" type="button" class="w-full sm:w-auto min-w-[280px] bg-primary text-on-primary py-3.5 px-space-xl rounded font-label-lg text-label-lg font-medium text-center hover:opacity-90 active:scale-[0.99] transition-all shadow-sm flex items-center justify-center gap-space-xs cursor-pointer">
              <span>Start game</span>
              <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
            <p class="font-body-sm text-body-sm text-on-surface-variant text-center">
              Reach the opposite rim first. Place walls to impede opponents.
            </p>
          </div>

        </div>
      </main>
    `;

    // Event listeners
    el.querySelectorAll('.size-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        boardSize = parseInt(e.currentTarget.getAttribute('data-size'), 10);
        render();
      });
    });

    el.querySelector('#btn-2p')?.addEventListener('click', () => {
      numPlayers = 2;
      firstMover = 0;
      render();
    });

    el.querySelector('#btn-4p')?.addEventListener('click', () => {
      numPlayers = 4;
      firstMover = 0;
      render();
    });

    el.querySelectorAll('.opp-card-2p').forEach((card) => {
      card.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
        selected2pOppIdx = idx;
        selected2pTierIdx = twoPlayerOpponents[idx].defaultTier;
        render();
      });
    });

    el.querySelectorAll('.tier-group-2p button').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        selected2pTierIdx = parseInt(e.currentTarget.getAttribute('data-tier'), 10);
        render();
      });
    });

    el.querySelectorAll('.tier-group-4p button').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const seatIdx = parseInt(e.currentTarget.parentElement.getAttribute('data-seat-idx'), 10);
        const tier = e.currentTarget.getAttribute('data-tier');
        fourPlayerSeats[seatIdx].tier = tier;
        render();
      });
    });

    el.querySelectorAll('.first-mover-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        firstMover = parseInt(e.currentTarget.getAttribute('data-mover'), 10);
        render();
      });
    });

    el.querySelector('#btn-start')?.addEventListener('click', () => {
      if (numPlayers === 2) {
        const opp = twoPlayerOpponents[selected2pOppIdx];
        const spec = opp.tiers[selected2pTierIdx].spec;
        onStart({
          boardSize,
          numPlayers: 2,
          humanPlayer: firstMover === 0 ? 0 : 2,
          opponent: spec,
          opponentInfo: {
            name: opp.name,
            displayName: `${opp.name} (${opp.tiers[selected2pTierIdx].label})`,
            badge: opp.badge,
            color: opp.color,
          },
        });
      } else {
        const oppSpecs = fourPlayerSeats.map((s) => get4pSpec(s));
        const oppInfos = fourPlayerSeats.map((s) => ({
          seat: s.seat,
          marker: s.marker,
          color: s.color,
          name: s.options[s.selectedIdx].name,
          direction: s.direction,
        }));
        onStart({
          boardSize,
          numPlayers: 4,
          humanPlayer: 0, // human is seat 0 in 4P
          opponents: oppSpecs,
          opponentInfos: oppInfos,
        });
      }
    });
  }

  render();
  return el;
}
