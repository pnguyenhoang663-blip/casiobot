import asyncio
import glob
import io
import os
import random
import re
import time

import chess
import discord
from PIL import Image, ImageDraw, ImageFont

LIGHT = (238, 238, 210)
DARK = (118, 150, 86)
SQ = 60
INF = 10 ** 9

GLYPH = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}
LETTER = {'K': 'K', 'Q': 'Q', 'R': 'R', 'B': 'B', 'N': 'N', 'P': 'P',
          'k': 'k', 'q': 'q', 'r': 'r', 'b': 'b', 'n': 'n', 'p': 'p'}

CHESS = {}
CHALLENGES = {}

DIFFS = {
    'easy': {'label': 'Dễ (100-400 ELO)', 'depth': 2, 'noise': 0.6, 'budget': 1.0},
    'normal': {'label': 'Bình thường (600-900 ELO)', 'depth': 3, 'noise': 0.4, 'budget': 2.0},
    'hard': {'label': 'Khó (1200-1600 ELO)', 'depth': 4, 'noise': 0.1, 'budget': 3.0},
    'hardcore': {'label': 'Siêu khó (2000-2400 ELO)', 'depth': 5, 'noise': 0.0, 'budget': 4.0},
}


def parse_diff(s):
    s = (s or '').strip().lower()
    aliases = {
        'easy': ('easy', 'e', 'de', 'dễ'),
        'normal': ('normal', 'binh thuong', 'binhthuong', 'binh', 'n', 'tb'),
        'hard': ('hard', 'kho', 'khó', 'h'),
        'hardcore': ('hardcore', 'sieu kho', 'siêu khó', 'sieu', 'hc', 'sk'),
    }
    for k, al in aliases.items():
        if s in al:
            return k
    return None


# ---------------- RENDER ---------------- 

_font_path = None


def _find_font():
    global _font_path
    if _font_path is not None:
        return _font_path or None
    roots = [r'C:\Windows\Fonts', '/usr/share/fonts', '/usr/local/share/fonts',
             '/System/Library/Fonts', '/Library/Fonts']
    names = ['NotoSansSymbols2-Regular.ttf', 'NotoSansSymbols-Regular.ttf',
             'ChessMerida.ttf', 'Chess Merida.ttf', 'merida.ttf',
             'seguisym.ttf', 'Symbola.ttf', 'DejaVuSans.ttf', 'DejaVuSerif.ttf']
    for root in roots:
        if not os.path.isdir(root):
            continue
        for n in names:
            p = os.path.join(root, n)
            if os.path.exists(p):
                _font_path = p
                return p
    for pat in ('**/NotoSansSymbols2-Regular.ttf', '**/NotoSansSymbols-Regular.ttf',
                '**/seguisym.ttf', '**/Symbola.ttf', '**/DejaVuSans.ttf'):
        for root in roots:
            if not os.path.isdir(root):
                continue
            for p in glob.glob(os.path.join(root, pat), recursive=True):
                _font_path = p
                return p
    _font_path = ''
    return None


def board_png(board):
    MARGIN = 28
    LABEL_BG = (245, 233, 203)
    LABEL_FG = (150, 108, 62)
    bw = 8 * SQ
    size = bw + MARGIN * 2
    img = Image.new('RGB', (size, size), LABEL_BG)
    d = ImageDraw.Draw(img)
    ox = MARGIN
    oy = MARGIN
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r + c) % 2 == 0 else DARK
            d.rectangle([ox + c * SQ, oy + r * SQ, ox + (c + 1) * SQ, oy + (r + 1) * SQ], fill=color)

    fp = _find_font()
    font = ImageFont.truetype(fp, int(SQ * 0.86)) if fp else None
    use_glyph = font is not None
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        col = sq % 8
        row = 7 - (sq // 8)
        x = ox + col * SQ
        y = oy + row * SQ
        sym = p.symbol()
        ch = GLYPH[sym] if use_glyph else LETTER[sym]
        fill = (255, 255, 255) if p.color == chess.WHITE else (0, 0, 0)
        outline = (0, 0, 0) if p.color == chess.WHITE else (255, 255, 255)
        if font:
            bbox = font.getbbox(ch)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = x + (SQ - tw) / 2 - bbox[0]
            ty = y + (SQ - th) / 2 - bbox[1]
            shadow = (70, 85, 60)
            d.text((tx + 1.5, ty + 1.5), ch, font=font, fill=shadow, stroke_width=2, stroke_fill=shadow)
            d.text((tx, ty), ch, font=font, fill=fill, stroke_width=2, stroke_fill=outline)
        else:
            d.text((x + SQ / 4, y + SQ / 4), ch, fill=fill)

    lf = ImageFont.truetype(fp, int(MARGIN * 0.85)) if fp else ImageFont.load_default()

    def center(xmid, ymid, t):
        bb = lf.getbbox(t)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        d.text((xmid - tw / 2 - bb[0], ymid - th / 2 - bb[1]), t, font=lf, fill=LABEL_FG)

    # số bên trái (1-8, trên xuống)
    for r in range(8):
        center(MARGIN / 2, oy + r * SQ + SQ / 2, str(8 - r))
    # chữ bên dưới (a-h)
    for c in range(8):
        center(ox + c * SQ + SQ / 2, oy + bw + MARGIN / 2, chr(97 + c))

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf


# ---------------- ENGINE ---------------- 

PIECE_VAL = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 0}

PAWN_PST = [0, 0, 0, 0, 0, 0, 0, 0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5, 5, 10, 25, 25, 10, 5, 5,
            0, 0, 0, 20, 20, 0, 0, 0,
            5, -5, -10, 0, 0, -10, -5, 5,
            5, 10, 10, -20, -20, 10, 10, 5,
            0, 0, 0, 0, 0, 0, 0, 0]
KNIGHT_PST = [-50, -40, -30, -30, -30, -30, -40, -50,
              -40, -20, 0, 0, 0, 0, -20, -40,
              -30, 0, 10, 15, 15, 10, 0, -30,
              -30, 5, 15, 20, 20, 15, 5, -30,
              -30, 0, 15, 20, 20, 15, 0, -30,
              -30, 5, 10, 15, 15, 10, 5, -30,
              -40, -20, 0, 5, 5, 0, -20, -40,
              -50, -40, -30, -30, -30, -30, -40, -50]
BISHOP_PST = [-20, -10, -10, -10, -10, -10, -10, -20,
              -10, 0, 0, 0, 0, 0, 0, -10,
              -10, 0, 5, 10, 10, 5, 0, -10,
              -10, 5, 5, 10, 10, 5, 5, -10,
              -10, 0, 10, 10, 10, 10, 0, -10,
              -10, 10, 10, 10, 10, 10, 10, -10,
              -10, 5, 0, 0, 0, 0, 5, -10,
              -20, -10, -10, -10, -10, -10, -10, -20]
ROOK_PST = [0, 0, 0, 0, 0, 0, 0, 0,
            5, 10, 10, 10, 10, 10, 10, 5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            0, 0, 0, 5, 5, 0, 0, 0]
QUEEN_PST = [-20, -10, -10, -5, -5, -10, -10, -20,
             -10, 0, 0, 0, 0, 0, 0, -10,
             -10, 0, 5, 5, 5, 5, 0, -10,
             -5, 0, 5, 5, 5, 5, 0, -5,
             0, 0, 5, 5, 5, 5, 0, -5,
             -10, 5, 5, 5, 5, 5, 0, -10,
             -10, 0, 5, 0, 0, 0, 0, -10,
             -20, -10, -10, -5, -5, -10, -10, -20]
KING_PST = [-30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -20, -30, -30, -40, -40, -30, -30, -20,
            -10, -20, -20, -20, -20, -20, -20, -10,
            20, 20, 0, 0, 0, 0, 20, 20,
            20, 30, 10, 0, 0, 10, 30, 20]
PST_MAP = {1: PAWN_PST, 2: KNIGHT_PST, 3: BISHOP_PST, 4: ROOK_PST, 5: QUEEN_PST, 6: KING_PST}

BOOK_MOVES = {'e2e4', 'e7e5', 'd2d4', 'd7d5', 'g1f3', 'g8f6', 'b1c3', 'c7c5',
              'c2c4', 'f1c4', 'f1b5', 'b8c6', 'e7e6', 'c7c6', 'g2g3', 'f7f5',
              'c2c3', 'f2f4', 'd7d6', 'e2e3', 'b8a6', 'b2b3', 'g8h6'}


def mirror(sq):
    return sq ^ 56


def evaluate(board):
    if board.is_checkmate():
        return -99999 if board.turn else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        idx = sq if p.color == chess.WHITE else mirror(sq)
        v = PIECE_VAL[p.piece_type] + PST_MAP[p.piece_type][idx]
        score += v if p.color == chess.WHITE else -v
    return score


class _SearchTimeout(Exception):
    pass


def search(board, depth, alpha, beta, deadline=None):
    if deadline is not None and time.monotonic() > deadline:
        raise _SearchTimeout()
    if depth == 0:
        return evaluate(board)
    legal = list(board.legal_moves)
    if not legal:
        if board.is_checkmate():
            return -99999 + (10 - depth)
        return 0
    legal.sort(key=lambda m: (board.is_capture(m), m.promotion is not None), reverse=True)
    best = -INF
    for mv in legal:
        board.push(mv)
        try:
            v = -search(board, depth - 1, -beta, -alpha, deadline)
        finally:
            board.pop()
        if v > best:
            best = v
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def score_move(board, mv, depth, deadline=None):
    board.push(mv)
    try:
        v = -search(board, max(depth - 1, 0), -INF, INF, deadline)
        board.pop()
        return v
    except _SearchTimeout:
        board.pop()
        raise


def best_move(board, depth, noise, time_budget=2.0):
    legal = list(board.legal_moves)
    if not legal:
        return None
    deadline = time.monotonic() + time_budget
    ordered = list(legal)
    random.shuffle(ordered)
    best = None
    for d in range(1, depth + 1):
        best_d = None
        best_s = -INF
        try:
            for mv in ordered:
                s = score_move(board, mv, d, deadline) + random.uniform(-noise, noise)
                if s > best_s:
                    best_s = s
                    best_d = mv
        except _SearchTimeout:
            break
        if best_d is not None:
            best = best_d
            ordered = [best_d] + [m for m in ordered if m != best_d]
    return best if best is not None else legal[0]


def _win_score(board, depth):
    """Điểm kiểu negamax chỉ để tìm chiếu hết: >50000 nghĩa là bên đang đi thắng buộc trong depth ply."""
    if board.is_checkmate():
        return -99999 + (10 - depth)
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    if depth <= 0:
        return 0
    legal = list(board.legal_moves)
    best = -999999
    for mv in legal:
        board.push(mv)
        v = -_win_score(board, depth - 1)
        board.pop()
        if v > best:
            best = v
        if best > 50000:
            break
    return best


def _forces_mate(board_after_mover_moved, plies):
    """Sau khi mover đi (đến lượt đối thủ): True nếu mover ép chiếu hết trong `plies` ply."""
    return -_win_score(board_after_mover_moved, plies) > 40000


def evaluate_played_move(board, mv, depth):
    legal = list(board.legal_moves)
    if not legal:
        return '❓️', 'Hết cờ'

    board.push(mv)
    mates_now = board.is_checkmate()
    board.pop()
    if mates_now:
        return '#', 'Hết cờ'

    if len(legal) == 1:
        if mates_now:
            return '⏩️', 'Ép buộc (dẫn đến chiếu hết)'
        return '➡️', 'Ép buộc'

    if board.ply() < 12 and mv.uci() in BOOK_MOVES:
        return '📖', 'Giáo khoa'

    # Bỏ lỡ chiếu hết (có nước chiếu hết trong 1 nhưng không đi)
    has_mate1 = False
    for m in legal:
        board.push(m)
        mm = board.is_checkmate()
        board.pop()
        if mm:
            has_mate1 = True
            if m == mv:
                return '#', 'Hết cờ'
    if has_mate1:
        return '➖️', 'Bỏ lỡ chiếu hết'

    # Đe dọa/ép chiếu hết: nước vừa đi khiến đối thủ không tránh được chiếu hết
    board.push(mv)
    forced = _forces_mate(board, 2)
    board.pop()
    if forced:
        return '⭐️', 'Tốt nhất'

    def _sc(m):
        return score_move(board, m, depth)

    best_score = max(_sc(m) for m in legal)
    played = _sc(mv)
    loss = best_score - played

    if best_score >= 2.0:
        good = [m for m in legal if _sc(m) >= best_score - 0.3]
        if len(good) == 1 and good[0] == mv:
            return '‼️', 'Thiên tài'
    if best_score >= 1.5 and played < 0.3:
        return '❌️', 'Bỏ lỡ cơ hội'

    best_move_here = max(legal, key=_sc)
    if loss <= 0.05:
        if mv == best_move_here:
            return '⭐️', 'Tốt nhất'
        return '👍', 'Xuất sắc'
    if loss <= 0.3:
        return '✅️', 'Tốt'
    if loss <= 0.7:
        return '⁉️', 'Không chính xác'
    if loss <= 1.2:
        return '❓️', 'Sai lầm'
    return '💥', 'Sai lầm ngớ ngẩn'


# ---------------- HELPERS ---------------- 

async def _send_turn(g, channel, text):
    img = await asyncio.to_thread(board_png, g['board'])
    msg = await channel.send(content=text, file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg
    g.setdefault('imgs', []).append(msg)


async def _cleanup_except_final(g):
    imgs = g.get('imgs', [])
    if not imgs:
        return
    final = imgs[-1]
    for m in imgs:
        if m.id == final.id:
            continue
        try:
            await m.delete()
        except Exception:
            pass


def _game_over_text(g):
    board = g['board']
    if board.is_checkmate():
        loser_color = 'white' if board.turn == chess.WHITE else 'black'
        winner_color = 'black' if loser_color == 'white' else 'white'
        if g.get('bot'):
            winner = 'Bot' if winner_color == 'black' else 'Bạn'
            loser = 'Bạn' if winner_color == 'black' else 'Bot'
        else:
            winner = f'<@{g["white"]}>' if winner_color == 'white' else f'<@{g["black"]}>'
            loser = f'<@{g["white"]}>' if loser_color == 'white' else f'<@{g["black"]}>'
        return f'# {loser} : Hết cờ — 👑 {winner} : Chiến thắng'
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves():
        if g.get('bot'):
            return '1/2 : Hòa (Bạn vs Bot)'
        return f'1/2 : Hòa (<@{g["white"]}> vs <@{g["black"]}>)'
    return None


async def _maybe_end(g, channel):
    end = _game_over_text(g)
    if end:
        await _send_turn(g, channel, end)
        await _cleanup_except_final(g)
        CHESS.pop(str(channel.id), None)
        return True
    return False


# ---------------- COMMANDS ---------------- 

def parse_color(s):
    s = (s or '').strip().lower()
    if s in ('trắng', 'trang', 'white', 'w', 't'):
        return 'white'
    if s in ('đen', 'den', 'black', 'b', 'd'):
        return 'black'
    if s in ('random', 'ngẫu nhiên', 'ngau nhien', 'r', 'rd', 'rand'):
        return 'random'
    return None


def _wrong(cmd, detail, usage):
    return f'❌ **Sai** `{cmd}` ({detail})! Cách dùng: `{usage}`'


def _miss(cmd, usage):
    return f'⚠️ **Thiếu tham số** `{cmd}`! Cách dùng: `{usage}`'


async def cmd_chess(message, args, prefix):
    parts = args.split(None, 1)
    name = parts[0] if parts else ''
    color_raw = parts[1] if len(parts) > 1 else ''
    target = None
    if message.mentions:
        target = message.mentions[0]
    else:
        if name.isdigit():
            target = message.guild.get_member(int(name))
        elif name:
            for m in message.guild.members:
                if m.name == name or m.display_name == name or (m.nick and m.nick == name):
                    target = m
                    break
    if not target:
        await message.reply(_wrong('chess', 'không tìm thấy người chơi đó', 'p!chess <username> [trắng|đen|random]'))
        return
    if target == message.author or target.bot:
        await message.reply('❌ Không thể thách chính mình hoặc bot (bot dùng `p!chessbot`).')
        return
    color = None
    if color_raw:
        color = parse_color(color_raw)
        if color is None:
            await message.reply(_wrong('chess', f'`{color_raw}` không hợp lệ', 'p!chess <username> [trắng|đen|random]'))
            return
    ch = str(message.channel.id)
    if CHESS.get(ch):
        await message.reply('❌ Đã có trận cờ đang chơi ở kênh này.')
        return
    CHALLENGES[ch] = {'from': message.author.id, 'to': target.id, 'color': color}
    col = {'white': ' (Trắng)', 'black': ' (Đen)', None: ' (Random)'}[color]
    await message.reply(f'⚔️ <@{target.id}> — <@{message.author.id}> thách đấu cờ vua{col}!\nNhận lời: `p!chessok` · Từ chối: `p!chessno`')


async def cmd_chessok(message, args, prefix):
    ch = str(message.channel.id)
    chall = CHALLENGES.get(ch)
    if not chall or chall['to'] != message.author.id:
        await message.reply('❌ Không có lời thách nào cho bạn.')
        return
    CHALLENGES.pop(ch)
    color = chall.get('color')
    if color == 'black':
        white, black = chall['to'], chall['from']
    elif color == 'white':
        white, black = chall['from'], chall['to']
    else:
        if random.random() < 0.5:
            white, black = chall['from'], chall['to']
        else:
            white, black = chall['to'], chall['from']
    board = chess.Board()
    g = {'board': board, 'white': white, 'black': black, 'bot': False,
         'difficulty': '', 'paused': False, 'img_msg': None, 'imgs': []}
    CHESS[ch] = g
    img = await asyncio.to_thread(board_png, board)
    msg = await message.channel.send(
        content=f'♟️ Trận cờ bắt đầu!\n<@{white}> (Trắng) vs <@{black}> (Đen)\nĐi nước: `move <nước>`',
        file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg
    g['imgs'].append(msg)


async def cmd_chessno(message, args, prefix):
    ch = str(message.channel.id)
    chall = CHALLENGES.get(ch)
    if not chall or chall['to'] != message.author.id:
        await message.reply('❌ Không có lời thách nào cho bạn.')
        return
    CHALLENGES.pop(ch)
    await message.reply(f'❌ <@{chall["from"]}> — <@{chall["to"]}> đã từ chối lời thách đấu.')


async def cmd_chessbot(message, args, prefix):
    parts = args.split(None, 1)
    level = parse_diff(parts[0] if parts else '')
    if not level:
        await message.reply(_wrong('chessbot', 'độ khó không hợp lệ', 'p!chessbot <dễ|bình thường|khó|siêu khó> [trắng|đen|random]'))
        return
    player_color = None
    if len(parts) > 1 and parts[1].strip():
        player_color = parse_color(parts[1])
        if player_color is None:
            await message.reply(_wrong('chessbot', f'`{parts[1].strip()}` không hợp lệ', 'p!chessbot <độ khó> [trắng|đen|random]'))
            return
    if player_color is None:
        player_color = 'white' if random.random() < 0.5 else 'black'
    ch = str(message.channel.id)
    if CHESS.get(ch):
        await message.reply('❌ Đã có trận cờ đang chơi ở kênh này.')
        return
    board = chess.Board()
    white = message.author.id if player_color == 'white' else 'bot'
    black = 'bot' if player_color == 'white' else message.author.id
    g = {'board': board, 'white': white, 'black': black, 'bot': True,
         'difficulty': level, 'paused': False, 'img_msg': None, 'imgs': []}
    CHESS[ch] = g
    my_col = 'Trắng' if player_color == 'white' else 'Đen'
    img = await asyncio.to_thread(board_png, board)
    msg = await message.channel.send(
        content=f'🤖 Trận cờ với Bot (**{DIFFS[level]["label"]}**) bắt đầu!\nBạn cầm **{my_col}** — đi: `move <nước>`',
        file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg
    g['imgs'].append(msg)
    if player_color == 'black':
        d = DIFFS[level]
        bm = await asyncio.to_thread(best_move, board, d['depth'], d['noise'], d['budget'])
        if bm:
            bsan = board.san(bm)
            board.push(bm)
            await _send_turn(g, message.channel, f'Bot : {bsan}')
            await _maybe_end(g, message.channel)


async def cmd_chessmove(message, args, prefix):
    ch = str(message.channel.id)
    g = CHESS.get(ch)
    if not g:
        await message.reply('❌ Chưa có trận cờ. Dùng `p!chessbot <độ khó>` hoặc `p!chess <user>`.')
        return
    if g.get('paused'):
        await message.reply('⏸️ Trận cờ đang tạm dừng — `tiep` để tiếp tục.')
        return
    if not args.strip():
        await message.reply(_miss('chessmove', 'p!chessmove <nước> (vd e2e4)'))
        return
    board = g['board']
    turn_color = 'white' if board.turn == chess.WHITE else 'black'
    if g.get('bot'):
        if message.author.id not in (g['white'], g['black']):
            await message.reply('❌ Trận này là bạn vs Bot — chỉ bạn chơi.')
            return
        my_color = 'white' if g['white'] == message.author.id else 'black'
        if turn_color != my_color:
            await message.reply('❌ Đang đến lượt Bot.')
            return
    else:
        expected = g['white'] if turn_color == 'white' else g['black']
        if message.author.id != expected:
            await message.reply('❌ Chưa đến lượt bạn.')
            return
    mv = None
    text = args.strip()
    try:
        try:
            mv = board.parse_uci(text.lower())
        except Exception:
            mv = board.parse_san(text)
    except Exception:
        mv = None
    if mv is None or mv not in board.legal_moves:
        await message.reply(f'❌ Nước không hợp lệ: `{text}`')
        return
    san = board.san(mv)
    name = message.author.display_name
    board.push(mv)
    await _send_turn(g, message.channel, f'{name} : {san}')
    if await _maybe_end(g, message.channel):
        return
    if g.get('bot') and not board.is_game_over():
        d = DIFFS[g['difficulty']]
        bm = await asyncio.to_thread(best_move, board, d['depth'], d['noise'], d['budget'])
        if bm:
            bsan = board.san(bm)
            board.push(bm)
            await _send_turn(g, message.channel, f'Bot : {bsan}')
            await _maybe_end(g, message.channel)


async def cmd_chessngung(message, args, prefix):
    g = CHESS.get(str(message.channel.id))
    if not g:
        await message.reply('❌ Không có trận cờ nào.')
        return
    if g.get('paused'):
        await message.reply('⏸️ Trận cờ đã tạm dừng rồi.')
        return
    g['paused'] = True
    await message.reply('⏸️ Đã tạm dừng trận cờ! Gõ `tiep` để tiếp tục.')


async def cmd_chesstiep(message, args, prefix):
    ch = str(message.channel.id)
    g = CHESS.get(ch)
    if not g:
        await message.reply('❌ Không có trận cờ nào.')
        return
    if not g.get('paused'):
        await message.reply('⏩ Trận cờ vẫn đang chạy.')
        return
    g['paused'] = False
    await _send_turn(g, message.channel, '▶️ Trận cờ tiếp tục!')
    await _maybe_end(g, message.channel)


async def cmd_chessthua(message, args, prefix):
    ch = str(message.channel.id)
    g = CHESS.pop(ch, None)
    if not g:
        await message.reply('❌ Không có trận cờ nào.')
        return
    if g.get('bot'):
        if message.author.id != g['white']:
            return
        loser, winner = 'Bạn', 'Bot'
    else:
        if message.author.id not in (g['white'], g['black']):
            return
        resigner = message.author.id
        winner_id = g['black'] if resigner == g['white'] else g['white']
        loser = f'<@{resigner}>'
        winner = f'<@{winner_id}>'
    await _send_turn(g, message.channel, f'🏳️ {loser} : Đầu hàng — 👑 {winner} : Chiến thắng')
    await _cleanup_except_final(g)


async def handle_bare_chat(message, prefix):
    ch = str(message.channel.id)
    if ch not in CHESS:
        return False
    low = message.content.strip().lower()
    if re.match(r'^move\b', low):
        args = re.sub(r'(?i)^move\s*', '', message.content.strip())
        await cmd_chessmove(message, args, prefix)
        return True
    if low == 'ngung':
        await cmd_chessngung(message, '', prefix)
        return True
    if low == 'tiep':
        await cmd_chesstiep(message, '', prefix)
        return True
    if low == 'thua':
        await cmd_chessthua(message, '', prefix)
        return True
    return False