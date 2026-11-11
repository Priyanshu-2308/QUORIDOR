/**
 * Game Screen (owner: Priyanshu).
 * Bone field, minimal HUD (turn indicator, wall counters, shortcuts line).
 */
export function createGameScreen({
  onUndo,
  onTogglePaths,
  onOpenStats,
  onQuit,
}) {
  const el = document.createElement('div');
  el.className = 'screen screen-game';

  let currentState = null;
  let humanPlayer = 0;
  let isThinking = false;

  function render() {
    if (!currentState) {
      el.innerHTML = `
        <div class="game-hud-top">
          <div class="turn-indicator">CONNECTING...</div>
        </div>
      `;
      return;
    }

    const isHumanTurn = (currentState.current === humanPlayer) && !currentState.winner && !isThinking;
    let turnText = 'YOUR MOVE';
    let turnClass = 'human-turn';

    if (currentState.winner !== null) {
      turnText = (currentState.winner === humanPlayer) ? 'VICTORY' : 'DEFEAT';
      turnClass = 'terminal';
    } else if (isThinking || currentState.current !== humanPlayer) {
      turnText = 'THINKING';
      turnClass = 'ai-turn';
    }

    const p0Walls = currentState.walls_left[0];
    const p1Walls = currentState.walls_left[1];

    el.innerHTML = `
      <div class="game-hud-top">
        <div>
          <div class="turn-indicator ${turnClass}">${turnText}</div>
          <p class="sub-label" style="margin-top: 4px;">PLY ${currentState.turn_count} &bull; ${humanPlayer === 0 ? 'YOU: COBALT' : 'YOU: VERMILION'}</p>
        </div>

        <div class="wall-stacks">
          <div class="wall-stack-item">
            <span class="sub-label">YOU</span>
            <div class="wall-count">${humanPlayer === 0 ? p0Walls : p1Walls}</div>
            <div class="wall-bars">
              ${Array.from({ length: 10 }).map((_, i) => `
                <div class="wall-bar-pip ${(i < (humanPlayer === 0 ? p0Walls : p1Walls)) ? '' : 'spent'}"></div>
              `).join('')}
            </div>
          </div>

          <div class="wall-stack-item">
            <span class="sub-label">AI</span>
            <div class="wall-count">${humanPlayer === 0 ? p1Walls : p0Walls}</div>
            <div class="wall-bars">
              ${Array.from({ length: 10 }).map((_, i) => `
                <div class="wall-bar-pip ${(i < (humanPlayer === 0 ? p1Walls : p0Walls)) ? '' : 'spent'}"></div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>

      <div class="game-hud-bottom">
        <div class="shortcuts-hint">
          [P] PATHS &bull; [R] ROTATE WALL &bull; [U] UNDO &bull; [S] STATS &bull; [ESC] TITLE
        </div>
        <div style="display: flex; gap: 24px;">
          <button class="monolith-btn" id="hud-undo" style="font-size: clamp(20px, 2.5vw, 36px);">UNDO</button>
          <button class="monolith-btn" id="hud-stats" style="font-size: clamp(20px, 2.5vw, 36px);">STATS</button>
        </div>
      </div>
    `;

    el.querySelector('#hud-undo')?.addEventListener('click', () => onUndo());
    el.querySelector('#hud-stats')?.addEventListener('click', () => onOpenStats());
  }

  el.updateState = function (state, humanPl, thinking = false) {
    currentState = state;
    humanPlayer = humanPl;
    isThinking = thinking;
    render();
  };

  render();
  return el;
}

