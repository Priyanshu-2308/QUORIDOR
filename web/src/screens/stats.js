/**
 * Stats Screen (owner: Priyanshu).
 * Ink field with bone type (no glow, no gradients).
 * Giant numerals for the last AI move: nodes, ms, eval, depth/iterations.
 */
export function createStatsScreen({ onBack }) {
  const el = document.createElement('div');
  el.className = 'screen screen-stats';

  let currentStats = {
    nodes: 0,
    time_s: 0,
    eval: 0,
    depth: null,
    iterations: null,
    tt_hits: null,
    cutoffs: null,
  };

  function render() {
    const ms = (currentStats.time_s * 1000).toFixed(0);
    const evalVal = (currentStats.eval !== undefined && currentStats.eval !== null)
      ? Number(currentStats.eval).toFixed(3)
      : '0.000';
    const nodes = currentStats.nodes || currentStats.iterations || 0;
    const depthOrIter = currentStats.depth ? `DEPTH ${currentStats.depth}` : (currentStats.iterations ? `${currentStats.iterations} ITER` : 'SEARCH');

    el.innerHTML = `
      <div class="screen-header">
        <h1 class="giant-label">AI TELEMETRY</h1>
        <p class="sub-label">LAST DECISION METRICS &bull; ${depthOrIter}</p>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="sub-label">NODES SEARCHED</span>
            <div class="stat-value">${nodes.toLocaleString()}</div>
          </div>

          <div class="stat-item">
            <span class="sub-label">TIME CONSUMED</span>
            <div class="stat-value">${ms} <span style="font-size: 0.4em;">MS</span></div>
          </div>

          <div class="stat-item">
            <span class="sub-label">POSITION EVAL</span>
            <div class="stat-value">${evalVal}</div>
          </div>

          <div class="stat-item">
            <span class="sub-label">PRUNING CUTOFFS</span>
            <div class="stat-value">${(currentStats.cutoffs || 0).toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div class="screen-footer">
        <button class="monolith-btn" id="btn-stats-back">&larr; BACK TO GAME</button>
        <div class="shortcuts-hint">PRESS [ESC] OR [S] TO RETURN</div>
      </div>
    `;

    el.querySelector('#btn-stats-back').addEventListener('click', () => onBack());
  }

  el.updateStats = function (stats) {
    if (stats) {
      currentStats = { ...currentStats, ...stats };
    }
    render();
  };

  render();
  return el;
}

