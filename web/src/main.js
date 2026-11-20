// Application controller: manages client-side view routing, keyboard shortcuts, and game loop orchestration.

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
    this.boardSize = 9;
    this.numPlayers = 2;
    this.lastStartConfig = null;
    this.opponentInfo = null;
    this.opponentInfos = [];
    this.legalMoves = [];
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
      onReview: () => {},
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

  async startGame(cfg) {
    this.lastStartConfig = cfg;
    this.boardSize = cfg.boardSize || 9;
    this.numPlayers = cfg.numPlayers || 2;
    this.humanPlayer = cfg.humanPlayer !== undefined ? cfg.humanPlayer : 0;
    this.opponentInfo = cfg.opponentInfo || null;
    this.opponentInfos = cfg.opponentInfos || [];

    try {
      const data = await api.createGame({
        boardSize: this.boardSize,
        numPlayers: this.numPlayers,
        humanPlayer: this.humanPlayer,
        opponent: cfg.opponent,
        opponents: cfg.opponents,
      });

      this.gameId = data.game_id;
      this.gameState = data.state;

      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;

      this.screens.game.initGame(this.gameState, this.humanPlayer, this.opponentInfo, this.opponentInfos);
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);

      this.navigate('#/game');
      await this.refreshPaths();

      if (this.gameState.current !== this.humanPlayer) {
        await this.triggerAiSequence();
      }
    } catch (err) {
      console.error('Failed to create game:', err);
      alert(`Could not start game: ${err.message}`);
    }
  }

  async restartGame() {
    if (this.lastStartConfig) {
      await this.startGame(this.lastStartConfig);
    }
  }

  async handlePawnMove(r, c) {
    if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null || this.gameState.no_winner) return;
    if (this.gameState.current !== this.humanPlayer) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight(true);
    try {
      const move = { type: 'pawn', to: [r, c] };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished(data.ranks);
    } catch (err) {
      console.warn('Pawn move error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight(false);
    }
  }

  async handleWallMove(r, c, o) {
    if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null || this.gameState.no_winner) return;
    if (this.gameState.current !== this.humanPlayer) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight(true);
    try {
      const move = { type: 'wall', r, c, o };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.gameState = data.state;
      await this.onMoveFinished(data.ranks);
    } catch (err) {
      console.warn('Wall move error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight(false);
    }
  }

  async handlePassMove() {
    if (this.isRequestInFlight || this.isAiThinking || !this.gameState) return;
    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight(true);
    try {
      const move = { type: 'pass' };
      const data = await api.makeMove(this.gameId, move);
      this.screens.game.addHistoryMove(this.humanPlayer, move);
      this.screens.game.showPassAlert('You had no legal moves. Turn skipped.');
      this.gameState = data.state;
      await this.onMoveFinished(data.ranks);
    } catch (err) {
      console.warn('Pass move error:', err.message);
    } finally {
      this.isRequestInFlight = false;
      this.screens.game.setRequestInFlight(false);
    }
  }

  async onMoveFinished(ranks = null) {
    if (this.gameState.winner !== null || this.gameState.no_winner) {
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, []);
      await this.refreshPaths();
      this.showGameOverModal(ranks);
      return;
    }

    const legalData = await api.getLegalMoves(this.gameId);
    this.legalMoves = legalData.moves;

    // Check if human must pass
    if (this.gameState.current === this.humanPlayer && this.legalMoves.length === 1 && this.legalMoves[0].type === 'pass') {
      await this.handlePassMove();
      return;
    }

    this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);
    await this.refreshPaths();

    if (this.gameState.current !== this.humanPlayer) {
      await this.triggerAiSequence();
    }
  }

  async triggerAiSequence() {
    while (
      this.gameState &&
      this.gameState.winner === null &&
      !this.gameState.no_winner &&
      this.gameState.current !== this.humanPlayer
    ) {
      this.isAiThinking = true;
      this.screens.game.updateState(this.gameState, this.humanPlayer, true, []);

      // Pause 400ms between AI turns so moves are clearly visible
      await new Promise((r) => setTimeout(r, 400));

      try {
        const data = await api.getAiMove(this.gameId);
        if (data.move) {
          this.screens.game.addHistoryMove(data.mover, data.move);
          if (data.move.type === 'pass') {
            this.screens.game.showPassAlert('No legal move, turn skipped.');
          }
        }
        this.gameState = data.state;
        this.screens.game.updateState(this.gameState, this.humanPlayer, true, []);
        await this.refreshPaths();

        if (data.is_terminal || this.gameState.winner !== null || this.gameState.no_winner) {
          this.isAiThinking = false;
          this.showGameOverModal(data.ranks);
          return;
        }
      } catch (err) {
        console.error('AI move sequence error:', err);
        break;
      }
    }

    this.isAiThinking = false;
    if (this.gameState && this.gameState.winner === null && !this.gameState.no_winner) {
      const legalData = await api.getLegalMoves(this.gameId);
      this.legalMoves = legalData.moves;
      this.screens.game.updateState(this.gameState, this.humanPlayer, false, this.legalMoves);

      // Check if human must pass
      if (this.legalMoves.length === 1 && this.legalMoves[0].type === 'pass') {
        await this.handlePassMove();
      }
    }
  }

  async handleUndo() {
    if (this.isRequestInFlight || this.isAiThinking || !this.gameId || (this.gameState && (this.gameState.winner !== null || this.gameState.no_winner))) return;

    this.isRequestInFlight = true;
    this.screens.game.setRequestInFlight(true);
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
      this.screens.game.setRequestInFlight(false);
    }
  }

  async refreshPaths() {
    if (!this.gameId) return;
    try {
      const data = await api.getPaths(this.gameId);
      this.screens.game.setPaths(data.paths);
    } catch (_) {}
  }

  showGameOverModal(ranks = null) {
    const totalWallsPlaced =
      (this.gameState.h_walls ? this.gameState.h_walls.length : 0) +
      (this.gameState.v_walls ? this.gameState.v_walls.length : 0);
    const duration = this.screens.game.getElapsedSeconds();

    const playerNames = { 0: 'You' };
    if (this.numPlayers === 4 && this.opponentInfos.length > 0) {
      this.opponentInfos.forEach((o) => {
        playerNames[o.seat] = o.name;
      });
    } else if (this.opponentInfo) {
      playerNames[2] = this.opponentInfo.name;
    }

    setTimeout(() => {
      this.resultOverlay.showResult({
        winner: this.gameState.winner,
        noWinner: this.gameState.no_winner,
        ranks: ranks,
        numPlayers: this.numPlayers,
        humanPlayer: this.humanPlayer,
        turnCount: this.gameState.turn_count,
        wallsPlaced: totalWallsPlaced,
        durationSeconds: duration,
        playerNames,
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
        if (this.isRequestInFlight || this.isAiThinking || !this.gameState || this.gameState.winner !== null || this.gameState.no_winner) return;
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
