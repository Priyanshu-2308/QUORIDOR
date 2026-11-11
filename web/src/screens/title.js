/**
 * Title Screen.
 * Vermilion field, giant "QUORIDOR", rotating monolith, button "PLAY".
 */
export function createTitleScreen({ onPlay }) {
  const el = document.createElement('div');
  el.className = 'screen screen-title';

  el.innerHTML = `
    <div class="screen-header">
      <h1 class="giant-title">QUORIDOR</h1>
      <p class="sub-label">A GAME OF CORRIDORS & CUNNING</p>
    </div>

    <div class="screen-footer">
      <button class="monolith-btn" id="btn-play">PLAY &rarr;</button>
      <div class="shortcuts-hint">PRESS [SPACE] OR [ENTER] TO BEGIN</div>
    </div>
  `;

  el.querySelector('#btn-play').addEventListener('click', () => {
    onPlay();
  });

  return el;
}

