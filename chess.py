import tkinter as tk
import random
from tkinter import simpledialog, messagebox

# Unicode chess pieces
UNICODE = {
    'wK': '\u2654', 'wQ': '\u2655', 'wR': '\u2656', 'wB': '\u2657', 'wN': '\u2658', 'wP': '\u2659',
    'bK': '\u265A', 'bQ': '\u265B', 'bR': '\u265C', 'bB': '\u265D', 'bN': '\u265E', 'bP': '\u265F',
}


def init_board():
    # 8x8 board, rows 0..7 top->bottom
    board = [[None for _ in range(8)] for _ in range(8)]
    # Black back rank
    back_black = ['bR', 'bN', 'bB', 'bQ', 'bK', 'bB', 'bN', 'bR']
    board[0] = back_black[:]
    board[1] = ['bP'] * 8
    # empty ranks
    for r in range(2, 6):
        board[r] = [None] * 8
    # White pawns and back rank
    board[6] = ['wP'] * 8
    back_white = ['wR', 'wN', 'wB', 'wQ', 'wK', 'wB', 'wN', 'wR']
    board[7] = back_white[:]
    return board


class ChessApp:
    def __init__(self, root):
        self.root = root
        root.title('Chess — Playable Setup')
        self.board = init_board()
        self.turn = 'w'  # 'w' or 'b'
        self.selected = None  # (r,c)
        self.move_highlights = []

        self.square_size = 64
        self.canvas = tk.Canvas(root, width=8*self.square_size, height=8*self.square_size)
        self.canvas.pack()
        self.canvas.bind('<Button-1>', self.on_click)

        self.status = tk.Label(root, text="White to move", font=('Arial', 14))
        self.status.pack(fill='x')

        # game and AI state
        self.game_over = False
        # allow AI per color
        self.ai_enabled = {'w': False, 'b': False}

        # moved flags for castling
        self.king_moved = {'w': False, 'b': False}
        self.rook_moved = {'w': {'a': False, 'h': False}, 'b': {'a': False, 'h': False}}

        # control buttons: toggle AI for white/black, forfeit, reset
        ctl = tk.Frame(root)
        ctl.pack(fill='x', pady=4)
        self.ai_w_btn = tk.Button(ctl, text='Enable AI: White', command=lambda: self.toggle_ai('w'))
        self.ai_w_btn.pack(side='left', padx=4)
        self.ai_b_btn = tk.Button(ctl, text='Enable AI: Black', command=lambda: self.toggle_ai('b'))
        self.ai_b_btn.pack(side='left', padx=4)
        self.forfeit_btn = tk.Button(ctl, text='Forfeit', command=self.forfeit)
        self.forfeit_btn.pack(side='left', padx=4)
        self.reset_btn = tk.Button(ctl, text='Reset', command=self.reset_game)
        self.reset_btn.pack(side='left', padx=4)

        # Timer controls
        tctl = tk.Frame(root)
        tctl.pack(fill='x', pady=2)
        tk.Label(tctl, text='Timer (minutes):').pack(side='left')
        self.timer_spin = tk.Spinbox(tctl, from_=1, to=60, width=4)
        self.timer_spin.pack(side='left', padx=4)
        self.start_timer_btn = tk.Button(tctl, text='Start Timer', command=self.start_timer)
        self.start_timer_btn.pack(side='left', padx=4)
        self.pause_timer_btn = tk.Button(tctl, text='Pause Timer', command=self.pause_timer)
        self.pause_timer_btn.pack(side='left', padx=4)

        # Timer display
        self.timers = {'w': 0, 'b': 0}
        self.timer_running = False
        timebar = tk.Frame(root)
        timebar.pack(fill='x')
        self.white_time_label = tk.Label(timebar, text='White: 00:00')
        self.white_time_label.pack(side='left', padx=8)
        self.black_time_label = tk.Label(timebar, text='Black: 00:00')
        self.black_time_label.pack(side='left', padx=8)

        self.draw_board()

    def draw_board(self):
        self.canvas.delete('all')
        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                fill = '#EEEED2' if (r + c) % 2 == 0 else '#769656'
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline='')
                piece = self.board[r][c]
                if piece:
                    ch = UNICODE.get(piece, '?')
                    self.canvas.create_text(x1 + self.square_size//2, y1 + self.square_size//2,
                                            text=ch, font=('Segoe UI Symbol', 36))
        # redraw highlights on top
        for (r, c) in self.move_highlights:
            x = c * self.square_size + self.square_size//2
            y = r * self.square_size + self.square_size//2
            self.canvas.create_oval(x-8, y-8, x+8, y+8, fill='#f6f669', outline='')

    def on_click(self, event):
        c = event.x // self.square_size
        r = event.y // self.square_size
        if not (0 <= r < 8 and 0 <= c < 8):
            return
        if self.game_over:
            return
        # if AI controls this side, ignore human clicks
        if self.ai_enabled.get(self.turn, False):
            return
        piece = self.board[r][c]
        if self.selected is None:
            # pick a piece
            if piece and piece[0] == self.turn:
                self.selected = (r, c)
                self.move_highlights = [(rr, cc) for (rr, cc) in self.legal_moves_for(r, c)]
                self.draw_board()
        else:
            sr, sc = self.selected
            if (r, c) in self.move_highlights:
                self.make_move(sr, sc, r, c)
                self.selected = None
                self.move_highlights = []
                self.draw_board()
                self.switch_turn()
                self.status.config(text=('White to move' if self.turn == 'w' else 'Black to move'))
            else:
                # select another piece
                if piece and piece[0] == self.turn:
                    self.selected = (r, c)
                    self.move_highlights = [(rr, cc) for (rr, cc) in self.legal_moves_for(r, c)]
                    self.draw_board()
                else:
                    # deselect
                    self.selected = None
                    self.move_highlights = []
                    self.draw_board()

    def switch_turn(self):
        self.turn = 'b' if self.turn == 'w' else 'w'
        # schedule AI move if next side is controlled by AI
        if not self.game_over and self.ai_enabled.get(self.turn, False):
            self.root.after(300, self.do_ai_move)
        # update status text
        self.status.config(text=('White to move' if self.turn == 'w' else 'Black to move'))

    def make_move(self, sr, sc, tr, tc):
        piece = self.board[sr][sc]
        self.board[tr][tc] = piece
        self.board[sr][sc] = None
        # pawn promotion
        if piece and piece[1] == 'P':
            if (piece[0] == 'w' and tr == 0) or (piece[0] == 'b' and tr == 7):
                prom = simpledialog.askstring('Promotion', 'Promote to (Q/R/B/N):', parent=self.root)
                if prom:
                    prom = prom.upper()
                    mapping = {'Q':'Q','R':'R','B':'B','N':'N'}
                    if prom in mapping:
                        self.board[tr][tc] = piece[0] + mapping[prom]
                    else:
                        self.board[tr][tc] = piece[0] + 'Q'
        # update moved flags for king/rook
        if piece:
            color = piece[0]
            if piece[1] == 'K':
                # detect castling (king moves two files)
                self.king_moved[color] = True
                if abs(tc - sc) == 2:
                    # kingside
                    if tc > sc:
                        # rook from h-file to f-file
                        rr, rc = tr, 7
                        new_r, new_c = tr, 5
                        if self.board[rr][rc] and self.board[rr][rc][1] == 'R':
                            self.board[new_r][new_c] = self.board[rr][rc]
                            self.board[rr][rc] = None
                            self.rook_moved[color]['h'] = True
                    else:
                        # queenside rook from a-file to d-file
                        rr, rc = tr, 0
                        new_r, new_c = tr, 3
                        if self.board[rr][rc] and self.board[rr][rc][1] == 'R':
                            self.board[new_r][new_c] = self.board[rr][rc]
                            self.board[rr][rc] = None
                            self.rook_moved[color]['a'] = True
            if piece[1] == 'R':
                # mark rook moved if it started from initial square
                if color == 'w':
                    if sr == 7 and sc == 0:
                        self.rook_moved['w']['a'] = True
                    if sr == 7 and sc == 7:
                        self.rook_moved['w']['h'] = True
                else:
                    if sr == 0 and sc == 0:
                        self.rook_moved['b']['a'] = True
                    if sr == 0 and sc == 7:
                        self.rook_moved['b']['h'] = True

        # update timer labels immediately after a move
        self.update_timer_labels()

    # -- Move generation and legality --
    def legal_moves_for(self, r, c):
        piece = self.board[r][c]
        if not piece:
            return []
        color = piece[0]
        moves = self.generate_pseudo_moves(r, c)
        legal = []
        for (tr, tc) in moves:
            # simulate
            saved = self.board[tr][tc]
            self.board[tr][tc] = self.board[r][c]
            self.board[r][c] = None
            king_safe = not self.is_in_check(color)
            # undo
            self.board[r][c] = self.board[tr][tc]
            self.board[tr][tc] = saved
            if king_safe:
                legal.append((tr, tc))
        return legal

    def is_in_check(self, color):
        # find king
        king_sq = None
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == color + 'K':
                    king_sq = (r, c)
                    break
            if king_sq:
                break
        if not king_sq:
            return True
        opp = 'b' if color == 'w' else 'w'
        attacked = self.squares_attacked_by(opp)
        return king_sq in attacked

    def squares_attacked_by(self, color):
        attacked = set()
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p[0] == color:
                    typ = p[1]
                    attacked.update(self.pseudo_attacks_for(r, c, typ, color))
        return attacked

    def pseudo_attacks_for(self, r, c, typ, color):
        # returns set of squares attacked by piece at r,c (ignores leaving king in check)
        res = set()
        dirs = []
        if typ == 'P':
            d = -1 if color == 'w' else 1
            for dc in (-1, 1):
                rr, cc = r + d, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8:
                    res.add((rr, cc))
            return res
        if typ == 'N':
            for dr, dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
                rr, cc = r+dr, c+dc
                if 0<=rr<8 and 0<=cc<8:
                    res.add((rr, cc))
            return res
        if typ == 'B' or typ == 'Q':
            dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
        if typ == 'R' or typ == 'Q':
            dirs += [(-1,0),(1,0),(0,-1),(0,1)]
        if typ == 'K':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    rr, cc = r+dr, c+dc
                    if 0<=rr<8 and 0<=cc<8:
                        res.add((rr, cc))
            return res
        # sliding pieces
        for dr, dc in dirs:
            rr, cc = r+dr, c+dc
            while 0<=rr<8 and 0<=cc<8:
                res.add((rr, cc))
                if self.board[rr][cc] is not None:
                    break
                rr += dr
                cc += dc
        return res

    def generate_pseudo_moves(self, r, c):
        piece = self.board[r][c]
        if not piece:
            return []
        color, typ = piece[0], piece[1]
        moves = []
        if typ == 'P':
            direction = -1 if color == 'w' else 1
            # forward one
            rr = r + direction
            if 0<=rr<8 and self.board[rr][c] is None:
                moves.append((rr, c))
                # two squares
                start_row = 6 if color == 'w' else 1
                rr2 = r + 2*direction
                if r == start_row and 0<=rr2<8 and self.board[rr2][c] is None:
                    moves.append((rr2, c))
            # captures
            for dc in (-1, 1):
                cc = c + dc
                rr = r + direction
                if 0<=rr<8 and 0<=cc<8:
                    target = self.board[rr][cc]
                    if target and target[0] != color:
                        moves.append((rr, cc))
            return moves
        if typ == 'N':
            for dr, dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
                rr, cc = r+dr, c+dc
                if 0<=rr<8 and 0<=cc<8:
                    t = self.board[rr][cc]
                    if t is None or t[0] != color:
                        moves.append((rr, cc))
            return moves
        if typ in ('B','R','Q'):
            dirs = []
            if typ in ('B','Q'):
                dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if typ in ('R','Q'):
                dirs += [(-1,0),(1,0),(0,-1),(0,1)]
            for dr, dc in dirs:
                rr, cc = r+dr, c+dc
                while 0<=rr<8 and 0<=cc<8:
                    t = self.board[rr][cc]
                    if t is None:
                        moves.append((rr, cc))
                    else:
                        if t[0] != color:
                            moves.append((rr, cc))
                        break
                    rr += dr
                    cc += dc
            return moves
        if typ == 'K':
            # normal king moves
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    rr, cc = r+dr, c+dc
                    if 0<=rr<8 and 0<=cc<8:
                        t = self.board[rr][cc]
                        if t is None or t[0] != color:
                            moves.append((rr, cc))
            # castling: king and rook must not have moved, path empty, and squares not attacked
            if not self.king_moved[color] and not self.is_in_check(color):
                opp = 'b' if color == 'w' else 'w'
                attacked = self.squares_attacked_by(opp)
                # kingside
                # rook must be at (r,7)
                if 0<=r<8 and 0<=c<8:
                    # kingside path c+1, c+2
                    try:
                        rook_piece = self.board[r][7]
                    except Exception:
                        rook_piece = None
                    if rook_piece == color + 'R' and not self.rook_moved[color]['h']:
                        if self.board[r][c+1] is None and self.board[r][c+2] is None:
                            if (r, c+1) not in attacked and (r, c+2) not in attacked:
                                moves.append((r, c+2))
                    # queenside rook at (r,0), path c-1,c-2,c-3
                    try:
                        rook_piece_q = self.board[r][0]
                    except Exception:
                        rook_piece_q = None
                    if rook_piece_q == color + 'R' and not self.rook_moved[color]['a']:
                        if self.board[r][c-1] is None and self.board[r][c-2] is None and self.board[r][c-3] is None:
                            if (r, c-1) not in attacked and (r, c-2) not in attacked:
                                moves.append((r, c-2))
            return moves
        return moves

    # -- AI and control methods --
    def toggle_ai(self, color):
        # toggle AI for a color ('w' or 'b') and update button text
        self.ai_enabled[color] = not self.ai_enabled.get(color, False)
        if color == 'w':
            self.ai_w_btn.config(text=('Disable AI: White' if self.ai_enabled[color] else 'Enable AI: White'))
        else:
            self.ai_b_btn.config(text=('Disable AI: Black' if self.ai_enabled[color] else 'Enable AI: Black'))
        # if enabling and it's that color's turn, schedule AI move
        if self.ai_enabled[color] and self.turn == color and not self.game_over:
            self.root.after(300, self.do_ai_move)

    def gather_all_legal_moves(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p[0] == color:
                    for (tr, tc) in self.legal_moves_for(r, c):
                        moves.append((r, c, tr, tc))
        return moves

    def do_ai_move(self):
        if self.game_over or not self.ai_enabled.get(self.turn, False):
            return
        moves = self.gather_all_legal_moves(self.turn)
        if not moves:
            self.game_over = True
            self.status.config(text='No legal moves')
            return
        # prefer captures
        capture_moves = []
        for (sr, sc, tr, tc) in moves:
            if self.board[tr][tc] is not None and self.board[tr][tc][0] != self.turn:
                capture_moves.append((sr, sc, tr, tc))
        choice = random.choice(capture_moves) if capture_moves else random.choice(moves)
        sr, sc, tr, tc = choice
        self.make_move(sr, sc, tr, tc)
        self.selected = None
        self.move_highlights = []
        self.draw_board()
        self.switch_turn()

    # -- Timer methods --
    def start_timer(self):
        try:
            minutes = int(self.timer_spin.get())
        except Exception:
            minutes = 10
        secs = max(1, minutes) * 60
        # initialize both timers if they are zero
        if self.timers['w'] == 0 and self.timers['b'] == 0:
            self.timers['w'] = secs
            self.timers['b'] = secs
        self.timer_running = True
        self.update_timer_labels()
        self.root.after(1000, self.timer_tick)

    def pause_timer(self):
        self.timer_running = False

    def timer_tick(self):
        if not self.timer_running or self.game_over:
            return
        # decrement current turn's clock
        self.timers[self.turn] -= 1
        if self.timers[self.turn] <= 0:
            self.timers[self.turn] = 0
            self.timer_running = False
            winner = 'White' if self.turn == 'b' else 'Black'
            messagebox.showinfo('Time', f'{winner} wins on time')
            self.game_over = True
            self.status.config(text=f'{winner} wins (time)')
            self.update_timer_labels()
            return
        self.update_timer_labels()
        self.root.after(1000, self.timer_tick)

    def update_timer_labels(self):
        self.white_time_label.config(text=f"White: {self.format_seconds(self.timers['w'])}")
        self.black_time_label.config(text=f"Black: {self.format_seconds(self.timers['b'])}")

    def format_seconds(self, s):
        m = s // 60
        sec = s % 60
        return f"{m:02d}:{sec:02d}"

    def forfeit(self):
        if self.game_over:
            return
        winner = 'White' if self.turn == 'b' else 'Black'
        messagebox.showinfo('Forfeit', f'{winner} wins by forfeit')
        self.game_over = True
        self.status.config(text=f'{winner} wins (forfeit)')

    def reset_game(self):
        self.board = init_board()
        self.turn = 'w'
        self.selected = None
        self.move_highlights = []
        self.game_over = False
        self.status.config(text='White to move')
        self.draw_board()
        # reset castling flags
        self.king_moved = {'w': False, 'b': False}
        self.rook_moved = {'w': {'a': False, 'h': False}, 'b': {'a': False, 'h': False}}
        # reset timers
        self.timer_running = False
        self.timers = {'w': 0, 'b': 0}
        self.update_timer_labels()
        if self.ai_enabled.get(self.turn, False):
            self.root.after(300, self.do_ai_move)


if __name__ == '__main__':
    root = tk.Tk()
    app = ChessApp(root)
    root.mainloop()
