const UNICODE = {
  wK: '♔', wQ: '♕', wR: '♖', wB: '♗', wN: '♘', wP: '♙',
  bK: '♚', bQ: '♛', bR: '♜', bB: '♝', bN: '♞', bP: '♟',
};

function initBoard() {
  const board = Array.from({ length: 8 }, () => Array(8).fill(null));
  board[0] = ['bR', 'bN', 'bB', 'bQ', 'bK', 'bB', 'bN', 'bR'];
  board[1] = Array(8).fill('bP');
  board[6] = Array(8).fill('wP');
  board[7] = ['wR', 'wN', 'wB', 'wQ', 'wK', 'wB', 'wN', 'wR'];
  return board;
}

const KNIGHT_DELTAS = [[2,1],[2,-1],[-2,1],[-2,-1],[1,2],[1,-2],[-1,2],[-1,-2]];
const DIAG_DIRS = [[-1,-1],[-1,1],[1,-1],[1,1]];
const ORTHO_DIRS = [[-1,0],[1,0],[0,-1],[0,1]];

class ChessApp {
  constructor() {
    this.board = initBoard();
    this.turn = 'w';
    this.selected = null;
    this.moveHighlights = [];
    this.gameOver = false;
    this.aiEnabled = { w: false, b: false };
    this.kingMoved = { w: false, b: false };
    this.rookMoved = { w: { a: false, h: false }, b: { a: false, h: false } };
    this.timers = { w: 0, b: 0 };
    this.timerRunning = false;
    this.pendingPromotion = null; // {sr,sc,tr,tc,color}

    this.boardEl = document.getElementById('board');
    this.statusEl = document.getElementById('status');
    this.whiteTimeEl = document.getElementById('whiteTime');
    this.blackTimeEl = document.getElementById('blackTime');
    this.promoModal = document.getElementById('promoModal');

    document.getElementById('aiWhiteBtn').addEventListener('click', () => this.toggleAi('w'));
    document.getElementById('aiBlackBtn').addEventListener('click', () => this.toggleAi('b'));
    document.getElementById('forfeitBtn').addEventListener('click', () => this.forfeit());
    document.getElementById('resetBtn').addEventListener('click', () => this.resetGame());
    document.getElementById('startTimerBtn').addEventListener('click', () => this.startTimer());
    document.getElementById('pauseTimerBtn').addEventListener('click', () => { this.timerRunning = false; });
    this.promoModal.querySelectorAll('[data-piece]').forEach((btn) => {
      btn.addEventListener('click', () => this.resolvePromotion(btn.dataset.piece));
    });

    this.buildSquares();
    this.drawBoard();
    this.updateTimerLabels();
  }

  buildSquares() {
    this.boardEl.innerHTML = '';
    this.squareEls = [];
    for (let r = 0; r < 8; r++) {
      const row = [];
      for (let c = 0; c < 8; c++) {
        const sq = document.createElement('div');
        sq.className = `square ${(r + c) % 2 === 0 ? 'light' : 'dark'}`;
        sq.dataset.row = r;
        sq.dataset.col = c;
        sq.addEventListener('click', () => this.onClick(r, c));
        this.boardEl.appendChild(sq);
        row.push(sq);
      }
      this.squareEls.push(row);
    }
  }

  drawBoard() {
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const sq = this.squareEls[r][c];
        sq.innerHTML = '';
        sq.classList.toggle('selected', !!this.selected && this.selected[0] === r && this.selected[1] === c);
        const piece = this.board[r][c];
        if (piece) {
          const span = document.createElement('span');
          span.className = `piece ${piece[0] === 'w' ? 'white' : 'black'}`;
          span.textContent = UNICODE[piece] || '?';
          sq.appendChild(span);
        }
        if (this.moveHighlights.some(([hr, hc]) => hr === r && hc === c)) {
          const dot = document.createElement('span');
          dot.className = 'dot';
          sq.appendChild(dot);
        }
      }
    }
  }

  onClick(r, c) {
    if (this.gameOver || this.pendingPromotion) return;
    if (this.aiEnabled[this.turn]) return;

    const piece = this.board[r][c];
    if (!this.selected) {
      if (piece && piece[0] === this.turn) {
        this.selected = [r, c];
        this.moveHighlights = this.legalMovesFor(r, c);
        this.drawBoard();
      }
      return;
    }

    const [sr, sc] = this.selected;
    const isLegalTarget = this.moveHighlights.some(([hr, hc]) => hr === r && hc === c);
    if (isLegalTarget) {
      this.selected = null;
      this.moveHighlights = [];
      this.makeMove(sr, sc, r, c);
    } else if (piece && piece[0] === this.turn) {
      this.selected = [r, c];
      this.moveHighlights = this.legalMovesFor(r, c);
      this.drawBoard();
    } else {
      this.selected = null;
      this.moveHighlights = [];
      this.drawBoard();
    }
  }

  makeMove(sr, sc, tr, tc) {
    const piece = this.board[sr][sc];
    this.board[tr][tc] = piece;
    this.board[sr][sc] = null;

    if (piece && piece[1] === 'P' && ((piece[0] === 'w' && tr === 0) || (piece[0] === 'b' && tr === 7))) {
      this.pendingPromotion = { tr, tc, color: piece[0] };
      this.drawBoard();
      this.promoModal.classList.remove('hidden');
      return;
    }

    this.finalizeMove(piece, sr, sc, tr, tc);
  }

  resolvePromotion(pieceLetter) {
    const { tr, tc, color } = this.pendingPromotion;
    this.board[tr][tc] = color + pieceLetter;
    this.promoModal.classList.add('hidden');
    this.pendingPromotion = null;
    this.finalizeMove(color + 'P', null, null, tr, tc);
  }

  finalizeMove(piece, sr, sc, tr, tc) {
    if (piece && piece[1] === 'K') {
      const color = piece[0];
      this.kingMoved[color] = true;
      if (sc !== null && Math.abs(tc - sc) === 2) {
        if (tc > sc) {
          const rr = tr, rc = 7, newC = 5;
          if (this.board[rr][rc] && this.board[rr][rc][1] === 'R') {
            this.board[rr][newC] = this.board[rr][rc];
            this.board[rr][rc] = null;
            this.rookMoved[color].h = true;
          }
        } else {
          const rr = tr, rc = 0, newC = 3;
          if (this.board[rr][rc] && this.board[rr][rc][1] === 'R') {
            this.board[rr][newC] = this.board[rr][rc];
            this.board[rr][rc] = null;
            this.rookMoved[color].a = true;
          }
        }
      }
    }
    if (piece && piece[1] === 'R' && sr !== null) {
      const color = piece[0];
      if (color === 'w') {
        if (sr === 7 && sc === 0) this.rookMoved.w.a = true;
        if (sr === 7 && sc === 7) this.rookMoved.w.h = true;
      } else {
        if (sr === 0 && sc === 0) this.rookMoved.b.a = true;
        if (sr === 0 && sc === 7) this.rookMoved.b.h = true;
      }
    }

    this.updateTimerLabels();
    this.drawBoard();
    this.switchTurn();
  }

  switchTurn() {
    this.turn = this.turn === 'w' ? 'b' : 'w';
    this.statusEl.textContent = this.turn === 'w' ? 'White to move' : 'Black to move';
    if (!this.gameOver && this.aiEnabled[this.turn]) {
      setTimeout(() => this.doAiMove(), 300);
    }
  }

  // ── move generation & legality ─────────────────────────────
  legalMovesFor(r, c) {
    const piece = this.board[r][c];
    if (!piece) return [];
    const color = piece[0];
    const moves = this.generatePseudoMoves(r, c);
    const legal = [];
    for (const [tr, tc] of moves) {
      const saved = this.board[tr][tc];
      this.board[tr][tc] = this.board[r][c];
      this.board[r][c] = null;
      const kingSafe = !this.isInCheck(color);
      this.board[r][c] = this.board[tr][tc];
      this.board[tr][tc] = saved;
      if (kingSafe) legal.push([tr, tc]);
    }
    return legal;
  }

  isInCheck(color) {
    let kingSq = null;
    for (let r = 0; r < 8 && !kingSq; r++) {
      for (let c = 0; c < 8; c++) {
        if (this.board[r][c] === color + 'K') { kingSq = [r, c]; break; }
      }
    }
    if (!kingSq) return true;
    const opp = color === 'w' ? 'b' : 'w';
    const attacked = this.squaresAttackedBy(opp);
    return attacked.has(`${kingSq[0]},${kingSq[1]}`);
  }

  squaresAttackedBy(color) {
    const attacked = new Set();
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = this.board[r][c];
        if (p && p[0] === color) {
          for (const sq of this.pseudoAttacksFor(r, c, p[1], color)) attacked.add(sq);
        }
      }
    }
    return attacked;
  }

  pseudoAttacksFor(r, c, typ, color) {
    const res = new Set();
    if (typ === 'P') {
      const d = color === 'w' ? -1 : 1;
      for (const dc of [-1, 1]) {
        const rr = r + d, cc = c + dc;
        if (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) res.add(`${rr},${cc}`);
      }
      return res;
    }
    if (typ === 'N') {
      for (const [dr, dc] of KNIGHT_DELTAS) {
        const rr = r + dr, cc = c + dc;
        if (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) res.add(`${rr},${cc}`);
      }
      return res;
    }
    if (typ === 'K') {
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (dr === 0 && dc === 0) continue;
          const rr = r + dr, cc = c + dc;
          if (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) res.add(`${rr},${cc}`);
        }
      }
      return res;
    }
    let dirs = [];
    if (typ === 'B' || typ === 'Q') dirs = dirs.concat(DIAG_DIRS);
    if (typ === 'R' || typ === 'Q') dirs = dirs.concat(ORTHO_DIRS);
    for (const [dr, dc] of dirs) {
      let rr = r + dr, cc = c + dc;
      while (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) {
        res.add(`${rr},${cc}`);
        if (this.board[rr][cc] !== null) break;
        rr += dr; cc += dc;
      }
    }
    return res;
  }

  generatePseudoMoves(r, c) {
    const piece = this.board[r][c];
    if (!piece) return [];
    const color = piece[0], typ = piece[1];
    const moves = [];

    if (typ === 'P') {
      const direction = color === 'w' ? -1 : 1;
      let rr = r + direction;
      if (rr >= 0 && rr < 8 && this.board[rr][c] === null) {
        moves.push([rr, c]);
        const startRow = color === 'w' ? 6 : 1;
        const rr2 = r + 2 * direction;
        if (r === startRow && rr2 >= 0 && rr2 < 8 && this.board[rr2][c] === null) moves.push([rr2, c]);
      }
      for (const dc of [-1, 1]) {
        const cc = c + dc;
        const rrc = r + direction;
        if (rrc >= 0 && rrc < 8 && cc >= 0 && cc < 8) {
          const target = this.board[rrc][cc];
          if (target && target[0] !== color) moves.push([rrc, cc]);
        }
      }
      return moves;
    }

    if (typ === 'N') {
      for (const [dr, dc] of KNIGHT_DELTAS) {
        const rr2 = r + dr, cc2 = c + dc;
        if (rr2 >= 0 && rr2 < 8 && cc2 >= 0 && cc2 < 8) {
          const t = this.board[rr2][cc2];
          if (!t || t[0] !== color) moves.push([rr2, cc2]);
        }
      }
      return moves;
    }

    if (typ === 'B' || typ === 'R' || typ === 'Q') {
      let dirs = [];
      if (typ === 'B' || typ === 'Q') dirs = dirs.concat(DIAG_DIRS);
      if (typ === 'R' || typ === 'Q') dirs = dirs.concat(ORTHO_DIRS);
      for (const [dr, dc] of dirs) {
        let rr = r + dr, cc = c + dc;
        while (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) {
          const t = this.board[rr][cc];
          if (t === null) {
            moves.push([rr, cc]);
          } else {
            if (t[0] !== color) moves.push([rr, cc]);
            break;
          }
          rr += dr; cc += dc;
        }
      }
      return moves;
    }

    if (typ === 'K') {
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (dr === 0 && dc === 0) continue;
          const rr = r + dr, cc = c + dc;
          if (rr >= 0 && rr < 8 && cc >= 0 && cc < 8) {
            const t = this.board[rr][cc];
            if (!t || t[0] !== color) moves.push([rr, cc]);
          }
        }
      }
      if (!this.kingMoved[color] && !this.isInCheck(color)) {
        const opp = color === 'w' ? 'b' : 'w';
        const attacked = this.squaresAttackedBy(opp);
        const rookK = this.board[r][7];
        if (rookK === color + 'R' && !this.rookMoved[color].h) {
          if (this.board[r][c + 1] === null && this.board[r][c + 2] === null) {
            if (!attacked.has(`${r},${c + 1}`) && !attacked.has(`${r},${c + 2}`)) moves.push([r, c + 2]);
          }
        }
        const rookQ = this.board[r][0];
        if (rookQ === color + 'R' && !this.rookMoved[color].a) {
          if (this.board[r][c - 1] === null && this.board[r][c - 2] === null && this.board[r][c - 3] === null) {
            if (!attacked.has(`${r},${c - 1}`) && !attacked.has(`${r},${c - 2}`)) moves.push([r, c - 2]);
          }
        }
      }
      return moves;
    }

    return moves;
  }

  // ── AI ──────────────────────────────────────────────────────
  toggleAi(color) {
    this.aiEnabled[color] = !this.aiEnabled[color];
    const btn = document.getElementById(color === 'w' ? 'aiWhiteBtn' : 'aiBlackBtn');
    const label = color === 'w' ? 'White' : 'Black';
    btn.textContent = `${this.aiEnabled[color] ? 'Disable' : 'Enable'} AI: ${label}`;
    if (this.aiEnabled[color] && this.turn === color && !this.gameOver) {
      setTimeout(() => this.doAiMove(), 300);
    }
  }

  gatherAllLegalMoves(color) {
    const moves = [];
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = this.board[r][c];
        if (p && p[0] === color) {
          for (const [tr, tc] of this.legalMovesFor(r, c)) moves.push([r, c, tr, tc]);
        }
      }
    }
    return moves;
  }

  doAiMove() {
    if (this.gameOver || !this.aiEnabled[this.turn]) return;
    const moves = this.gatherAllLegalMoves(this.turn);
    if (moves.length === 0) {
      this.gameOver = true;
      this.statusEl.textContent = 'No legal moves';
      return;
    }
    const captures = moves.filter(([, , tr, tc]) => this.board[tr][tc] !== null && this.board[tr][tc][0] !== this.turn);
    const pool = captures.length ? captures : moves;
    const [sr, sc, tr, tc] = pool[Math.floor(Math.random() * pool.length)];
    this.makeMove(sr, sc, tr, tc);
  }

  // ── timer ───────────────────────────────────────────────────
  startTimer() {
    const minutes = Math.max(1, parseInt(document.getElementById('timerMinutes').value, 10) || 10);
    const secs = minutes * 60;
    if (this.timers.w === 0 && this.timers.b === 0) {
      this.timers.w = secs;
      this.timers.b = secs;
    }
    this.timerRunning = true;
    this.updateTimerLabels();
    setTimeout(() => this.timerTick(), 1000);
  }

  timerTick() {
    if (!this.timerRunning || this.gameOver) return;
    this.timers[this.turn] -= 1;
    if (this.timers[this.turn] <= 0) {
      this.timers[this.turn] = 0;
      this.timerRunning = false;
      const winner = this.turn === 'b' ? 'White' : 'Black';
      this.gameOver = true;
      this.statusEl.textContent = `${winner} wins (time)`;
      this.updateTimerLabels();
      alert(`${winner} wins on time`);
      return;
    }
    this.updateTimerLabels();
    setTimeout(() => this.timerTick(), 1000);
  }

  updateTimerLabels() {
    this.whiteTimeEl.textContent = `White: ${this.formatSeconds(this.timers.w)}`;
    this.blackTimeEl.textContent = `Black: ${this.formatSeconds(this.timers.b)}`;
  }

  formatSeconds(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }

  // ── controls ────────────────────────────────────────────────
  forfeit() {
    if (this.gameOver) return;
    const winner = this.turn === 'b' ? 'White' : 'Black';
    this.gameOver = true;
    this.statusEl.textContent = `${winner} wins (forfeit)`;
    alert(`${winner} wins by forfeit`);
  }

  resetGame() {
    this.board = initBoard();
    this.turn = 'w';
    this.selected = null;
    this.moveHighlights = [];
    this.gameOver = false;
    this.pendingPromotion = null;
    this.promoModal.classList.add('hidden');
    this.statusEl.textContent = 'White to move';
    this.kingMoved = { w: false, b: false };
    this.rookMoved = { w: { a: false, h: false }, b: { a: false, h: false } };
    this.timerRunning = false;
    this.timers = { w: 0, b: 0 };
    this.updateTimerLabels();
    this.drawBoard();
    if (this.aiEnabled[this.turn]) setTimeout(() => this.doAiMove(), 300);
  }
}

document.addEventListener('DOMContentLoaded', () => { window.app = new ChessApp(); });
