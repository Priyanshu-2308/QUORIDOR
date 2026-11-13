// router and controller for the screens

import * as api from './api.js';
import { createSetupScreen } from './screens/setup.js';
import { createGameScreen } from './screens/game.js';
import { createResultScreen } from './screens/result.js';

class QuoridorApp {
  constructor() {
    this.screenContainer = document.getElementById('screen-container');

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
    this.isRequestInFlight = false;
    this.currentScreenKey = null;

    this.screens = {
      setup: createSetupScreen({
        onStart: (cfg) => this.startGame(cfg),
        onBack: () => this.navigate('#/setup'),
      }),
      game: createGameScreen({
        onPawnMove: (r, c) => this.handlePawnMove(r, c),
        onWallMove: (r, c, o) => this.handleWallMove(r, c, o),
        onUndo: () => this.handleUndo(),
        onTogglePaths: () => this.refreshPaths(),
        onQuit: () => this.navigate('#/setup'),
      }),
    };

    this.resultOverlay = createResultScreen({
      onRematch: () => this.restartGame(),
      onReview: () => {
      },
      onNewGame: () => this.navigate('#/setup'),
    });
    this.resultOverlay.classList.add('hidden');
    document.body.appendChild(this.resultOverlay);

    window.addEventListener('keydown', this.handleKeyDown.bind(this));
    window.addEventListener('hashchange', () => this.route());

    if (!window.location.hash || window.location.hash === '#' || window.location.hash === '#/') {
      window.location.hash = '#/setup';
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
    const hash = window.location.hash || '#/setup';
    let screenKey = hash.replace('#/', '').split('?')[0] || 'setup';

    if (screenKey !== 'setup' && screenKey !== 'game') {
      screenKey = 'setup';
    }

    if (screenKey === 'game' && !this.gameId) {
      this.navigate('#/setup');
      return;
    }

    if (this.currentScreenKey === screenKey) return;

    this.resultOverlay.classList.add('hidden');

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
    if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight?.(true);
    try {
      const move = { type: 'pawn', to: [r, c] };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished();
    } catch (err) {
      console.warn('Pawn move error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight?.(false);
    }
  }

  async handleWallMove(r, c, o) {
    if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
    if (this.gameState.current !== this.humanPlayer) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight?.(true);
    try {
      const move = { type: 'wall', r, c, o };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished();
    } catch (err) {
      console.warn('Wall move error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight?.(false);
    }
  }

  async onMoveFinished() {
    if (this.gameState.winner !== null) {
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, []);
      await this.refreshPaths();
      this.showGameOverModal();
      return;
    }

    const legalData = await api.getLegalMoves(this.gameId);
    this.legalMoves = legalData.moves;
    this.screens.game.updateState(this.gameState, this.humanPlayer, true, this.legalMoves);
    await this.refreshPaths();

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
    if (this.isRequestInFlight || this.isAiThinking || !this.gameId || (this.gameState && this.gameState.winner !== null)) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight?.(true);
    try {
      const data = await api.undoMove(this.gameId);
      this.gameState = data.state;
      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);
      await this.refreshPaths();
    } catch (err) {
      console.warn('Undo error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight?.(false);
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
    }, 500);
  }

  handleKeyDown(event) {
    if (this.currentScreenKey === 'setup') {
      if (event.key === 'Enter') {
        this.screens.setup.querySelector('#btn-start')?.click();
      }
      return;
    }

    if (this.currentScreenKey === 'game') {
      if (!this.resultOverlay.classList.contains('hidden')) {
        const key = event.key.toUpperCase();
        if (key === 'R') {
          this.restartGame();
        } else if (event.key === 'Escape') {
          this.navigate('#/setup');
        }
        return;
      }

      const arrowMap = {
        ArrowUp: 'up',
        ArrowDown: 'down',
        ArrowLeft: 'left',
        ArrowRight: 'right',
      };
      const dir = arrowMap[event.key];
      if (dir) {
        event.preventDefault();
        if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return;
        if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null) return;
        if (this.gameState.current !== this.humanPlayer) return;

        this.screens.game.moveByArrow(dir);
        return;
      }

      const key = event.key.toUpperCase();
      if (event.key === 'Escape') {
        const cancelled = this.screens.game.cancelChoice?.();
        if (!cancelled) {
          this.navigate('#/setup');
        }
      } else if (key === 'R') {
        this.screens.game.cancelChoice?.();
        this.screens.game.toggleWallOrientation();
      } else if (key === 'P') {
        this.screens.game.cancelChoice?.();
        this.screens.game.togglePaths();
      } else if (key === 'U') {
        this.screens.game.cancelChoice?.();
        this.handleUndo();
      } else {
        this.screens.game.cancelChoice?.();
      }
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  new QuoridorApp();
});
