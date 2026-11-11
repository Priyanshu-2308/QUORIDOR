/**
 * Quoridor Monolith UI — Screen Router and Game Controller (owner: Priyanshu).
 */
import { QuoridorScene } from './scene.js';
import * as api from './api.js';
import { createTitleScreen } from './screens/title.js';
import { createSetupScreen } from './screens/setup.js';
import { createGameScreen } from './screens/game.js';
import { createStatsScreen } from './screens/stats.js';
import { createResultScreen } from './screens/result.js';

class MonolithApp {
  constructor() {
    this.canvasContainer = document.getElementById('canvas-container');
    this.screenContainer = document.getElementById('screen-container');
    this.wipeOverlay = document.getElementById('wipe-overlay');

    this.scene = new QuoridorScene(this.canvasContainer);

    // Active Game State
    this.gameId = null;
    this.gameState = null;
    this.humanPlayer = 0;
    this.opponentSpec = 'alphabeta:depth=3';
    this.legalMoves = [];
    this.lastStats = null;
    this.statsHistory = [];
    this.isAiThinking = false;
    this.isTransitioning = false;

    // Build screen instances
    this.screens = {
      title: createTitleScreen({
        onPlay: () => this.navigate('#/setup'),
      }),
      setup: createSetupScreen({
        onStart: (cfg) => this.startGame(cfg),
        onConfigChange: (lvl, col) => this.scene.updateSetupMonolith(lvl, col),
      }),
      game: createGameScreen({
        onUndo: () => this.handleUndo(),
        onTogglePaths: () => this.togglePaths(),
        onOpenStats: () => this.navigate('#/stats'),
        onQuit: () => this.navigate('#/title'),
      }),
      stats: createStatsScreen({
        onBack: () => this.navigate('#/game'),
      }),
      result: createResultScreen({
        onRematch: () => this.restartGame(),
        onMenu: () => this.navigate('#/title'),
      }),
    };

    // Attach scene callbacks for board interaction
    this.scene.onCellClick = (r, c) => this.handlePawnMove(r, c);
    this.scene.onWallClick = (r, c, o) => this.handleWallMove(r, c, o);

    // Keyboard controls
    window.addEventListener('keydown', this.handleKeyDown.bind(this));
    window.addEventListener('hashchange', () => this.route());

    // Initial route
    if (!window.location.hash) {
      window.location.hash = '#/title';
    } else {
      this.route();
    }
  }

  /* -------------------------------------------------------------
   * Router and Screen Transitions
   * ------------------------------------------------------------- */
  navigate(hash) {
    if (window.location.hash === hash) {
      this.route();
    } else {
      window.location.hash = hash;
    }
  }

  async route() {
    const hash = window.location.hash || '#/title';
    const screenKey = hash.replace('#/', '').split('?')[0] || 'title';

    if (!this.screens[screenKey]) {
      this.navigate('#/title');
      return;
    }

    if (screenKey === 'game' && !this.gameId) {
      this.navigate('#/setup');
      return;
    }

    if (this.currentScreenKey === screenKey) return;
    await this.transitionTo(screenKey);
  }

  async transitionTo(screenKey) {
    if (this.isTransitioning) return;
    this.isTransitioning = true;

    // 1. Wipe in (cover screen)
    this.wipeOverlay.style.transition = 'transform 0.2s cubic-bezier(0.77, 0, 0.175, 1)';
    this.wipeOverlay.style.transform = 'translateX(0%)';
    await new Promise(r => setTimeout(r, 200));

    // 2. Swap active screen DOM
    this.screenContainer.innerHTML = '';
    const screenEl = this.screens[screenKey];
    this.screenContainer.appendChild(screenEl);

    // 3. Update 3D scene active group
    this.scene.setScreen(screenKey);
    this.currentScreenKey = screenKey;

    if (screenKey === 'game') {
      this.screens.game.updateState(this.gameState, this.humanPlayer, this.isAiThinking);
      this.scene.syncGameState(this.gameState, this.legalMoves);
      this.refreshPaths();
    } else if (screenKey === 'stats') {
      this.screens.stats.updateStats(this.lastStats);
      if (this.lastStats) {
        this.scene.updateStatsVisual(this.lastStats.nodes || this.lastStats.iterations || 100, this.statsHistory);
      }
    } else if (screenKey === 'result') {
      this.screens.result.setResult(this.gameState ? this.gameState.winner : null, this.humanPlayer);
      this.scene.setResultWinner(this.gameState ? this.gameState.winner : 0);
    }

    // 4. Wipe out (reveal new screen)
    this.wipeOverlay.style.transform = 'translateX(100%)';
    await new Promise(r => setTimeout(r, 200));
    this.wipeOverlay.style.transition = 'none';
    this.wipeOverlay.style.transform = 'translateX(-100%)';

    this.isTransitioning = false;
  }

  /* -------------------------------------------------------------
   * Game Lifecycle & Turns
   * ------------------------------------------------------------- */
  async startGame({ opponent, humanPlayer }) {
    this.opponentSpec = opponent;
    this.humanPlayer = humanPlayer;
    this.statsHistory = [];
    this.lastStats = null;

    try {
      const data = await api.createGame(opponent, humanPlayer);
      this.gameId = data.game_id;
      this.gameState = data.state;

      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;

      this.navigate('#/game');

      // If AI moves first
      if (this.gameState.current !== this.humanPlayer) {
        await this.triggerAiMove();
      }
    } catch (err) {
      alert(`Failed to start game: ${err.message}`);
    }
  }

  async restartGame() {
    await this.startGame({
      opponent: this.opponentSpec,
      humanPlayer: this.humanPlayer,
    });
  }

  async handlePawnMove(r, c) {
    if (this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    try {
      const move = { type: 'pawn', to: [r, c] };
      const data = await api.makeMove(this.gameId, move);
      this.gameState = data.state;
      this.onMoveApplied();
    } catch (err) {
      console.warn('Move failed:', err.message);
    }
  }

  async handleWallMove(r, c, o) {
    if (this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    try {
      const move = { type: 'wall', r, c, o };
      const data = await api.makeMove(this.gameId, move);
      this.gameState = data.state;
      this.onMoveApplied();
    } catch (err) {
      console.warn('Wall placement failed:', err.message);
    }
  }

  async onMoveApplied() {
    if (this.gameState.winner !== null) {
      this.screens.game.updateState(this.gameState, this.humanPlayer, false);
      this.scene.syncGameState(this.gameState, []);
      setTimeout(() => this.navigate('#/result'), 600);
      return;
    }

    // Refresh legal moves and sync
    const legalData = await api.getLegalMoves(this.gameId);
    this.legalMoves = legalData.moves;
    this.screens.game.updateState(this.gameState, this.humanPlayer, true);
    this.scene.syncGameState(this.gameState, this.legalMoves);
    this.refreshPaths();

    // Trigger AI move if it's AI turn
    if (this.gameState.current !== this.humanPlayer) {
      await this.triggerAiMove();
    }
  }

  async triggerAiMove() {
    this.isAiThinking = true;
    this.screens.game.updateState(this.gameState, this.humanPlayer, true);

    try {
      const data = await api.getAiMove(this.gameId);
      this.gameState = data.state;
      this.lastStats = data.stats;
      if (data.stats && (data.stats.nodes || data.stats.iterations)) {
        this.statsHistory.push(data.stats.nodes || data.stats.iterations);
      }

      if (this.gameState.winner !== null) {
        this.screens.game.updateState(this.gameState, this.humanPlayer, false);
        this.scene.syncGameState(this.gameState, []);
        setTimeout(() => this.navigate('#/result'), 700);
        return;
      }

      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;
    } catch (err) {
      console.error('AI move error:', err);
    } finally {
      this.isAiThinking = false;
      this.screens.game.updateState(this.gameState, this.humanPlayer, false);
      this.scene.syncGameState(this.gameState, this.legalMoves);
      this.refreshPaths();
    }
  }

  async handleUndo() {
    if (this.isAiThinking || !this.gameId) return;

    try {
      const data = await api.undoMove(this.gameId);
      this.gameState = data.state;
      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;

      this.screens.game.updateState(this.gameState, this.humanPlayer, false);
      this.scene.syncGameState(this.gameState, this.legalMoves);
      this.refreshPaths();
    } catch (err) {
      console.warn('Undo error:', err.message);
    }
  }

  async refreshPaths() {
    if (!this.gameId) return;
    try {
      const data = await api.getPaths(this.gameId);
      this.scene.setShortestPaths(data.paths);
    } catch (_) {}
  }

  togglePaths() {
    return this.scene.toggleShortestPaths();
  }

  /* -------------------------------------------------------------
   * Global Keyboard Shortcuts
   * ------------------------------------------------------------- */
  handleKeyDown(event) {
    const key = event.key.toUpperCase();

    if (this.currentScreenKey === 'title') {
      if (key === ' ' || key === 'ENTER') {
        this.navigate('#/setup');
      }
    } else if (this.currentScreenKey === 'setup') {
      if (key === 'ENTER') {
        this.screens.setup.querySelector('#btn-start')?.click();
      } else if (key === ' ') {
        this.screens.setup.querySelector('#btn-side')?.click();
      } else if (key === 'ARROWLEFT') {
        this.screens.setup.querySelector('#btn-prev-opp')?.click();
      } else if (key === 'ARROWRIGHT') {
        this.screens.setup.querySelector('#btn-next-opp')?.click();
      } else if (key === 'ARROWUP') {
        this.screens.setup.querySelector('#btn-next-lvl')?.click();
      } else if (key === 'ARROWDOWN') {
        this.screens.setup.querySelector('#btn-prev-lvl')?.click();
      }
    } else if (this.currentScreenKey === 'game') {
      if (key === 'R') {
        this.scene.toggleWallOrientation();
      } else if (key === 'P') {
        this.togglePaths();
      } else if (key === 'U') {
        this.handleUndo();
      } else if (key === 'S') {
        this.navigate('#/stats');
      } else if (key === 'ESCAPE') {
        this.navigate('#/title');
      }
    } else if (this.currentScreenKey === 'stats') {
      if (key === 'ESCAPE' || key === 'S') {
        this.navigate('#/game');
      }
    } else if (this.currentScreenKey === 'result') {
      if (key === 'R') {
        this.restartGame();
      } else if (key === 'ESCAPE') {
        this.navigate('#/title');
      }
    }
  }
}

// Instantiate application on DOM ready
window.addEventListener('DOMContentLoaded', () => {
  new MonolithApp();
});

