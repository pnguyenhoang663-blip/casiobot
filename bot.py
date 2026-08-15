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
        CONFIG['guilds'][gid] = {'channel': None, 'search580': None, 'search880': None, 'ai_key': None}
    return CONFIG['guilds'][gid]


def locked_channel_id(guild_id):
    return guild_settings(guild_id).get('channel')


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
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 1/4 - Chọn trang khác bên dưới để xem tiếp')
    embed.add_field(name=f'`{PREFIX}help`', value='Mở ra bảng hướng dẫn', inline=False)
    embed.add_field(name=f'`{PREFIX}ping`', value='Ping xem bot còn không', inline=False)
    embed.add_field(name=f'`{PREFIX}setchannel <id>`', value='Set kênh bot chỉ được hoạt động tại kênh đó (Chỉ có quyền admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}delchannel`', value='Xoá id kênh đó và bot có thể hoạt động ở mọi kênh (Chỉ có quyền admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}credit`', value='Giới thiệu', inline=False)
    return embed


def build_page_casio():
    embed = discord.Embed(title='🧮 Casio tools', color=0x00aaff)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 2/4')
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
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 3/4 - Vui là chính 😎')
    embed.add_field(name=f'`{PREFIX}noitu`', value='Bắt đầu nối từ với từ ngẫu nhiên (`p!noitu 1` hoặc `p!noitu 2` chọn chế độ)', inline=False)
    embed.add_field(name=f'`{PREFIX}noitiep <1/2>`', value='Chọn chế độ: 1. Nối 1 lần (mỗi người chỉ nối 1 từ) / 2. Nối nhiều (nối liên tiếp)', inline=False)
    embed.add_field(name=f'`{PREFIX}dung`', value='Tạm dừng trò chơi tạm thời', inline=False)
    embed.add_field(name=f'`{PREFIX}tiep`', value='Tiếp tục trò chơi đang tạm dừng', inline=False)
    embed.add_field(name=f'`{PREFIX}stop`', value='Kết thúc cuộc chơi', inline=False)
    embed.add_field(name='📜 Luật chơi', value='- Nối tiếp bằng **từ cuối** của cụm trước (vd: con mèo → mèo mướp)\n- Trả lời đúng → ✅\n- Trả lời sai → ❌\n- Người đã nối rồi mà nối tiếp (chế độ 1 lần) → ⏳\n- Ai nối 1 từ không ai có từ tiếp theo nối được nữa → người đó **THẮNG** 🏆', inline=False)
    return embed


def build_page_ai():
    embed = discord.Embed(title='🤖 AI', color=0x7b68ee)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 4/4 - Nói chuyện với AI')
    embed.add_field(name=f'`{PREFIX}join`', value='Bot vào cuộc hội thoại, không cần ping hay reply', inline=False)
    embed.add_field(name=f'`{PREFIX}leave`', value='Bot rời cuộc hội thoại, cần ping hoặc reply', inline=False)
    embed.add_field(name=f'`{PREFIX}setkey <key>`', value='Set key', inline=False)
    embed.add_field(name=f'`{PREFIX}delkey`', value='Xoá key hiện tại', inline=False)
    embed.add_field(name=f'`{PREFIX}showkey`', value='Xem key hiện tại', inline=False)
    embed.add_field(name=f'`{PREFIX}models`', value='Xem danh sách model Gemini khả dụng với key', inline=False)
    embed.add_field(name='🧠 Model', value=f'`{AI_MODEL}` — Google Gemini (free). Lấy key tại aistudio.google.com/apikey, set bằng `{PREFIX}setkey`', inline=False)
    return embed


class HelpSelect(discord.ui.Select):
    def __init__(self, pages):
        options = [
            discord.SelectOption(label='Lệnh chung', value='0', emoji='📖'),
            discord.SelectOption(label='Casio tools', value='1', emoji='🧮'),
            discord.SelectOption(label='Nối từ', value='2', emoji='🎮'),
            discord.SelectOption(label='AI', value='3', emoji='🤖'),
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
    pages = [build_page_chung(), build_page_casio(), build_page_games(), build_page_ai()]
    view = HelpView(pages)
    msg = await message.reply(embed=pages[0], view=view)
    view.message = msg


async def cmd_ping(message, args):
    ms = round(bot.latency * 1000)
    await message.reply(f'Pong! {ms}ms, Phong đang nhớ ny UwU')


async def cmd_setchannel(message, args):
    if not is_admin(message):
        await message.reply('❌ Chỉ có quyền admin mới dùng được lệnh này!')
        return
    cid = extract_id(args)
    if not cid:
        await message.reply(f'Cách dùng: `{PREFIX}setchannel <id>`')
        return
    chan = message.guild.get_channel(cid)
    if not chan:
        await message.reply('❌ Không tìm thấy kênh có id đó!')
        return
    guild_settings(message.guild.id)['channel'] = cid
    save_config()
    reply = await message.reply(f'Từ giờ bot chỉ hoạt động ở kênh <#{cid}>')
    await reply.delete(delay=5)


async def cmd_delchannel(message, args):
    if not is_admin(message):
        await message.reply('❌ Chỉ có quyền admin mới dùng được lệnh này!')
        return
    guild_settings(message.guild.id)['channel'] = None
    save_config()
    await message.reply('Đã xoá kênh, bot hoạt động ở mọi kênh!')


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
        await message.reply(f'Cách dùng: `{PREFIX}comp{model} <asm>`\nCó thể dán code asm trong khối ```asm ... ```')
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
    hexstr = cl.clean_hex(hexstr)
    if not hexstr or len(hexstr) % 2 != 0:
        await message.reply(f'Cách dùng: `{PREFIX}decomp <model> <hex>` (model: 580 hoặc 880)\nHoặc đính kèm file .txt chứa hex.')
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
        await message.reply(f'Cách dùng: `{PREFIX}phantich <asm>` hoặc đính kèm file .txt chứa asm.')
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
        await message.reply(f'Cách dùng: `{PREFIX}p2b` kèm theo 1 ảnh (đính kèm).')
        return
    att = message.attachments[0]
    if not att.content_type or not att.content_type.startswith('image/'):
        await message.reply('❌ Đây không phải file ảnh.')
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
    if not hexstr or len(hexstr) % 2 != 0:
        await message.reply(f'Cách dùng: `{PREFIX}h2b <hex>` hoặc đính kèm file .txt chứa hex.')
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
        await message.reply(f'Cách dùng: `{PREFIX}pixel <XxX>` kèm theo 1 ảnh. VD: `{PREFIX}pixel 96x31`')
        return
    att = message.attachments[0]
    if not att.content_type or not att.content_type.startswith('image/'):
        await message.reply('❌ Đây không phải file ảnh.')
        return
    m = re.match(r'^\s*(\d+)\s*[xX×]\s*(\d+)\s*$', args)
    if not m:
        await message.reply(f'Cách dùng: `{PREFIX}pixel <XxX>` - VD: `{PREFIX}pixel 96x31`')
        return
    w = int(m.group(1))
    h = int(m.group(2))
    if w < 1 or h < 1:
        await message.reply('❌ Kích thước phải ≥ 1.')
        return
    if w > 192 or h > 63:
        await message.reply('❌ Kích thước tối đa 192x63.')
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
    hexstr = cl.clean_hex(args)
    if not hexstr or len(hexstr) % 2 != 0:
        await message.reply(f'Cách dùng: `{PREFIX}ganhex <hex>`')
        return
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
    if not cleaned or len(cleaned) % 2 != 0:
        await message.reply(f'Cách dùng: `{PREFIX}dichhex <580/880> <hex>`')
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
        await message.reply(f'Cách dùng: `{PREFIX}set{model} <id>`')
        return
    chan = message.guild.get_channel(cid)
    if not chan:
        await message.reply('❌ Không tìm thấy kênh có id đó!')
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
        await message.reply(f'Chưa set kênh! Dùng `{PREFIX}set{model} <id>` trước.')
        return
    chan = bot.get_channel(cid)
    if not chan:
        await message.reply('❌ Kênh đã set không tồn tại.')
        return
    kw = args.strip()
    if not kw:
        await message.reply(f'Cách dùng: `{PREFIX}find{model} <từ khoá>`')
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
    if not tokens or len(tokens) > 2:
        return
    base = [t for t in (noitu.canon(x) for x in tokens) if len(t) >= 2]
    if not base:
        return
    if len(base) == 1:
        phrase = base[0]
        ok_dict = phrase in noitu.WORDS
    else:
        phrase = ' '.join(base)
        ok_dict = phrase in noitu.PHRASES
    if g['mode'] == 1 and g['last_player'] == message.author.id:
        try:
            await message.add_reaction('⏳')
        except Exception:
            pass
        return
    if phrase in g['used'] or not ok_dict or base[0] != g['need_word']:
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
        await message.reply('Cách dùng: `p!setkey <key>`')
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
    hist = AI_HISTORY.setdefault(ch, [])
    hist = (hist + [{'role': 'user', 'content': user_text}])[-20:]
    sys_base = 'Bạn là Casiobot - bot Discord tiếng Việt. Trả lời ngắn gọn, thân thiện, đúng trọng tâm, bằng tiếng Việt. Không cần nhắc tài liệu.'
    msgs = [{'role': 'system', 'content': sys_base}] + hist
    try:
        async with message.channel.typing():
            reply = await ai_chat(key, msgs)
    except Exception as e:
        await message.reply(f'❌ Lỗi AI: `{e}`')
        AI_HISTORY.pop(ch, None)
        return
    AI_HISTORY[ch] = (hist + [{'role': 'assistant', 'content': reply}])[-20:]
    chunks = vd_docs.chunk_text(reply)
    await message.reply(chunks[0])
    for c in chunks[1:]:
        await message.channel.send(c)


COMMANDS = {
    'help': cmd_help,
    'ping': cmd_ping,
    'setchannel': cmd_setchannel,
    'delchannel': cmd_delchannel,
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
        await handle_noitu_move(message)
        await handle_ai_message(message)
        return
    lc = locked_channel_id(message.guild.id)
    if lc and message.channel.id != lc:
        reply = await message.reply(f'Bot chỉ hoạt động ở kênh <#{lc}> thôi!')
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
