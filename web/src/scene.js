/**
 * Three.js 3D Scene and Monolith Visualizer (owner: Priyanshu).
 */
import * as THREE from 'three';

// Palette constants (Monolith Design System)
export const PALETTE = {
  BONE: 0xEDE7DA,
  INK: 0x121212,
  VERMILION: 0xE8452C,
  COBALT: 0x2441D6,
  OCHRE: 0xD9A441,
};

const BOARD_SIZE = 9;
const TILE_SIZE = 1.0;
const GROOVE_WIDTH = 0.25;
const STEP = TILE_SIZE + GROOVE_WIDTH; // 1.25

export class QuoridorScene {
  constructor(container) {
    this.container = container;

    // Core Three.js components
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = false;
    this.container.appendChild(this.renderer.domElement);

    // Lighting (soft flat-shaded aesthetic)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.95);
    dirLight.position.set(6, 14, 8);
    this.scene.add(dirLight);

    // Screen Groups
    this.groups = {
      title: new THREE.Group(),
      setup: new THREE.Group(),
      game: new THREE.Group(),
      stats: new THREE.Group(),
      result: new THREE.Group(),
    };

    for (const group of Object.values(this.groups)) {
      this.scene.add(group);
      group.visible = false;
    }

    this.currentScreen = null;

    // Raycasting & Interaction
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(-999, -999);
    this.boardPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

    // Interaction states
    this.wallOrientation = 'H'; // 'H' or 'V'
    this.hoveredWall = null; // {r, c, o, legal}
    this.legalPawnMoves = []; // array of [r, c]
    this.legalWallMoves = new Set(); // set of "r,c,o"
    this.shortestPaths = null;
    this.showShortestPaths = false;

    // Callbacks
    this.onCellClick = null;
    this.onWallClick = null;

    // Build sub-scenes
    this._initTitleScene();
    this._initSetupScene();
    this._initGameScene();
    this._initStatsScene();
    this._initResultScene();

    // Event listeners
    window.addEventListener('resize', this._onResize.bind(this));
    this.renderer.domElement.addEventListener('pointermove', this._onPointerMove.bind(this));
    this.renderer.domElement.addEventListener('pointerdown', this._onPointerDown.bind(this));

    // Animation loop
    this.clock = new THREE.Clock();
    this._animate = this._animate.bind(this);
    requestAnimationFrame(this._animate);
  }

  /* -------------------------------------------------------------
   * 1. TITLE SCREEN: Giant rotating pawn monolith
   * ------------------------------------------------------------- */
  _initTitleScene() {
    const group = this.groups.title;

    // Base pedestal
    const baseGeo = new THREE.CylinderGeometry(0.9, 1.0, 0.35, 32);
    const baseMat = new THREE.MeshLambertMaterial({ color: PALETTE.INK });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = -1.2;

    // Slab monolith body
    const bodyGeo = new THREE.BoxGeometry(0.9, 3.2, 0.9);
    const bodyMat = new THREE.MeshLambertMaterial({ color: PALETTE.BONE });
    const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
    bodyMesh.position.y = 0.5;

    // Crown slab
    const crownGeo = new THREE.BoxGeometry(1.05, 0.3, 1.05);
    const crownMat = new THREE.MeshLambertMaterial({ color: PALETTE.OCHRE });
    const crownMesh = new THREE.Mesh(crownGeo, crownMat);
    crownMesh.position.y = 2.25;

    const monolith = new THREE.Group();
    monolith.add(baseMesh);
    monolith.add(bodyMesh);
    monolith.add(crownMesh);
    monolith.position.set(2.5, 0, 0);
    this.titleMonolith = monolith;

    group.add(monolith);
  }

  /* -------------------------------------------------------------
   * 2. SETUP SCREEN: Reactive height/color difficulty monolith
   * ------------------------------------------------------------- */
  _initSetupScene() {
    const group = this.groups.setup;

    this.setupMonolithMat = new THREE.MeshLambertMaterial({ color: PALETTE.BONE });
    this.setupMonolithGeo = new THREE.BoxGeometry(1.1, 2.5, 1.1);
    this.setupMonolithMesh = new THREE.Mesh(this.setupMonolithGeo, this.setupMonolithMat);

    const baseGeo = new THREE.BoxGeometry(1.4, 0.3, 1.4);
    const baseMat = new THREE.MeshLambertMaterial({ color: PALETTE.INK });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.position.y = -1.5;

    const container = new THREE.Group();
    container.add(base);
    container.add(this.setupMonolithMesh);
    container.position.set(1.8, 0, 0);
    this.setupContainer = container;

    group.add(container);
  }

  updateSetupMonolith(level, color = PALETTE.BONE) {
    // Height scales with difficulty level (1 to 4)
    const height = 1.2 + level * 0.8;
    this.setupMonolithMesh.geometry.dispose();
    this.setupMonolithMesh.geometry = new THREE.BoxGeometry(1.1, height, 1.1);
    this.setupMonolithMesh.position.y = -1.35 + height / 2;
    this.setupMonolithMat.color.setHex(color);
  }

  /* -------------------------------------------------------------
   * 3. GAME SCREEN: 9x9 Board with grooves, pawns, walls, markers
   * ------------------------------------------------------------- */
  _initGameScene() {
    const group = this.groups.game;

    // Underlay board base slab
    const baseWidth = 9 * STEP + 0.3;
    const baseGeo = new THREE.BoxGeometry(baseWidth, 0.3, baseWidth);
    const baseMat = new THREE.MeshLambertMaterial({ color: PALETTE.INK });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = -0.22;
    group.add(baseMesh);

    // 81 Cell Tiles
    this.cellTiles = [];
    const tileGeo = new THREE.BoxGeometry(TILE_SIZE, 0.15, TILE_SIZE);

    for (let r = 0; r < BOARD_SIZE; r++) {
      this.cellTiles[r] = [];
      for (let c = 0; c < BOARD_SIZE; c++) {
        let tileColor = PALETTE.BONE;
        if (r === 0) tileColor = 0xD9E2F8; // Subtle cobalt goal tint
        if (r === 8) tileColor = 0xF8D7D3; // Subtle vermilion goal tint

        const tileMat = new THREE.MeshLambertMaterial({ color: tileColor });
        const tileMesh = new THREE.Mesh(tileGeo, tileMat);
        const x = (c - 4) * STEP;
        const z = (r - 4) * STEP;
        tileMesh.position.set(x, 0, z);
        tileMesh.userData = { r, c, baseColor: tileColor };

        group.add(tileMesh);
        this.cellTiles[r][c] = tileMesh;
      }
    }

    // Pawns
    // Player 0 pawn (Cobalt capsule/cylinder)
    const p0Geo = new THREE.CylinderGeometry(0.38, 0.42, 0.75, 24);
    const p0Mat = new THREE.MeshLambertMaterial({ color: PALETTE.COBALT });
    this.pawn0 = new THREE.Mesh(p0Geo, p0Mat);
    this.pawn0.position.set(0, 0.45, 4 * STEP);
    group.add(this.pawn0);

    // Player 1 pawn (Vermilion capsule/cylinder)
    const p1Geo = new THREE.CylinderGeometry(0.38, 0.42, 0.75, 24);
    const p1Mat = new THREE.MeshLambertMaterial({ color: PALETTE.VERMILION });
    this.pawn1 = new THREE.Mesh(p1Geo, p1Mat);
    this.pawn1.position.set(0, 0.45, -4 * STEP);
    group.add(this.pawn1);

    // Walls container
    this.placedWallsGroup = new THREE.Group();
    group.add(this.placedWallsGroup);

    // Legal pawn destination markers group
    this.pawnMarkersGroup = new THREE.Group();
    group.add(this.pawnMarkersGroup);

    // Ghost wall for placement preview
    const ghostGeo = new THREE.BoxGeometry(2 * TILE_SIZE + GROOVE_WIDTH, 0.42, GROOVE_WIDTH * 0.9);
    this.ghostWallMat = new THREE.MeshLambertMaterial({
      color: PALETTE.OCHRE,
      transparent: true,
      opacity: 0.6,
    });
    this.ghostWall = new THREE.Mesh(ghostGeo, this.ghostWallMat);
    this.ghostWall.visible = false;
    group.add(this.ghostWall);

    // Board interaction plane for raycasting
    const planeGeo = new THREE.PlaneGeometry(baseWidth + 2, baseWidth + 2);
    const planeMat = new THREE.MeshBasicMaterial({ visible: false });
    this.interactPlane = new THREE.Mesh(planeGeo, planeMat);
    this.interactPlane.rotation.x = -Math.PI / 2;
    group.add(this.interactPlane);
  }

  /* -------------------------------------------------------------
   * 4. STATS SCREEN: 3D Log10(nodes) Column Visualizer
   * ------------------------------------------------------------- */
  _initStatsScene() {
    const group = this.groups.stats;
    group.position.x = 2.0;

    this.statsColumns = new THREE.Group();
    group.add(this.statsColumns);

    const baseGeo = new THREE.BoxGeometry(6, 0.2, 3);
    const baseMat = new THREE.MeshLambertMaterial({ color: 0x222222 });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.position.set(0, -1.2, 0);
    group.add(base);
  }

  updateStatsVisual(nodes, history = []) {
    while (this.statsColumns.children.length > 0) {
      const child = this.statsColumns.children[0];
      this.statsColumns.remove(child);
      if (child.geometry) child.geometry.dispose();
    }

    const logNodes = Math.max(0.5, Math.log10(Math.max(1, nodes)));
    const mainHeight = Math.min(3.8, logNodes * 0.85);

    // Main column
    const mainGeo = new THREE.BoxGeometry(1.2, mainHeight, 1.2);
    const mainMat = new THREE.MeshLambertMaterial({ color: PALETTE.OCHRE });
    const mainMesh = new THREE.Mesh(mainGeo, mainMat);
    mainMesh.position.set(0, -1.1 + mainHeight / 2, 0.5);
    this.statsColumns.add(mainMesh);

    // Past columns in history
    history.slice(-4).forEach((pastNodes, idx) => {
      const pLog = Math.max(0.3, Math.log10(Math.max(1, pastNodes)));
      const pHeight = Math.min(3.2, pLog * 0.7);
      const pGeo = new THREE.BoxGeometry(0.8, pHeight, 0.8);
      const pMat = new THREE.MeshLambertMaterial({ color: PALETTE.COBALT });
      const pMesh = new THREE.Mesh(pGeo, pMat);
      pMesh.position.set((idx - 1.5) * 1.3, -1.1 + pHeight / 2, -1.0);
      this.statsColumns.add(pMesh);
    });
  }

  /* -------------------------------------------------------------
   * 5. RESULT SCREEN: Spinning/rising winning pawn monolith
   * ------------------------------------------------------------- */
  _initResultScene() {
    const group = this.groups.result;
    group.position.x = 1.8;

    const winGeo = new THREE.BoxGeometry(1.2, 3.6, 1.2);
    this.winMat = new THREE.MeshLambertMaterial({ color: PALETTE.COBALT });
    this.winMonolith = new THREE.Mesh(winGeo, this.winMat);
    group.add(this.winMonolith);
  }

  setResultWinner(winner) {
    if (winner === 0) {
      this.winMat.color.setHex(PALETTE.COBALT);
    } else if (winner === 1) {
      this.winMat.color.setHex(PALETTE.VERMILION);
    } else {
      this.winMat.color.setHex(PALETTE.OCHRE);
    }
    this.winMonolith.position.set(0, -0.2, 0);
  }

  /* -------------------------------------------------------------
   * Screen Management & Camera Framing
   * ------------------------------------------------------------- */
  setScreen(screenName) {
    this.currentScreen = screenName;
    for (const [key, group] of Object.entries(this.groups)) {
      group.visible = (key === screenName);
    }

    if (screenName === 'title') {
      this.camera.position.set(0, 1.2, 7.5);
      this.camera.lookAt(0, 0.6, 0);
    } else if (screenName === 'setup') {
      this.camera.position.set(0, 1.0, 7.0);
      this.camera.lookAt(0, 0.2, 0);
    } else if (screenName === 'game') {
      // Tilted camera for 9x9 board: Player 0 at bottom, Player 1 at top
      this.camera.position.set(0, 10.5, 9.2);
      this.camera.lookAt(0, -0.4, 0.6);
    } else if (screenName === 'stats') {
      this.camera.position.set(0, 1.2, 7.0);
      this.camera.lookAt(0, 0.3, 0);
    } else if (screenName === 'result') {
      this.camera.position.set(0, 0.8, 6.5);
      this.camera.lookAt(0, 0, 0);
    }
  }

  /* -------------------------------------------------------------
   * Game State Synchronization
   * ------------------------------------------------------------- */
  syncGameState(state, legalMoves = []) {
    // 1. Update Pawns
    const [p0, p1] = state.pawns;
    const p0x = (p0[1] - 4) * STEP;
    const p0z = (p0[0] - 4) * STEP;
    const p1x = (p1[1] - 4) * STEP;
    const p1z = (p1[0] - 4) * STEP;

    this.pawn0.position.set(p0x, 0.45, p0z);
    this.pawn1.position.set(p1x, 0.45, p1z);

    // 2. Rebuild placed walls
    while (this.placedWallsGroup.children.length > 0) {
      const child = this.placedWallsGroup.children[0];
      this.placedWallsGroup.remove(child);
      if (child.geometry) child.geometry.dispose();
    }

    const wallThickness = GROOVE_WIDTH * 0.9;
    const wallLength = 2 * TILE_SIZE + GROOVE_WIDTH;
    const wallHeight = 0.42;

    const wallMat = new THREE.MeshLambertMaterial({ color: PALETTE.OCHRE });

    // H walls: spans columns c and c+1 in groove below row r
    for (const [r, c] of state.h_walls) {
      const geo = new THREE.BoxGeometry(wallLength, wallHeight, wallThickness);
      const mesh = new THREE.Mesh(geo, wallMat);
      const x = (c - 3.5) * STEP;
      const z = (r - 3.5) * STEP;
      mesh.position.set(x, wallHeight / 2 + 0.05, z);
      this.placedWallsGroup.add(mesh);
    }

    // V walls: spans rows r and r+1 in groove right of column c
    for (const [r, c] of state.v_walls) {
      const geo = new THREE.BoxGeometry(wallThickness, wallHeight, wallLength);
      const mesh = new THREE.Mesh(geo, wallMat);
      const x = (c - 3.5) * STEP;
      const z = (r - 3.5) * STEP;
      mesh.position.set(x, wallHeight / 2 + 0.05, z);
      this.placedWallsGroup.add(mesh);
    }

    // 3. Update legal moves lookup
    this.legalPawnMoves = [];
    this.legalWallMoves.clear();

    for (const m of legalMoves) {
      if (m.type === 'pawn') {
        this.legalPawnMoves.push(m.to);
      } else if (m.type === 'wall') {
        this.legalWallMoves.add(`${m.r},${m.c},${m.o}`);
      }
    }

    this._renderPawnDestinationMarkers();
    this._updateShortestPathsOverlay();
  }

  _renderPawnDestinationMarkers() {
    while (this.pawnMarkersGroup.children.length > 0) {
      const child = this.pawnMarkersGroup.children[0];
      this.pawnMarkersGroup.remove(child);
      if (child.geometry) child.geometry.dispose();
    }

    const markerGeo = new THREE.CylinderGeometry(0.25, 0.28, 0.12, 18);
    const markerMat = new THREE.MeshLambertMaterial({ color: PALETTE.COBALT });

    for (const [r, c] of this.legalPawnMoves) {
      const marker = new THREE.Mesh(markerGeo, markerMat);
      const x = (c - 4) * STEP;
      const z = (r - 4) * STEP;
      marker.position.set(x, 0.16, z);
      marker.userData = { r, c, isPawnDestination: true };
      this.pawnMarkersGroup.add(marker);
    }
  }

  setShortestPaths(paths) {
    this.shortestPaths = paths;
    this._updateShortestPathsOverlay();
  }

  toggleShortestPaths() {
    this.showShortestPaths = !this.showShortestPaths;
    this._updateShortestPathsOverlay();
    return this.showShortestPaths;
  }

  _updateShortestPathsOverlay() {
    // Reset all tile colors to default
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        const tile = this.cellTiles[r][c];
        tile.material.color.setHex(tile.userData.baseColor);
      }
    }

    if (!this.showShortestPaths || !this.shortestPaths) return;

    const [p0Path, p1Path] = this.shortestPaths;
    if (p0Path) {
      for (const [r, c] of p0Path) {
        if (r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE) {
          this.cellTiles[r][c].material.color.setHex(0xA3B8FA);
        }
      }
    }
    if (p1Path) {
      for (const [r, c] of p1Path) {
        if (r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE) {
          // If overlap, blend with ochre
          if (this.cellTiles[r][c].material.color.getHex() === 0xA3B8FA) {
            this.cellTiles[r][c].material.color.setHex(PALETTE.OCHRE);
          } else {
            this.cellTiles[r][c].material.color.setHex(0xF8A399);
          }
        }
      }
    }
  }

  toggleWallOrientation() {
    this.wallOrientation = (this.wallOrientation === 'H') ? 'V' : 'H';
    this._updateGhostWall();
  }

  /* -------------------------------------------------------------
   * Pointer Events & Raycasting Interactions
   * ------------------------------------------------------------- */
  _onPointerMove(event) {
    this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    if (this.currentScreen !== 'game') return;

    this.raycaster.setFromCamera(this.mouse, this.camera);

    // 1. Raycast against board plane for ghost wall positioning
    const intersects = this.raycaster.intersectObject(this.interactPlane);
    if (intersects.length > 0) {
      const pt = intersects[0].point;
      // Convert 3D world coord to nearest groove intersection (r, c)
      // center_x = (c - 3.5) * STEP => c = (pt.x / STEP) + 3.5
      // center_z = (r - 3.5) * STEP => r = (pt.z / STEP) + 3.5
      const rawC = (pt.x / STEP) + 3.5;
      const rawR = (pt.z / STEP) + 3.5;

      const c = Math.round(rawC);
      const r = Math.round(rawR);

      if (r >= 0 && r <= 7 && c >= 0 && c <= 7) {
        // Distance check from intersection
        const distX = Math.abs(rawC - c);
        const distZ = Math.abs(rawR - r);
        if (distX < 0.65 && distZ < 0.65) {
          const key = `${r},${c},${this.wallOrientation}`;
          const isLegal = this.legalWallMoves.has(key);
          this.hoveredWall = { r, c, o: this.wallOrientation, isLegal };
          this._updateGhostWall();
          return;
        }
      }
    }

    if (this.hoveredWall !== null) {
      this.hoveredWall = null;
      this.ghostWall.visible = false;
    }
  }

  _updateGhostWall() {
    if (!this.hoveredWall) {
      this.ghostWall.visible = false;
      return;
    }

    const { r, c, o, isLegal } = this.hoveredWall;
    const x = (c - 3.5) * STEP;
    const z = (r - 3.5) * STEP;

    const wallThickness = GROOVE_WIDTH * 0.9;
    const wallLength = 2 * TILE_SIZE + GROOVE_WIDTH;
    const wallHeight = 0.42;

    this.ghostWall.geometry.dispose();
    if (o === 'H') {
      this.ghostWall.geometry = new THREE.BoxGeometry(wallLength, wallHeight, wallThickness);
    } else {
      this.ghostWall.geometry = new THREE.BoxGeometry(wallThickness, wallHeight, wallLength);
    }

    this.ghostWall.position.set(x, wallHeight / 2 + 0.05, z);
    this.ghostWallMat.color.setHex(isLegal ? PALETTE.OCHRE : PALETTE.VERMILION);
    this.ghostWallMat.opacity = isLegal ? 0.65 : 0.45;
    this.ghostWall.visible = true;
  }

  _onPointerDown(event) {
    if (this.currentScreen !== 'game') return;

    this.raycaster.setFromCamera(this.mouse, this.camera);

    // 1. Check if clicked a legal pawn destination marker
    const markerHits = this.raycaster.intersectObjects(this.pawnMarkersGroup.children);
    if (markerHits.length > 0) {
      const hit = markerHits[0].object;
      if (hit.userData && hit.userData.isPawnDestination && this.onCellClick) {
        this.onCellClick(hit.userData.r, hit.userData.c);
        return;
      }
    }

    // 2. Check if clicked a cell tile that is a legal destination
    const tileHits = this.raycaster.intersectObjects(this.cellTiles.flat());
    if (tileHits.length > 0) {
      const tile = tileHits[0].object;
      const r = tile.userData.r;
      const c = tile.userData.c;
      const isLegalDestination = this.legalPawnMoves.some(([pr, pc]) => pr === r && pc === c);
      if (isLegalDestination && this.onCellClick) {
        this.onCellClick(r, c);
        return;
      }
    }

    // 3. Check if clicked hovered ghost wall
    if (this.hoveredWall && this.hoveredWall.isLegal && this.onWallClick) {
      const { r, c, o } = this.hoveredWall;
      this.onWallClick(r, c, o);
      this.hoveredWall = null;
      this.ghostWall.visible = false;
    }
  }

  _onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  _animate() {
    requestAnimationFrame(this._animate);

    const delta = this.clock.getDelta();
    const elapsed = this.clock.getElapsedTime();

    // Screen specific animations
    if (this.currentScreen === 'title' && this.titleMonolith) {
      this.titleMonolith.rotation.y += delta * 0.45;
      this.titleMonolith.position.y = Math.sin(elapsed * 1.5) * 0.08;
    } else if (this.currentScreen === 'setup' && this.setupContainer) {
      this.setupContainer.rotation.y = Math.sin(elapsed * 0.8) * 0.25;
    } else if (this.currentScreen === 'result' && this.winMonolith) {
      this.winMonolith.rotation.y += delta * 1.2;
      this.winMonolith.position.y = Math.sin(elapsed * 2.0) * 0.15;
    }

    this.renderer.render(this.scene, this.camera);
  }
}

