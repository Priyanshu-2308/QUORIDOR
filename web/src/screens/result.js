/**
 * Result Screen.
 * Solid field with winner's colour (Cobalt for human win, Vermilion for AI win, Ochre for draw).
 * Giant "YOU WIN" or "AI WINS", buttons "REMATCH" and "MENU".
 */
export function createResultScreen({ onRematch, onMenu }) {
  const el = document.createElement('div');
  el.className = 'screen screen-result-p0';

  let currentWinner = 0;
  let humanPlayer = 0;

  function render() {
    const isHumanWin = (currentWinner === humanPlayer);
    let titleText = isHumanWin ? 'YOU WIN' : 'AI WINS';
    let subtitle = isHumanWin ? 'CORRIDOR MASTERED' : 'OPPONENT SECURED GOAL';

    if (currentWinner === null) {
      titleText = 'DRAW';
      subtitle = 'MAX PLIES REACHED';
      el.className = 'screen screen-result-draw';
    } else if (currentWinner === 0) {
      el.className = 'screen screen-result-p0';
    } else {
      el.className = 'screen screen-result-p1';
    }

    el.innerHTML = `
      <div class="screen-header">
        <h1 class="giant-title">${titleText}</h1>
        <p class="sub-label">${subtitle}</p>
      </div>

      <div class="screen-footer">
        <div class="result-buttons">
          <button class="monolith-btn" id="btn-rematch">REMATCH &rarr;</button>
          <button class="monolith-btn" id="btn-menu">MENU</button>
        </div>
        <div class="shortcuts-hint">PRESS [R] REMATCH &bull; [ESC] TITLE MENU</div>
      </div>
    `;

    el.querySelector('#btn-rematch').addEventListener('click', () => onRematch());
    el.querySelector('#btn-menu').addEventListener('click', () => onMenu());
  }

  el.setResult = function (winner, humanPl) {
    currentWinner = winner;
    humanPlayer = humanPl;
    render();
  };

  render();
  return el;
}

