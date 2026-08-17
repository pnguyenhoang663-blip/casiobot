import asyncio
import glob
import io
import os
import random

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
    'easy': {'label': 'Dễ', 'depth': 1, 'noise': 0.8},
    'normal': {'label': 'Bình thường', 'depth': 2, 'noise': 0.3},
    'hard': {'label': 'Khó', 'depth': 3, 'noise': 0.1},
    'hardcore': {'label': 'Siêu khó', 'depth': 4, 'noise': 0.0},
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
    names = ['DejaVuSans.ttf', 'DejaVuSerif.ttf', 'seguisym.ttf', 'Symbola.ttf',
             'NotoSansSymbols-Regular.ttf']
    for root in roots:
        if not os.path.isdir(root):
            continue
        for n in names:
            p = os.path.join(root, n)
            if os.path.exists(p):
                _font_path = p
                return p
    for pat in ('**/DejaVuSans.ttf', '**/seguisym.ttf', '**/Symbola.ttf'):
        for root in roots:
            if not os.path.isdir(root):
                continue
            for p in glob.glob(os.path.join(root, pat), recursive=True):
                _font_path = p
                return p
    _font_path = ''
    return None


def board_png(board):
    size = 8 * SQ
    img = Image.new('RGB', (size, size), LIGHT)
    d = ImageDraw.Draw(img)
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r + c) % 2 == 0 else DARK
            d.rectangle([c * SQ, r * SQ, (c + 1) * SQ, (r + 1) * SQ], fill=color)

    fp = _find_font()
    font = ImageFont.truetype(fp, int(SQ * 0.78)) if fp else None
    use_glyph = font is not None
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        col = sq % 8
        row = 7 - (sq // 8)
        x = col * SQ
        y = row * SQ
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
            d.text((tx, ty), ch, font=font, fill=fill, stroke_width=2, stroke_fill=outline)
        else:
            d.text((x + SQ / 4, y + SQ / 4), ch, fill=fill)
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


def search(board, depth, alpha, beta):
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
        v = -search(board, depth - 1, -beta, -alpha)
        board.pop()
        if v > best:
            best = v
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def score_move(board, mv, depth):
    board.push(mv)
    v = -search(board, max(depth - 1, 0), -INF, INF)
    board.pop()
    return v


def best_move(board, depth, noise):
    legal = list(board.legal_moves)
    if not legal:
        return None
    random.shuffle(legal)
    best = None
    best_s = -INF
    for mv in legal:
        s = score_move(board, mv, depth) + random.uniform(-noise, noise)
        if s > best_s:
            best_s = s
            best = mv
    return best


def evaluate_played_move(board, mv, depth):
    legal = list(board.legal_moves)
    if not legal:
        return '❓️', 'Hết cờ'
    mate_move = None
    for m in legal:
        board.push(m)
        mm = board.is_checkmate()
        board.pop()
        if mm:
            mate_move = m
            break
    if mate_move is not None:
        if mv == mate_move:
            return '#', 'Hết cờ'
        return '➖️', 'Bỏ lỡ chiếu hết'
    if len(legal) == 1:
        board.push(mv)
        mm = board.is_checkmate()
        board.pop()
        if mm:
            return '⏩️', 'Ép buộc (dẫn đến chiếu hết)'
        return '➡️', 'Ép buộc'
    if board.ply() < 12 and mv.uci() in BOOK_MOVES:
        return '📖', 'Giáo khoa'

    def _sc(m):
        return score_move(board, m, depth)

    best_score = max(_sc(m) for m in legal)
    played = _sc(mv)
    loss = best_score - played
    if best_score >= 1.5:
        good = [m for m in legal if _sc(m) >= best_score - 0.2]
        if len(good) == 1 and good[0] == mv:
            return '‼️', 'Thiên tài'
    if best_score >= 1.0 and played < 0.2:
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
    if g.get('img_msg'):
        try:
            await g['img_msg'].delete()
        except Exception:
            pass
    img = await asyncio.to_thread(board_png, g['board'])
    msg = await channel.send(content=text, file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg


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
        return f'👑 {winner} : Chiến thắng\n# {loser} : Hết cờ'
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves():
        return '1/2 : Hòa'
    return None


async def _maybe_end(g, channel):
    end = _game_over_text(g)
    if end:
        await _send_turn(g, channel, end)
        CHESS.pop(str(channel.id), None)
        return True
    return False


# ---------------- COMMANDS ---------------- 

def _wrong(cmd, detail, usage):
    return f'❌ **Sai** `{cmd}` ({detail})! Cách dùng: `{usage}`'


def _miss(cmd, usage):
    return f'⚠️ **Thiếu tham số** `{cmd}`! Cách dùng: `{usage}`'


async def cmd_chess(message, args, prefix):
    target = None
    if message.mentions:
        target = message.mentions[0]
    else:
        a = args.strip()
        if a.isdigit():
            target = message.guild.get_member(int(a))
        elif a:
            for m in message.guild.members:
                if m.name == a or m.display_name == a or (m.nick and m.nick == a):
                    target = m
                    break
    if not target:
        await message.reply(_wrong('chess', 'không tìm thấy người chơi đó', 'p!chess <username>'))
        return
    if target == message.author or target.bot:
        await message.reply('❌ Không thể thách chính mình hoặc bot (bot dùng `p!chessbot`).')
        return
    ch = str(message.channel.id)
    if CHESS.get(ch):
        await message.reply('❌ Đã có trận cờ đang chơi ở kênh này.')
        return
    CHALLENGES[ch] = {'from': message.author.id, 'to': target.id}
    await message.reply(f'⚔️ <@{target.id}> — <@{message.author.id}> thách đấu cờ vua!\nNhận lời: `p!chessok` · Từ chối: `p!chessno`')


async def cmd_chessok(message, args, prefix):
    ch = str(message.channel.id)
    chall = CHALLENGES.get(ch)
    if not chall or chall['to'] != message.author.id:
        await message.reply('❌ Không có lời thách nào cho bạn.')
        return
    CHALLENGES.pop(ch)
    board = chess.Board()
    g = {'board': board, 'white': chall['from'], 'black': chall['to'], 'bot': False,
         'difficulty': '', 'paused': False, 'img_msg': None}
    CHESS[ch] = g
    img = await asyncio.to_thread(board_png, board)
    msg = await message.channel.send(
        content=f'♟️ Trận cờ bắt đầu!\n<@{chall["from"]}> (Trắng) vs <@{chall["to"]}> (Đen)\nĐi nước: `p!chessmove <nước>`',
        file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg


async def cmd_chessno(message, args, prefix):
    ch = str(message.channel.id)
    chall = CHALLENGES.get(ch)
    if not chall or chall['to'] != message.author.id:
        await message.reply('❌ Không có lời thách nào cho bạn.')
        return
    CHALLENGES.pop(ch)
    await message.reply(f'❌ <@{chall["from"]}> — <@{chall["to"]}> đã từ chối lời thách đấu.')


async def cmd_chessbot(message, args, prefix):
    level = parse_diff(args)
    if not level:
        await message.reply(_wrong('chessbot', 'độ khó không hợp lệ', 'p!chessbot <dễ|bình thường|khó|siêu khó>'))
        return
    ch = str(message.channel.id)
    if CHESS.get(ch):
        await message.reply('❌ Đã có trận cờ đang chơi ở kênh này.')
        return
    board = chess.Board()
    g = {'board': board, 'white': message.author.id, 'black': 'bot', 'bot': True,
         'difficulty': level, 'paused': False, 'img_msg': None}
    CHESS[ch] = g
    img = await asyncio.to_thread(board_png, board)
    msg = await message.channel.send(
        content=f'🤖 Trận cờ với Bot (**{DIFFS[level]["label"]}**) bắt đầu!\nBạn cầm **Trắng** — đi: `p!chessmove <nước>`',
        file=discord.File(img, 'banco.png'))
    g['img_msg'] = msg


async def cmd_chessmove(message, args, prefix):
    ch = str(message.channel.id)
    g = CHESS.get(ch)
    if not g:
        await message.reply('❌ Chưa có trận cờ. Dùng `p!chessbot <độ khó>` hoặc `p!chess <user>`.')
        return
    if g.get('paused'):
        await message.reply('⏸️ Trận cờ đang tạm dừng — `p!chesstiep` để tiếp tục.')
        return
    if not args.strip():
        await message.reply(_miss('chessmove', 'p!chessmove <nước> (vd e2e4)'))
        return
    board = g['board']
    turn_color = 'white' if board.turn == chess.WHITE else 'black'
    if g.get('bot'):
        if message.author.id != g['white']:
            await message.reply('❌ Trận này là bạn vs Bot — chỉ bạn chơi (Trắng).')
            return
        if board.turn != chess.WHITE:
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
    ev_depth = min(max(DIFFS.get(g['difficulty'], DIFFS['normal'])['depth'] if g.get('bot') else 3, 1), 3)
    icon, label = await asyncio.to_thread(evaluate_played_move, board, mv, ev_depth)
    san = board.san(mv)
    name = message.author.display_name
    board.push(mv)
    await _send_turn(g, message.channel, f'{name} : {san} {icon} {label}')
    if await _maybe_end(g, message.channel):
        return
    if g.get('bot') and not board.is_game_over():
        d = DIFFS[g['difficulty']]
        bm = await asyncio.to_thread(best_move, board, d['depth'], d['noise'])
        if bm:
            bicon, blabel = await asyncio.to_thread(evaluate_played_move, board, bm, ev_depth)
            bsan = board.san(bm)
            board.push(bm)
            await _send_turn(g, message.channel, f'Bot : {bsan} {bicon} {blabel}')
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
    await message.reply('⏸️ Đã tạm dừng trận cờ! `p!chesstiep` để tiếp tục.')


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
    if g.get('img_msg'):
        try:
            await g['img_msg'].delete()
        except Exception:
            pass
    img = await asyncio.to_thread(board_png, g['board'])
    await message.channel.send(content=f'🏳️ {loser} : Đầu hàng — 👑 {winner} : Chiến thắng',
                               file=discord.File(img, 'banco.png'))