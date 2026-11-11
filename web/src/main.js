/**
 * Quoridor V2 — Quiet Bastion Minimalist Client.
 * Router and Game Controller orchestrating Setup, Arena, and Overlays.
 */

import * as api from './api.js';
import { createTitleScreen } from './screens/title.js';
import { createSetupScreen } from './screens/setup.js';
import { createGameScreen } from './screens/game.js';
import { createResultScreen } from './screens/result.js';

class QuoridorApp {
  constructor() {
    this.screenContainer = document.getElementById('screen-container');

    // App State
    this.gameId = null;
    this.gameState = null;
    this.humanPlayer = 0;
    this.opponentSpec = 'alphabeta:depth=3';
    this.opponentInfo = {
      name: 'Professor Prune',
      displayName: 'Professor Prune (Depth 3)',
      badge: 'P',
      id: 'alphabeta',
    };
    this.legalMoves = [];
    this.lastStats = null;
    this.isAiThinking = false;
    this.currentScreenKey = null;

    // Instantiate screen modules
    this.screens = {
      title: createTitleScreen({
        onPlay: () => this.navigate('#/setup'),
      }),
      setup: createSetupScreen({
        onStart: (cfg) => this.startGame(cfg),
        onBack: () => this.navigate('#/title'),
      }),
      game: createGameScreen({
        onPawnMove: (r, c) => this.handlePawnMove(r, c),
        onWallMove: (r, c, o) => this.handleWallMove(r, c, o),
        onUndo: () => this.handleUndo(),
        onTogglePaths: () => this.refreshPaths(),
        onQuit: () => this.navigate('#/setup'),
      }),
    };

    // Instantiate result overlay
    this.resultOverlay = createResultScreen({
      onRematch: () => this.restartGame(),
      onReview: () => {
        // Overlay dismissed, user stays in arena to inspect final board
      },
      onNewGame: () => this.navigate('#/setup'),
    });
    this.resultOverlay.classList.add('hidden');
    document.body.appendChild(this.resultOverlay);

    // Global keyboard listener
    window.addEventListener('keydown', this.handleKeyDown.bind(this));
    window.addEventListener('hashchange', () => this.route());

    // Initial routing
    if (!window.location.hash) {
      window.location.hash = '#/title';
    } else {
      this.route();
    }
  }

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

    // Hide any lingering result overlay
    this.resultOverlay.classList.add('hidden');

    // Mount screen
    this.screenContainer.innerHTML = '';
    const screenEl = this.screens[screenKey];
    this.screenContainer.appendChild(screenEl);
    this.currentScreenKey = screenKey;

    if (screenKey === 'game') {
      this.screens.game.updateState(this.gameState, this.humanPlayer, this.isAiThinking, this.legalMoves);
      await this.refreshPaths();
    }
  }

  async startGame({ opponent, humanPlayer, opponentInfo }) {
    this.opponentSpec = opponent;
    this.humanPlayer = humanPlayer;
    if (opponentInfo) this.opponentInfo = opponentInfo;
    this.lastStats = null;

    try {
      const data = await api.createGame(opponent, humanPlayer);
      this.gameId = data.game_id;
      this.gameState = data.state;

      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;

      this.screens.game.initGame(this.gameState, this.humanPlayer, this.opponentInfo);
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);

      this.navigate('#/game');
      await this.refreshPaths();

      // If AI moves first
      if (this.gameState.current !== this.humanPlayer) {
        await this.triggerAiMove();
      }
    } catch (err) {
      console.error('Failed to create game:', err);
      alert(`Could not start game: ${err.message}`);
    }
  }

  async restartGame() {
    await this.startGame({
      opponent: this.opponentSpec,
      humanPlayer: this.humanPlayer,
      opponentInfo: this.opponentInfo,
    });
  }

  async handlePawnMove(r, c) {
    if (this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    try {
      const move = { type: 'pawn', to: [r, c] };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished();
    } catch (err) {
      console.warn('Pawn move error:', err.message);
    }
  }

  async handleWallMove(r, c, o) {
    if (this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    try {
      const move = { type: 'wall', r, c, o };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished();
    } catch (err) {
      console.warn('Wall move error:', err.message);
    }
  }

  async onMoveFinished() {
    if (this.gameState.winner !== null) {
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, []);
      await this.refreshPaths();
      this.showGameOverModal();
      return;
    }

    // Refresh legal moves and paths
    const legalData = await api.getLegalMoves(this.gameId);
    this.legalMoves = legalData.moves;
    this.screens.game.updateState(this.gameState, this.humanPlayer, true, this.legalMoves);
    await this.refreshPaths();

    // Trigger AI move
    if (this.gameState.current !== this.humanPlayer) {
      await this.triggerAiMove();
    }
  }

  async triggerAiMove() {
    this.isAiThinking = true;
    this.screens.game.updateState(this.gameState, this.humanPlayer, true, []);

    try {
      const data = await api.getAiMove(this.gameId);
      if (data.move) {
        this.screens.game.addHistoryMove(1 - this.humanPlayer, data.move);
      }
      this.gameState = data.state;
      this.lastStats = data.stats;
      this.screens.game.setStats(data.stats);

      if (this.gameState.winner !== null) {
        this.screens.game.updateState(this.gameState, this.humanPlayer, false, []);
        await this.refreshPaths();
        this.showGameOverModal();
        return;
      }

      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;
    } catch (err) {
      console.error('AI move error:', err);
    } finally {
      this.isAiThinking = false;
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);
      await this.refreshPaths();
    }
  }

  async handleUndo() {
    if (this.isAiThinking || !this.gameId || (this.gameState && this.gameState.winner !== null)) return;

    try {
      const data = await api.undoMove(this.gameId);
      this.gameState = data.state;
      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);
      await this.refreshPaths();
    } catch (err) {
      console.warn('Undo error:', err.message);
    }
  }

  async refreshPaths() {
    if (!this.gameId) return;
    try {
      const data = await api.getPaths(this.gameId);
      this.screens.game.setPaths(data.paths);
    } catch (_) {}
  }

  showGameOverModal() {
    const history = this.screens.game.getMoveHistory();
    const lastMove = history.length > 0 ? history[history.length - 1].notation : 'e9#';
    const totalWallsPlaced = (this.gameState.h_walls ? this.gameState.h_walls.length : 0) + (this.gameState.v_walls ? this.gameState.v_walls.length : 0);
    const duration = this.screens.game.getElapsedSeconds();

    setTimeout(() => {
      this.resultOverlay.showResult({
        winner: this.gameState.winner,
        humanPlayer: this.humanPlayer,
        opponentInfo: this.opponentInfo,
        turnCount: this.gameState.turn_count,
        wallsPlaced: totalWallsPlaced,
        durationSeconds: duration,
        lastNotation: lastMove,
      });
    }, 600);
  }

  handleKeyDown(event) {
    const key = event.key.toUpperCase();

    if (this.currentScreenKey === 'title') {
      if (key === ' ' || key === 'ENTER') {
        this.navigate('#/setup');
      }
    } else if (this.currentScreenKey === 'setup') {
      if (key === 'ENTER') {
        this.screens.setup.querySelector('#btn-start')?.click();
      } else if (key === 'ESCAPE') {
        this.navigate('#/title');
      }
    } else if (this.currentScreenKey === 'game') {
      if (!this.resultOverlay.classList.contains('hidden')) {
        if (key === 'R') {
          this.restartGame();
        } else if (key === 'ESCAPE') {
          this.navigate('#/setup');
        }
        return;
      }

      if (key === 'R') {
        this.screens.game.toggleWallOrientation();
      } else if (key === 'P') {
        this.screens.game.togglePaths();
      } else if (key === 'U') {
        this.handleUndo();
      } else if (key === 'ESCAPE') {
        this.navigate('#/setup');
      }
    }
  }
}

// Initialize on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
  new QuoridorApp();
});
