import asyncio
import io
import json
import os
import random
import re
import subprocess
import time

import aiohttp
import html
import discord
from PIL import Image

import compiler_lib as cl
import chessbot
import gsearch
import matkhau
import noitu
import vd_docs

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

CONFIG.setdefault('prefix', 'p!')
CONFIG.setdefault('token', '')
CONFIG.setdefault('guilds', {})

PREFIX = os.getenv('PREFIX', '') or CONFIG.get('prefix', 'p!')
TOKEN = os.getenv('TOKEN', '') or CONFIG.get('token', '')

try:
    from aiohttp import web
except Exception:
    web = None

AI_MODELS = [m.strip() for m in os.getenv('AI_MODELS', 'gemini-1.5-flash,gemini-1.5-pro,gemini-2.0-flash').split(',') if m.strip()] or ['gemini-1.5-flash']
AI_MODEL = AI_MODELS[0]
AI_KEY = os.getenv('AI_KEY', '')
AI_BASE = os.getenv('AI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/openai')
AI_CHANNELS = set()
AI_HISTORY = {}
AI_NOKEY_ONCE = set()
AI_DOC = ''
AI_HISTORY_LEN = 8
PERSONAS = {
    1: 'TÍNH CÁCH NGOAN: lịch sự, đúng mực, thân thiện, không chửi thề, không xúc phạm, trả lời mọi câu hỏi (biết hết mọi thứ).',
    2: 'TÍNH CÁCH LÁO: hơi láo, hay chọc ghẹo, tếu táo, nhưng không xúc phạm nặng và không chửi tục (biết hết mọi thứ).',
    3: 'TÍNH CÁCH ĐCM: rất láo, hay chửi tục, có thể xúc phạm nhẹ — người gõ đã tự chấp nhận (biết hết mọi thứ).',
    4: 'TÍNH CÁCH >.<: chỉ nói về chuyện tình của Phong và NGƯỜI YÊU CỦA PHONG (ny là người yêu của Phong — KHÔNG phải bạn/bot là ny). Bạn chỉ là người buôn chuyện, ủng hộ cho vui; có thể nói những câu đen tối, lãng mạn; không bàn chuyện khác.',
}


def load_ai_doc():
    global AI_DOC
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'doc_extracted.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            AI_DOC = html.unescape(f.read())
    except Exception:
        AI_DOC = ''

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


def save_config():
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, ensure_ascii=False, indent=2)


def guild_settings(guild_id):
    gid = str(guild_id)
    if gid not in CONFIG['guilds']:
        CONFIG['guilds'][gid] = {'channel': [], 'search580': None, 'search880': None, 'ai_key': None, 'ai_persona': 1}
    gs = CONFIG['guilds'][gid]
    if not isinstance(gs.get('channel'), list):
        gs['channel'] = [gs['channel']] if gs.get('channel') else []
    return gs


def locked_channels(guild_id):
    return guild_settings(guild_id).get('channel', [])





def is_admin(message):
    author = message.author
    if not isinstance(author, discord.Member):
        return False
    return author.guild_permissions.administrator or author.guild_permissions.manage_guild


def parse(content):
    if not content.startswith(PREFIX):
        return None, ''
    rest = content[len(PREFIX):]
    m = re.match(r'([A-Za-z0-9_]+)\s*(.*)', rest, re.S)
    if not m:
        return None, ''
    return m.group(1).lower(), m.group(2)


def extract_id(text):
    m = re.search(r'\d+', text or '')
    return int(m.group()) if m else None


def miss_msg(cmd, usage):
    return f'⚠️ **Thiếu tham số** `{cmd}`! Cách dùng: `{usage}`'


def wrong_msg(cmd, detail, usage):
    return f'❌ **Sai** `{cmd}` ({detail})! Cách dùng: `{usage}`'


def clean_code(text):
    text = text.strip()
    lines = text.split('\n')
    if lines and lines[0].startswith('```'):
        rest = lines[0][3:].strip()
        if rest and not re.search(r'\s', rest) and not rest.endswith(':'):
            lines[0] = ''
        else:
            lines[0] = rest
    if lines:
        lines[-1] = lines[-1].replace('```', '').rstrip()
    text = '\n'.join(lines)
    return text.strip('\n')


async def read_image(attachment):
    data = await attachment.read()
    return Image.open(io.BytesIO(data))


# ---------------- HELP (3 trang + chọn trang) ----------------

def build_page_chung():
    embed = discord.Embed(title='📖 Lệnh chung', color=0x00aaff)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 1/7 - Chọn trang khác bên dưới để xem tiếp')
    embed.add_field(name=f'`{PREFIX}help`', value='Mở ra bảng hướng dẫn', inline=False)
    embed.add_field(name=f'`{PREFIX}ping`', value='Ping xem bot còn không', inline=False)
    embed.add_field(name=f'`{PREFIX}setchannel <kênh1> <kênh2> ...`', value='Thêm nhiều kênh được phép hoạt động vào danh sách (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}delchannel <số|id> [<số|id> ...]`', value='Xoá nhiều kênh khỏi danh sách theo số thứ tự hoặc id (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}listchannel`', value='Xem danh sách kênh đang được phép hoạt động', inline=False)
    embed.add_field(name=f'`{PREFIX}credit`', value='Giới thiệu', inline=False)
    return embed


def build_page_casio():
    embed = discord.Embed(title='🧮 Casio tools', color=0x00aaff)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 2/7')
    embed.add_field(name=f'`{PREFIX}comp580 <asm>`', value='Compiler asm theo model 580vnx', inline=False)
    embed.add_field(name=f'`{PREFIX}comp880 <asm>`', value='Compiler asm theo model 880btg', inline=False)
    embed.add_field(name=f'`{PREFIX}decomp <model> <hex>`', value='Decomp theo model (580 hoặc 880)', inline=False)
    embed.add_field(name=f'`{PREFIX}vd`', value='Đưa ra 1 bảng lựa chọn ví dụ về các hàm phổ biến', inline=False)
    embed.add_field(name=f'`{PREFIX}phantich <asm>`', value='Phân tích asm đã đưa (demo) - file .txt hoặc dán trực tiếp, Chỉ dành cho 580vnx', inline=False)
    embed.add_field(name=f'`{PREFIX}p2b <ảnh>`', value='Dịch ảnh sang trắng đen theo 192x63 và đưa hex ra theo dạng .txt', inline=False)
    embed.add_field(name=f'`{PREFIX}h2b <hex>`', value='Dịch hex sang ảnh trắng đen theo 192x63', inline=False)
    embed.add_field(name=f'`{PREFIX}pixel <XxX>`', value='Dịch ảnh sang hex theo kích cỡ tùy chỉnh (X tối đa 192x63), xuất ảnh + .txt', inline=False)
    embed.add_field(name=f'`{PREFIX}ganhex <hex>`', value='Gán hex đã đưa vào biến A, B, C', inline=False)
    embed.add_field(name=f'`{PREFIX}dichhex <580/880> <hex>`', value='Dịch hex sang token (580vnx/880btg)', inline=False)
    embed.add_field(name=f'`{PREFIX}set580 <id>`', value='Set id kênh bot sẽ tìm tin nhắn (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}set880 <id>`', value='Set id kênh bot sẽ tìm tin nhắn (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}find580 <từ khoá>`', value='Tìm tin nhắn trong kênh đã set từ c!set580', inline=False)
    embed.add_field(name=f'`{PREFIX}find880 <từ khoá>`', value='Tìm tin nhắn trong kênh đã set từ c!set880', inline=False)
    return embed


def build_page_games():
    embed = discord.Embed(title='🎮 Nối từ', color=0xff44aa)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 3/7 - Vui là chính 😎')
    embed.add_field(name=f'`{PREFIX}noitu`', value='Bắt đầu nối từ với từ ngẫu nhiên (`p!noitu 1` hoặc `p!noitu 2` chọn chế độ)', inline=False)
    embed.add_field(name=f'`{PREFIX}noitiep <1/2>`', value='Chọn chế độ: 1. Nối 1 lần (mỗi người chỉ nối 1 từ) / 2. Nối nhiều (nối liên tiếp)', inline=False)
    embed.add_field(name=f'`{PREFIX}dung`', value='Tạm dừng trò chơi tạm thời', inline=False)
    embed.add_field(name=f'`{PREFIX}tiep`', value='Tiếp tục trò chơi đang tạm dừng', inline=False)
    embed.add_field(name=f'`{PREFIX}stop`', value='Kết thúc cuộc chơi', inline=False)
    embed.add_field(name='📜 Luật chơi', value='- Nối bằng **từ ghép 2 tiếng** (2 từ, vd: con mèo → mèo mướp), **gõ đúng dấu**\n- Không đủ 2 từ / 3 từ trở lên → báo **Sai luật**\n- Trả lời đúng → ✅\n- Trả lời sai → ❌\n- Người đã nối rồi mà nối tiếp (chế độ 1 lần) → ⏳\n- Ai nối 1 từ không ai có từ tiếp theo nối được nữa → người đó **THẮNG** 🏆', inline=False)
    return embed


def build_page_ai():
    embed = discord.Embed(title='🤖 AI', color=0x7b68ee)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 4/7 - Nói chuyện với AI')
    embed.add_field(name=f'`{PREFIX}join`', value='Bot vào cuộc hội thoại, không cần ping hay reply', inline=False)
    embed.add_field(name=f'`{PREFIX}leave`', value='Bot rời cuộc hội thoại, cần ping hoặc reply', inline=False)
    embed.add_field(name=f'`{PREFIX}setkey <key>`', value='Set key', inline=False)
    embed.add_field(name=f'`{PREFIX}delkey`', value='Xoá key hiện tại', inline=False)
    embed.add_field(name=f'`{PREFIX}showkey`', value='Xem key hiện tại', inline=False)
    embed.add_field(name=f'`{PREFIX}models`', value='Xem danh sách model Gemini khả dụng với key', inline=False)
    embed.add_field(name=f'`{PREFIX}doitinhcach <1/2/3/4>`', value='Đổi tính cách AI (chung cả server): 1 Ngoan · 2 Láo · 3 Đcm · 4 >.<  (chuyện tình Phong & ny của Phong)', inline=False)
    embed.add_field(name='🧠 Model', value=f'`{AI_MODEL}` — Google Gemini (free). Lấy key tại aistudio.google.com/apikey, set bằng `{PREFIX}setkey`', inline=False)
    return embed


def build_page_pass():
    embed = discord.Embed(title='🔐 Password game', color=0xff9900)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 5/7')
    embed.add_field(name=f'`{PREFIX}pass <độ khó>`', value='Bắt đầu game (dễ / bình thường / khó / siêu khó)', inline=False)
    embed.add_field(name=f'`{PREFIX}trl <chuỗi>`', value='Gửi mật khẩu để kiểm tra điều kiện (chỉ người bắt đầu)', inline=False)
    embed.add_field(name=f'`{PREFIX}stoppass`', value='Dừng trò chơi', inline=False)
    embed.add_field(name='📜 Luật chơi', value='Bot đưa ra danh sách các điều kiện, gõ `p!trl` với mật khẩu đáp ứng hết là thắng. Riêng Siêu khó: làm hỏng điều kiện đã hoàn thành là thua.', inline=False)
    return embed


def build_page_chess():
    embed = discord.Embed(title='♟️ Cờ vua', color=0xccbb88)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 6/7')
    embed.add_field(name=f'`{PREFIX}chess <username> [trắng|đen|random]`', value='Thách đấu người chơi + chọn màu (mặc định random)', inline=False)
    embed.add_field(name=f'`{PREFIX}chessok`', value='Chấp nhận lời thách đấu', inline=False)
    embed.add_field(name=f'`{PREFIX}chessno`', value='Từ chối lời thách đấu', inline=False)
    embed.add_field(name=f'`{PREFIX}chessbot <độ khó> [trắng|đen|random]`', value='Chơi với bot + chọn màu (mặc định random). Độ khó: Dễ (100-400) · Bình thường (600-900) · Khó (1200-1600) · Siêu khó (2000-2400)', inline=False)
    embed.add_field(name='🎮 Khi đã vào trận', value='Gõ **không cần `p!`**:\n`move <nước>` — di chuyển cờ (vd: e2e4, Nf3, O-O)\n`ngung` — tạm dừng\n`tiep` — tiếp tục\n`thua` — đầu hàng', inline=False)
    embed.add_field(name='📌 Lưu ý', value='Các lệnh `move / ngung / tiep / thua` **chỉ dùng được khi đã vào trò chơi** — tin nhắn khác không ảnh hưởng.', inline=False)
    return embed


def build_page_google():
    embed = discord.Embed(title='🔍 Search tools', color=0x4285f4)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 7/7')
    embed.add_field(name=f'`{PREFIX}search <nội dung>`', value='Search web — 5 kết quả (tiêu đề + link + mô tả). Dùng DuckDuckGo, không cần key.', inline=False)
    embed.add_field(name=f'`{PREFIX}imgsearch <nội dung>`', value='Search ảnh — 3 ảnh thumbnail kèm link (không chiếm chỗ chat). Dùng Openverse, không cần key.', inline=False)
    embed.add_field(name='💡 Lưu ý', value='Hai lệnh này miễn phí và không cần cấu hình gì. Bấm link để xem nguồn gốc kết quả.', inline=False)
    return embed


class HelpSelect(discord.ui.Select):
    def __init__(self, pages):
        options = [
            discord.SelectOption(label='Lệnh chung', value='0', emoji='📖'),
            discord.SelectOption(label='Casio tools', value='1', emoji='🧮'),
            discord.SelectOption(label='Nối từ', value='2', emoji='🎮'),
            discord.SelectOption(label='AI', value='3', emoji='🤖'),
            discord.SelectOption(label='Password game', value='4', emoji='🔐'),
            discord.SelectOption(label='Cờ vua', value='5', emoji='♟️'),
            discord.SelectOption(label='Search tools', value='6', emoji='🔍'),
        ]
        super().__init__(placeholder='Chọn trang hướng dẫn', options=options, row=0)
        self.pages = pages

    async def callback(self, interaction):
        idx = int(self.values[0])
        await interaction.response.edit_message(embed=self.pages[idx], view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(pages))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


# ---------------- VÍ DỤ / TÀI LIỆU (vd) ----------------

class VdDocsSelect(discord.ui.Select):
    def __init__(self, options, placeholder):
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction):
        item = vd_docs.DATA[self.values[0]]
        text = item['content'] + '\n\n*Tài liệu soạn bởi @Bashamee*'
        chunks = vd_docs.chunk_text(text)
        await interaction.response.defer()
        await interaction.message.edit(content=chunks[0], embed=None, view=None)
        for c in chunks[1:]:
            await interaction.channel.send(c)


class VdDocsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        options = [
            discord.SelectOption(label=item['title'][:100], value=key)
            for key, item in vd_docs.DATA.items()
        ]
        self.add_item(VdDocsSelect(options, 'Chọn 1 mục để xem tài liệu...'))


# ---------------- LỆNH CHUNG ----------------

async def cmd_help(message, args):
    pages = [build_page_chung(), build_page_casio(), build_page_games(), build_page_ai(), build_page_pass(), build_page_chess(), build_page_google()]
    view = HelpView(pages)
    msg = await message.reply(embed=pages[0], view=view)
    view.message = msg


async def cmd_ping(message, args):
    ms = round(bot.latency * 1000)
    await message.reply(f'Pong! {ms}ms, Phong đang nhớ ny UwU')


def fmt_channel_list(guild, lst):
    lines = []
    for i, c in enumerate(lst, start=1):
        ch = guild.get_channel(c)
        label = ch.mention if ch else f'`{c}`'
        lines.append(f'{i}. {label}')
    return '\n'.join(lines)


async def cmd_setchannel(message, args):
    if not is_admin(message):
        await message.reply('❌ Chỉ có quyền admin mới dùng được lệnh này!')
        return
    ids = [int(x) for x in re.findall(r'\d+', args)]
    if not ids:
        await message.reply(miss_msg('setchannel', f'{PREFIX}setchannel <kênh1> <kênh2> ...'))
        return
    lst = locked_channels(message.guild.id)
    added = []
    already = []
    not_found = []
    for cid in ids:
        if cid in lst:
            already.append(cid)
            continue
        chan = message.guild.get_channel(cid)
        if not chan:
            not_found.append(cid)
            continue
        lst.append(cid)
        added.append(cid)
    save_config()
    parts = []
    if added:
        parts.append('Đã thêm: ' + ', '.join(f'<#{c}>' for c in added))
    if already:
        parts.append('Đã có sẵn: ' + ', '.join(f'<#{c}>' for c in already))
    if not_found:
        parts.append('Không tìm thấy: ' + ', '.join(f'`{c}`' for c in not_found))
    if not parts:
        await message.reply('❌ Không có kênh nào hợp lệ để thêm.')
        return
    reply = await message.reply(' | '.join(parts) + f' (tổng {len(lst)} kênh)')
    await reply.delete(delay=5)


async def cmd_delchannel(message, args):
    if not is_admin(message):
        await message.reply('❌ Chỉ có quyền admin mới dùng được lệnh này!')
        return
    lst = locked_channels(message.guild.id)
    if not lst:
        await message.reply('Danh sách kênh trống — bot đang hoạt động ở mọi kênh.')
        return
    if not args.strip():
        await message.reply(f'Cách dùng: `{PREFIX}delchannel <số|id> [<số|id> ...]`\n{fmt_channel_list(message.guild, lst)}')
        return
    removed = []
    for tok in args.split():
        if not tok.isdigit():
            continue
        n = int(tok)
        if 1 <= n <= len(lst):
            removed.append(lst.pop(n - 1))
        elif n in lst:
            lst.remove(n)
            removed.append(n)
    save_config()
    if removed:
        await message.reply('Đã xoá: ' + ', '.join(f'<#{c}>' for c in removed) + f' (còn {len(lst)} kênh).')
    else:
        await message.reply('Không tìm thấy kênh nào để xoá trong danh sách.')


async def cmd_listchannel(message, args):
    lst = locked_channels(message.guild.id)
    if not lst:
        await message.reply('Danh sách kênh trống — bot hoạt động ở mọi kênh.')
        return
    await message.reply('Các kênh bot được phép hoạt động:\n' + fmt_channel_list(message.guild, lst))


async def cmd_credit(message, args):
    text = ('Tools Bot\n'
            '----------------------------------\n'
            '► Ý TƯỞNG & PHÁT TRIỂN : Phong\n'
            '► KIẾN TRÚC AI CỐT LÕI  : DeepSeek AI\n'
            '----------------------------------\n'
            '© Được tạo ra bởi Phong & DeepSeek.')
    await message.reply(f'```\n{text}\n```')


# ---------------- CASIO TOOLS ----------------

async def cmd_comp580(message, args):
    await do_comp(message, args, '580')


async def cmd_comp880(message, args):
    await do_comp(message, args, '880')


async def do_comp(message, args, model):
    if not args:
        await message.reply(miss_msg(f'comp{model}', f'{PREFIX}comp{model} <asm>'))
        return
    asm = clean_code(args)
    try:
        async with message.channel.typing():
            hex_line, home, end, out, err = cl.compile_asm(model, asm)
    except subprocess.TimeoutExpired:
        await message.reply('❌ Compiler chạy quá lâu (>120s), thử lại nhé!')
        return
    except Exception as e:
        await message.reply(f'❌ Lỗi chạy compiler: `{e}`')
        return
    if hex_line is None:
        detail = '\n'.join((out + '\n' + err).strip().splitlines()[-25:])
        await message.reply(f'❌ Compile thất bại (model {model})\n```\n{detail[:1500]}\n```')
        return
    header = f'== 0x{home} -> 0x{end} =='
    sep = '================='
    spaced = ' '.join(hex_line[i:i + 2] for i in range(0, len(hex_line), 2))
    notes = [l for l in err.strip().splitlines() if l.strip()]
    note_block = '\n'.join(notes) if notes else ''
    if len(spaced) > 900:
        spaced = spaced[:900] + ' ...'
    if len(note_block) > 600:
        note_block = note_block[:600] + '\n...'
    text = f'{header}\n{sep}\n{spaced}\n{sep}'
    if note_block:
        text += '\n' + note_block
    await message.reply(f'```\n{text}\n```')


async def cmd_decomp(message, args):
    model = '580'
    hexstr = ''
    parts = args.split(None, 1) if args.strip() else []
    if parts:
        head = parts[0].lower().replace('vnx', '').replace('btg', '')
        if head in ('580', '880'):
            model = head
            hexstr = parts[1] if len(parts) > 1 else ''
        else:
            hexstr = args
    if not hexstr and message.attachments:
        att = message.attachments[0]
        if att.filename.lower().endswith('.txt'):
            hexstr = (await att.read()).decode('utf-8', errors='replace')
    clean_check = cl.clean_hex(hexstr)
    if not clean_check:
        await message.reply(miss_msg('decomp', f'{PREFIX}decomp <model> <hex>'))
        return
    hexstr = clean_check
    if len(hexstr) % 2 != 0:
        await message.reply(wrong_msg('decomp', 'hex phải có số ký tự chẵn', f'{PREFIX}decomp <model> <hex>'))
        return
    model_name = '580vnx' if model == '580' else '880btg'
    async with message.channel.typing():
        asm = cl.decomp_hex(model, hexstr)
    text = asm
    if len(text) > 1900:
        text = text[:1900] + '\n...'
    await message.reply(f'**Decomp ({model_name})**\n```\n{text}\n```')


async def cmd_vd(message, args):
    embed = discord.Embed(
        title='📚 Bảng lựa chọn tài liệu (vd)',
        description='Các hàm & kỹ thuật lập trình ROP cho Casio fx-580VN X.\nChọn 1 mục bên dưới để xem chi tiết.\n\n*Tài liệu soạn bởi @Bashamee*',
        color=0x00ccff)
    embed.set_footer(text=f'Tổng cộng {len(vd_docs.DATA)} mục')
    view = VdDocsView()
    await message.channel.send(embed=embed, view=view)


async def cmd_phantich(message, args):
    if not args and not message.attachments:
        await message.reply(miss_msg('phantich', f'{PREFIX}phantich <asm>'))
        return
    if message.attachments:
        att = message.attachments[0]
        text = (await att.read()).decode('utf-8', errors='replace')
    else:
        text = clean_code(args)
    if not text.strip():
        await message.reply('❌ Không có nội dung để phân tích.')
        return
    header = '★ PHÂN TÍCH ASM (580vnx) ★\n' + '═' * 30
    body = header + '\n' + cl.annotate_asm(text, '580')
    lines = body.split('\n')
    chunks = []
    cur = ''
    for ln in lines:
        if cur and len(cur) + len(ln) + 1 > 1500:
            chunks.append(cur)
            cur = ln
        else:
            cur = cur + '\n' + ln if cur else ln
    if cur:
        chunks.append(cur)
    await message.channel.send('```\n' + chunks[0] + '\n```')
    for c in chunks[1:]:
        await message.channel.send('```\n' + c + '\n```')


async def cmd_p2b(message, args):
    if not message.attachments:
        await message.reply(miss_msg('p2b', f'{PREFIX}p2b + ảnh đính kèm'))
        return
    att = message.attachments[0]
    if not att.content_type or not att.content_type.startswith('image/'):
        await message.reply(wrong_msg('p2b', 'đây không phải file ảnh', f'{PREFIX}p2b + ảnh đính kèm'))
        return
    try:
        async with message.channel.typing():
            img = await read_image(att)
            data = cl.image_to_hex_bytes(img)
            spaced_hex = data.hex(' ')
            ts = int(time.time())
            txt_path = cl.save_output(f'p2b_{ts}.txt', spaced_hex)
            preview = cl.hex_bytes_to_image(data).resize((192 * 4, 63 * 4), Image.NEAREST)
            png_path = os.path.join(cl.OUTPUT_DIR, f'p2b_{ts}.png')
            preview.save(png_path)
    except Exception as e:
        await message.reply(f'❌ Lỗi xử lý ảnh: `{e}`')
        return
    await message.reply(files=[discord.File(png_path), discord.File(txt_path)])


async def cmd_h2b(message, args):
    hexstr = cl.clean_hex(args)
    if not hexstr and message.attachments:
        att = message.attachments[0]
        if att.filename.lower().endswith('.txt'):
            content = (await att.read()).decode('utf-8', errors='replace')
            hexstr = cl.clean_hex(content)
    if not hexstr:
        await message.reply(miss_msg('h2b', f'{PREFIX}h2b <hex>'))
        return
    if len(hexstr) % 2 != 0:
        await message.reply(wrong_msg('h2b', 'hex phải có số ký tự chẵn', f'{PREFIX}h2b <hex>'))
        return
    try:
        async with message.channel.typing():
            data = bytes.fromhex(hexstr)
            img = cl.hex_bytes_to_image(data)
            png_path = os.path.join(cl.OUTPUT_DIR, f'h2b_{int(time.time())}.png')
            img.resize((192 * 4, 63 * 4), Image.NEAREST).save(png_path)
    except Exception as e:
        await message.reply(f'❌ Lỗi xử lý hex: `{e}`')
        return
    embed = discord.Embed(title='🖼️ Hex → Ảnh (192x63)', color=0x00ffcc)
    embed.add_field(name='Hex', value=f'{len(hexstr)} ký tự ({len(hexstr)//2} byte)', inline=False)
    await message.reply(embed=embed, file=discord.File(png_path))


async def cmd_pixel(message, args):
    if not message.attachments:
        await message.reply(miss_msg('pixel', f'{PREFIX}pixel <NxY> + ảnh (N = rộng, Y = cao)'))
        return
    att = message.attachments[0]
    if not att.content_type or not att.content_type.startswith('image/'):
        await message.reply(wrong_msg('pixel', 'đây không phải file ảnh', f'{PREFIX}pixel <NxY> + ảnh'))
        return
    m = re.match(r'^\s*(\d+)\s*[xX×]\s*(\d+)\s*$', args)
    if not m:
        await message.reply(wrong_msg('pixel', f'format `{args.strip() or "?"}` không phải NxY', f'{PREFIX}pixel <NxY> (VD 96x31)'))
        return
    w = int(m.group(1))
    h = int(m.group(2))
    if w < 1 or h < 1:
        await message.reply(wrong_msg('pixel', 'kích thước phải ≥ 1', f'{PREFIX}pixel <NxY>'))
        return
    if w > 192 or h > 63:
        await message.reply(wrong_msg('pixel', f'{w}x{h}: chiều rộng ≤ 192, chiều cao ≤ 63', f'{PREFIX}pixel <NxY>'))
        return
    try:
        async with message.channel.typing():
            img = await read_image(att)
            data = cl.image_to_hex_bytes_size(img, w, h)
            spaced_hex = data.hex(' ')
            ts = int(time.time())
            txt_path = cl.save_output(f'pixel_{ts}.txt', spaced_hex)
            factor = max(1, min(32, 768 // w))
            preview = cl.hex_bytes_to_image_size(data, w, h).resize((w * factor, h * factor), Image.NEAREST)
            png_path = os.path.join(cl.OUTPUT_DIR, f'pixel_{ts}.png')
            preview.save(png_path)
    except Exception as e:
        await message.reply(f'❌ Lỗi xử lý ảnh: `{e}`')
        return
    await message.reply(files=[discord.File(png_path), discord.File(txt_path)])


async def cmd_ganhex(message, args):
    cleaned = cl.clean_hex(args)
    if not cleaned:
        await message.reply(miss_msg('ganhex', f'{PREFIX}ganhex <hex>'))
        return
    if len(cleaned) % 2 != 0:
        await message.reply(wrong_msg('ganhex', 'hex phải có số ký tự chẵn', f'{PREFIX}ganhex <hex>'))
        return
    hexstr = cleaned
    out, byte_1 = cl.gan_hex(hexstr)
    text = out
    if byte_1:
        text += '\n\nSố byte cần gán: ' + ' '.join(byte_1)
    else:
        text += '\n\nKhông có byte để gán.'
    embed = discord.Embed(title='🧬 Gán hex (A/B/C)', color=0x66ccff)
    embed.add_field(name='Kết quả', value=f'```\n{text}\n```', inline=False)
    await message.reply(embed=embed)


async def cmd_dichhex(message, args):
    parts = args.split(None, 1) if args.strip() else []
    model = '580'
    hexstr = ''
    if parts:
        head = parts[0].lower().replace('vnx', '').replace('btg', '')
        if head in ('580', '880'):
            model = head
            hexstr = parts[1] if len(parts) > 1 else ''
        else:
            hexstr = args
    cleaned = cl.clean_hex(hexstr)
    if not cleaned:
        await message.reply(miss_msg('dichhex', f'{PREFIX}dichhex <580/880> <hex>'))
        return
    if len(cleaned) % 2 != 0:
        await message.reply(wrong_msg('dichhex', 'hex phải có số ký tự chẵn', f'{PREFIX}dichhex <580/880> <hex>'))
        return
    model_name = '580vnx' if model == '580' else '880btg'
    result = cl.hex_to_tokens(model, hexstr)
    if len(result) > 1900:
        result = result[:1900] + '\n...'
    embed = discord.Embed(title=f'🔤 Hex → Token ({model_name})', color=0xffcc66)
    embed.add_field(name='Kết quả', value=f'```\n{result}\n```', inline=False)
    await message.reply(embed=embed)


async def cmd_set580(message, args):
    await do_setsearch(message, args, 'search580', '580')


async def cmd_set880(message, args):
    await do_setsearch(message, args, 'search880', '880')


async def do_setsearch(message, args, key, model):
    if not is_admin(message):
        await message.reply('❌ Chỉ có quyền admin mới dùng được lệnh này!')
        return
    cid = extract_id(args)
    if not cid:
        await message.reply(miss_msg(f'set{model}', f'{PREFIX}set{model} <id>'))
        return
    chan = message.guild.get_channel(cid)
    if not chan:
        await message.reply(wrong_msg(f'set{model}', 'không tìm thấy kênh có id đó', f'{PREFIX}set{model} <id>'))
        return
    guild_settings(message.guild.id)[key] = cid
    save_config()
    reply = await message.reply(f'Đã set kênh tìm tin nhắn → <#{cid}>')
    await reply.delete(delay=5)


async def cmd_find580(message, args):
    await do_find(message, args, 'search580', '580')


async def cmd_find880(message, args):
    await do_find(message, args, 'search880', '880')


async def do_find(message, args, key, model):
    cid = guild_settings(message.guild.id).get(key)
    if not cid:
        await message.reply(f'⚠️ **Thiếu**: chưa set kênh tìm tin nhắn cho {model}. Dùng `{PREFIX}set{model} <id>` trước.')
        return
    chan = bot.get_channel(cid)
    if not chan:
        await message.reply(wrong_msg(f'find{model}', 'kênh đã set không tồn tại', f'{PREFIX}set{model} <id> lại'))
        return
    kw = args.strip()
    if not kw:
        await message.reply(miss_msg(f'find{model}', f'{PREFIX}find{model} <từ khoá>'))
        return
    found = []
    async with message.channel.typing():
        async for m in chan.history(limit=1000):
            if kw.lower() in (m.content or '').lower():
                found.append(m)
                if len(found) >= 20:
                    break
    if not found:
        await message.reply(f'Không tìm thấy tin nhắn nào chứa cụm từ \'{kw}\' trong kênh <#{cid}>.')
        return
    lines = [f'- https://discord.com/channels/{message.guild.id}/{chan.id}/{m.id}' for m in found]
    extra = ''
    if len(found) >= 20:
        extra = '\n... (có thể còn nhiều kết quả khác)'
    text = f'Tìm thấy {len(found)} guide chứa cụm từ \'{kw}\':\n' + '\n'.join(lines) + extra
    await message.reply(text)


GAMES = {}
MK_GAMES = {}


async def cmd_pass(message, args):
    level = matkhau.parse_level(args)
    if not level:
        await message.reply(wrong_msg('pass', f'độ khó `{args.strip() or "?"}` không hợp lệ', 'p!pass <dễ|bình thường|khó|siêu khó>'))
        return
    if not matkhau.LEVELS[level]['rule_ids']:
        await message.reply(f'🔒 Chế độ **{matkhau.LEVELS[level]["label"]}** chưa ra mắt. Bản hiện tại chỉ có **Easy (Dễ)**.')
        return
    rules, data = matkhau.start(level)
    ch = str(message.channel.id)
    MK_GAMES[ch] = {'level': level, 'rules': rules, 'data': data, 'starter': message.author.id, 'passed': set(), 'count': 0}
    lines = [
        f'🔐 **Password game — {matkhau.LEVELS[level]["label"]}** ({len(rules)} điều kiện)',
        f'Người chơi: <@{message.author.id}> — gửi mật khẩu bằng `p!trl <chuỗi>`.',
        'Các điều kiện:',
    ]
    for idx, r in enumerate(rules, start=1):
        lines.append(f'**{idx}.** {r["name"]}')
    for chunk in vd_docs.chunk_text('\n'.join(lines)):
        await message.channel.send(chunk)


async def cmd_trl(message, args):
    ch = str(message.channel.id)
    g = MK_GAMES.get(ch)
    if not g:
        await message.reply('Không có trò chơi nào đang chạy. Gõ `p!pass <độ khó>` để bắt đầu.')
        return
    if message.author.id != g['starter']:
        await message.reply(f'Chỉ <@{g["starter"]}> được chơi thôi! (người bắt đầu game)')
        return
    pw = args
    if not pw and message.attachments:
        att = message.attachments[0]
        if att.filename.lower().endswith('.txt'):
            pw = (await att.read()).decode('utf-8', errors='replace').strip()
    if not pw:
        await message.reply(miss_msg('trl', 'p!trl <chuỗi mật khẩu> hoặc đính kèm file .txt'))
        return
    res = matkhau.check(pw, g['rules'], g['passed'], g.get('data', {}))
    if g['level'] == 'hardcore' and res['lost']:
        MK_GAMES.pop(ch, None)
        await message.reply('💥 Bạn đã làm hỏng một điều kiện đã hoàn thành trước đó!\n**Bạn đã thua**, p!pass <độ khó> để chơi lại.')
        return
    g['passed'] = res['passed']
    g['count'] += 1
    if res['ok']:
        MK_GAMES.pop(ch, None)
        await message.reply(f'🏆 Chính xác! <@{message.author.id}> đã tìm ra mật khẩu đáp ứng mọi điều kiện (sau {g["count"]} lần gửi).')
        return
    pos, name = res['missing'][0]
    text = f'Password thiếu điều kiện {pos}: {name}'
    if len(res['missing']) > 1:
        more = [f'{i}. {n}' for i, n in res['missing']]
        text += '\n\nTất cả điều kiện đang thiếu:\n' + '\n'.join(more)
    await message.reply(text)


async def cmd_stoppass(message, args):
    g = MK_GAMES.pop(str(message.channel.id), None)
    if not g:
        await message.reply('Không có trò chơi nào để dừng.')
        return
    await message.reply(f'<@{g["starter"]}> đã chịu thua, gà!')


async def cmd_noitu(message, args):
    mode = 1
    a = args.strip().lower()
    if a in ('2', 'nhieu', 'nhiều'):
        mode = 2
    start = noitu.pick_start()
    start_base_words = [b for b in (noitu.canon(t) for t in start.split()) if len(b) >= 2]
    need_base = start_base_words[-1]
    last_start = start.split()[-1]
    GAMES[str(message.channel.id)] = {
        'need_word': need_base,
        'need_word_d': last_start,
        'used': {' '.join(start_base_words)},
        'last_player': None,
        'paused': False,
        'mode': mode,
        'count': 1,
    }
    mode_name = 'Nối 1 lần' if mode == 1 else 'Nối nhiều'
    embed = discord.Embed(title='🎮 Nối từ', color=0xff44aa)
    embed.add_field(name='🔤 Từ đầu', value=f'**{start}**', inline=False)
    embed.add_field(name='➡️ Nối tiếp từ', value=f'Bắt đầu bằng từ **{last_start}**', inline=False)
    embed.add_field(name='⚙️ Chế độ', value=mode_name, inline=False)
    embed.set_footer(text=f'{PREFIX}noitiep 1/2 đổi chế độ | {PREFIX}dung | {PREFIX}tiep | {PREFIX}stop')
    await message.reply(embed=embed)


async def cmd_noitiep(message, args):
    g = GAMES.get(str(message.channel.id))
    a = args.strip().lower()
    if g is None:
        await message.reply(f'Chưa có trò chơi nào ở kênh này. Gõ `{PREFIX}noitu` để bắt đầu!\n\nCó 2 chế độ:\n1. **Nối 1 lần** - mỗi người chỉ nối 1 từ, chờ người khác nối tiếp\n2. **Nối nhiều** - nối được nhiều từ liên tiếp\nDùng `{PREFIX}noitu 1` hoặc `{PREFIX}noitu 2` để chọn.')
        return
    if a in ('2', 'nhieu', 'nhiều'):
        g['mode'] = 2
        await message.reply('✅ Đã đổi sang chế độ **Nối nhiều** - nối được nhiều từ liên tiếp!')
    elif a in ('1', 'mot', 'một', 'lan', 'lần'):
        g['mode'] = 1
        await message.reply('✅ Đã đổi sang chế độ **Nối 1 lần** - mỗi người chỉ nối 1 từ, chờ người khác!')
    else:
        await message.reply('Có 2 chế độ:\n1. **Nối 1 lần** - mỗi người chỉ nối 1 từ\n2. **Nối nhiều** - nối được nhiều từ liên tiếp\n\nĐổi chế độ bằng `p!noitiep 1` hoặc `p!noitiep 2`.')


async def cmd_dung(message, args):
    g = GAMES.get(str(message.channel.id))
    if not g:
        await message.reply('Không có trò nối từ nào đang hoạt động.')
        return
    if g['paused']:
        await message.reply('⏸️ Trò chơi đang được tạm dừng rồi.')
        return
    g['paused'] = True
    await message.reply('⏸️ Tạm dừng trò chơi! Gõ `p!tiep` để tiếp tục.')


async def cmd_tiep(message, args):
    g = GAMES.get(str(message.channel.id))
    if not g:
        await message.reply('Không có trò nối từ nào đang hoạt động.')
        return
    if not g['paused']:
        await message.reply('⏩ Trò chơi vẫn đang chạy mà!')
        return
    g['paused'] = False
    await message.reply(f'▶️ Tiếp tục! Nối tiếp bằng từ **{g["need_word_d"]}**.')


async def cmd_stop(message, args):
    if GAMES.pop(str(message.channel.id), None):
        await message.reply('🏁 Đã kết thúc trò nối từ!')
    else:
        await message.reply('Không có trò nối từ nào để kết thúc.')


async def handle_noitu_move(message):
    ch = str(message.channel.id)
    g = GAMES.get(ch)
    if not g or g['paused']:
        return
    content = message.content.strip()
    tokens = content.split()
    if not tokens:
        return
    if not all(t.isalpha() for t in tokens):
        return
    if len(tokens) != 2:
        try:
            await message.add_reaction('❌')
        except Exception:
            pass
        await message.reply(f'⚠️ **Sai luật**: phải nối từ ghép **2 tiếng** (2 từ, vd: `mèo mướp`)!')
        return
    base = [t for t in (noitu.canon(x) for x in tokens) if len(t) >= 2]
    if len(base) != 2:
        try:
            await message.add_reaction('❌')
        except Exception:
            pass
        await message.reply('❌ Không hợp lệ — cần từ ghép đủ 2 tiếng có nghĩa (vd: `mèo mướp`).')
        return
    phrase = ' '.join(base)
    if g['mode'] == 1 and g['last_player'] == message.author.id:
        try:
            await message.add_reaction('⏳')
        except Exception:
            pass
        return
    if phrase in g['used'] or phrase not in noitu.PHRASES or base[0] != g['need_word']:
        try:
            await message.add_reaction('❌')
        except Exception:
            pass
        return
    try:
        await message.add_reaction('✅')
    except Exception:
        pass
    g['used'].add(phrase)
    g['need_word'] = base[-1]
    g['need_word_d'] = tokens[-1]
    g['last_player'] = message.author.id
    g['count'] += 1
    if not noitu.can_continue(g['need_word'], g['used']):
        await message.reply(f'🏆 **{message.author.display_name}** thắng! Không còn từ nào nối được sau từ **{g["need_word_d"]}**. Tổng cộng **{g["count"]}** từ đã nối. 🎉')
        GAMES.pop(ch, None)
        return
    await message.reply(f'➡️ **{content}** → nối tiếp bằng từ **{g["need_word_d"]}**')


async def discover_models(key):
    try:
        url = AI_BASE.rstrip('/') + '/models'
        async with aiohttp.ClientSession() as session:
            async with session.get(url,
                                   headers={'Authorization': 'Bearer ' + key},
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        return [m.get('id') for m in data.get('data', []) if m.get('id')]
    except Exception:
        return []


async def ai_chat(key, messages):
    url = AI_BASE.rstrip('/') + '/chat/completions'
    model = AI_MODEL
    last_err = None
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        json={'model': model, 'messages': messages},
                        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
                        timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status in (429, 503):
                        last_err = f'HTTP {resp.status}: quá tải (lần {attempt + 1}/3)...'
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    if resp.status == 404:
                        last_err = f'Model {model} không khả dụng'
                        break
                    if resp.status != 200:
                        raise RuntimeError(f'HTTP {resp.status}: {(await resp.text())[:250]}')
                    data = await resp.json()
            try:
                return data['choices'][0]['message']['content']
            except Exception:
                raise RuntimeError(f'Response thiếu nội dung: {str(data)[:200]}')
        except asyncio.TimeoutError:
            last_err = 'API phản hồi quá chậm (>45s), thử lại...'
            await asyncio.sleep(5 * (attempt + 1))
        except aiohttp.ClientError as e:
            last_err = f'Kết nối API thất bại: {e}'
            await asyncio.sleep(5 * (attempt + 1))
    discovered = await discover_models(key)
    ordered = [m for m in discovered if 'flash' in m] + [m for m in discovered if 'flash' not in m]
    for m in ordered[:10]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        json={'model': m, 'messages': messages},
                        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
                        timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        except Exception:
            continue
    if discovered:
        raise RuntimeError((last_err or 'Không thể gọi API AI.') + '\nModel khả dụng: ' + ', '.join(discovered[:10]))
    raise RuntimeError(last_err or 'Không thể gọi API AI.')


async def cmd_ai_join(message, args):
    ch = message.channel.id
    AI_CHANNELS.add(ch)
    AI_HISTORY.setdefault(ch, [])
    await message.reply('🤖 Bot đã vào hội thoại! Từ giờ nói chuyện trong kênh này **không cần ping hay reply**. (Muốn rời: p!leave)')


async def cmd_ai_leave(message, args):
    ch = message.channel.id
    AI_CHANNELS.discard(ch)
    AI_HISTORY.pop(ch, None)
    AI_NOKEY_ONCE.discard(ch)
    await message.reply('👋 Bot đã rời hội thoại! Muốn nói chuyện thì **ping @bot hoặc reply tin của bot** nhé.')


async def cmd_ai_setkey(message, args):
    key = args.strip()
    if not key:
        await message.reply(miss_msg('setkey', 'p!setkey <key>'))
        return
    guild_settings(message.guild.id)['ai_key'] = key
    save_config()
    await message.reply('✅ Đã lưu key cho server này.')


async def cmd_ai_delkey(message, args):
    guild_settings(message.guild.id)['ai_key'] = None
    save_config()
    await message.reply('🗑️ Đã xoá key hiện tại.')


async def cmd_ai_showkey(message, args):
    key = guild_settings(message.guild.id).get('ai_key') or AI_KEY
    if key:
        masked = key[:8] + '*' * min(12, max(0, len(key) - 8))
    else:
        masked = 'Chưa có key'
    await message.reply(f'🔑 Key: `{masked}`\n🧠 Model: `{AI_MODEL}`\n🌐 API: `{AI_BASE}`')


async def cmd_ai_models(message, args):
    key = guild_settings(message.guild.id).get('ai_key') or AI_KEY
    if not key:
        await message.reply('Chưa có key (`p!setkey`) để liệt kê model.')
        return
    ids = await discover_models(key)
    if not ids:
        await message.reply('❌ Không lấy được danh sách model.')
        return
    await message.reply('🧠 Model khả dụng:\n' + '\n'.join(ids[:30]) + ('\n...' if len(ids) > 30 else ''))


async def cmd_doitinhcach(message, args):
    a = args.strip()
    names = {1: 'Ngoan', 2: 'Láo', 3: 'Đcm', 4: '>.<'}
    if not a:
        await message.reply('Các tính cách AI (áp dụng chung cho cả server):\n'
                            '1. **Ngoan** — lịch sự, đúng mực, không chửi (mặc định)\n'
                            '2. **Láo** — hơi láo, chọc ghẹo, không xúc phạm nặng\n'
                            '3. **Đcm** — rất láo, chửi tục, có thể xúc phạm (người dùng tự chịu trách nhiệm)\n'
                            '4. **>.<** — chỉ nói chuyện tình của Phong & **ny của Phong** (bot không phải ny), có thể đen tối\n'
                            f'Dùng `{PREFIX}doitinhcach <1/2/3/4>` để chọn.')
        return
    if a not in ('1', '2', '3', '4'):
        await message.reply(wrong_msg('doitinhcach', f'`{a}` không hợp lệ', 'p!doitinhcach <1/2/3/4>'))
        return
    n = int(a)
    guild_settings(message.guild.id)['ai_persona'] = n
    save_config()
    await message.reply(f'✅ Đã đổi tính cách AI thành **{names[n]}** — áp dụng cho cả server.')


async def handle_ai_message(message):
    if message.author.bot or not message.guild:
        return
    name, _ = parse(message.content)
    if name is not None:
        return
    ch = message.channel.id
    joined = ch in AI_CHANNELS
    mentioned = bot.user in message.mentions
    replied_bot = bool(message.reference and message.reference.resolved
                       and message.reference.resolved.author == bot.user)
    if not (joined or mentioned or replied_bot):
        return
    key = guild_settings(message.guild.id).get('ai_key') or AI_KEY
    if not key:
        if ch not in AI_NOKEY_ONCE:
            AI_NOKEY_ONCE.add(ch)
            await message.reply('🔑 Chưa set key AI cho server. Dùng `p!setkey <key>` để nói chuyện với AI.')
        return
    user_text = message.content
    if mentioned:
        user_text = re.sub(r'<@!?(\d+)>', '', user_text).strip()
    author_name = message.author.display_name or message.author.name
    hist = AI_HISTORY.setdefault(ch, [])
    hist = (hist + [{'role': 'user', 'content': f'[{author_name}]: {user_text}'}])[-AI_HISTORY_LEN:]
    persona = guild_settings(message.guild.id).get('ai_persona', 1)
    sys_base = ('Bạn là Casiobot - bot Discord tiếng Việt. Trả lời ngắn gọn, tự nhiên bằng tiếng Việt. '
                + PERSONAS.get(persona, PERSONAS[1]) + ' '
                'MỖI TIN NHẮN CỦA NGƯỜI DÙNG CÓ DẠNG [Tên]: nội dung — nhiều người có thể nhắn chung, hãy PHÂN BIỆT ai nói gì và trả lời đúng người. '
                'TRẢ LỜI ĐÚNG KIỂU CHAT DISCORD: không dùng LaTeX ($..$, $$..$$), không dùng HTML/markdown math, '
                'không đóng khung công thức kiểu Google, dùng kí tự thường (vd H2O chứ không phải $H_2O$), '
                'hạn chế tối đa emoji (chỉ 0-1 khi thật cần), không quá dài dòng.')
    msgs = [{'role': 'system', 'content': sys_base}] + hist
    try:
        async with message.channel.typing():
            reply = await ai_chat(key, msgs)
    except Exception as e:
        await message.reply(f'❌ Lỗi AI: `{e}`')
        AI_HISTORY.pop(ch, None)
        return
    AI_HISTORY[ch] = (hist + [{'role': 'assistant', 'content': reply}])[-AI_HISTORY_LEN:]
    chunks = vd_docs.chunk_text(reply)
    await message.reply(chunks[0])
    for c in chunks[1:]:
        await message.channel.send(c)


async def cmd_chess(message, args):
    await chessbot.cmd_chess(message, args, PREFIX)


async def cmd_chessok(message, args):
    await chessbot.cmd_chessok(message, args, PREFIX)


async def cmd_chessno(message, args):
    await chessbot.cmd_chessno(message, args, PREFIX)


async def cmd_chessbot(message, args):
    await chessbot.cmd_chessbot(message, args, PREFIX)


async def cmd_gsearch(message, args):
    if not args.strip():
        await message.reply(miss_msg('search', 'p!search <nội dung>'))
        return
    query = args.strip()
    try:
        results = await gsearch.search_web_free(query)
    except Exception as e:
        await message.reply(f'❌ Lỗi tìm kiếm: `{e}`')
        return
    if not results:
        await message.reply('Không tìm thấy kết quả cho: `' + query + '`')
        return
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(f'**{i}. {r["title"]}**\n{r["link"]}\n{r["snippet"]}')
    chunks = vd_docs.chunk_text('\n\n'.join(lines))
    await message.reply(chunks[0])
    for c in chunks[1:]:
        await message.channel.send(c)


async def cmd_imgsearch(message, args):
    if not args.strip():
        await message.reply(miss_msg('imgsearch', 'p!imgsearch <nội dung>'))
        return
    query = args.strip()
    try:
        results = await gsearch.search_images_free(query)
    except Exception as e:
        await message.reply(f'❌ Lỗi tìm ảnh: `{e}`')
        return
    if not results:
        await message.reply('Không tìm thấy ảnh cho: `' + query + '`')
        return
    files = []
    links = []
    for r in results:
        links.append(f"**{r['title']}**\n{r['link']}")
        if r.get('thumb'):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(r['thumb'], headers={'User-Agent': gsearch.UA},
                                     timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            continue
                        raw = await resp.read()
                with Image.open(io.BytesIO(raw)) as im:
                    im.thumbnail((400, 400))
                    buf = io.BytesIO()
                    im.convert('RGB').save(buf, format='JPEG', quality=85)
                    files.append(discord.File(io.BytesIO(buf.getvalue()), filename='img.jpg'))
            except Exception:
                pass
    chunks = vd_docs.chunk_text('\n\n'.join(links))
    if used_free:
        text = '🔍 (chế độ free — Openverse)\n\n' + text
    chunks = vd_docs.chunk_text(text)
    await message.reply(chunks[0], files=files)
    for c in chunks[1:]:
        await message.channel.send(c)


COMMANDS = {
    'help': cmd_help,
    'ping': cmd_ping,
    'setchannel': cmd_setchannel,
    'delchannel': cmd_delchannel,
    'listchannel': cmd_listchannel,
    'credit': cmd_credit,
    'comp580': cmd_comp580,
    'comp880': cmd_comp880,
    'decomp': cmd_decomp,
    'vd': cmd_vd,
    'phantich': cmd_phantich,
    'p2b': cmd_p2b,
    'h2b': cmd_h2b,
    'pixel': cmd_pixel,
    'ganhex': cmd_ganhex,
    'dichhex': cmd_dichhex,
    'set580': cmd_set580,
    'set880': cmd_set880,
    'find580': cmd_find580,
    'find880': cmd_find880,
    'noitu': cmd_noitu,
    'noitiep': cmd_noitiep,
    'dung': cmd_dung,
    'tiep': cmd_tiep,
    'stop': cmd_stop,
    'join': cmd_ai_join,
    'leave': cmd_ai_leave,
    'setkey': cmd_ai_setkey,
    'delkey': cmd_ai_delkey,
    'showkey': cmd_ai_showkey,
    'models': cmd_ai_models,
    'doitinhcach': cmd_doitinhcach,
    'pass': cmd_pass,
    'trl': cmd_trl,
    'stoppass': cmd_stoppass,
    'chess': cmd_chess,
    'chessok': cmd_chessok,
    'chessno': cmd_chessno,
    'chessbot': cmd_chessbot,
    'search': cmd_gsearch,
    'imgsearch': cmd_imgsearch,
}


_web_started = False


@bot.event
async def on_ready():
    global _web_started
    print(f'Đăng nhập thành công! Bot: {bot.user} (ID: {bot.user.id})')
    print(f'Số server: {len(bot.guilds)}')
    for g in bot.guilds:
        print(f'  - {g.name} ({g.id})')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{PREFIX}help'))
    if web is not None and not _web_started:
        _web_started = True
        asyncio.create_task(web_main())


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    name, args = parse(message.content)
    if name is None:
        if await chessbot.handle_bare_chat(message, PREFIX):
            return
        await handle_noitu_move(message)
        await handle_ai_message(message)
        return
    channels = locked_channels(message.guild.id)
    if channels and message.channel.id not in channels:
        names = ', '.join(f'<#{c}>' for c in channels)
        reply = await message.reply(f'Bot chỉ hoạt động ở kênh {names} thôi!')
        await reply.delete(delay=5)
        return
    handler = COMMANDS.get(name)
    if handler:
        try:
            await handler(message, args)
        except Exception as e:
            await message.reply(f'❌ Có lỗi: `{e}`')


async def web_main():
    if web is None:
        return
    async def handle(_request):
        return web.Response(text='Casiobot đang chạy 👍')
    port = int(os.getenv('PORT', '8080'))
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/ping', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'Web server (keep-alive) chạy trên port {port}')


if __name__ == '__main__':
    cl.ensure_output_dir()
    noitu.load()
    if not TOKEN:
        print('❌ Thiếu token (đặt biến môi trường TOKEN hoặc sửa config.json)')
    else:
        bot.run(TOKEN)
