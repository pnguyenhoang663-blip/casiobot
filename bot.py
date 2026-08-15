import asyncio
import io
import json
import os
import re
import subprocess
import time

import discord
from PIL import Image

import compiler_lib as cl
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

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


def save_config():
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, ensure_ascii=False, indent=2)


def guild_settings(guild_id):
    gid = str(guild_id)
    if gid not in CONFIG['guilds']:
        CONFIG['guilds'][gid] = {'channel': None, 'search580': None, 'search880': None}
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


# ---------------- HELP (2 trang + chọn trang) ----------------

def build_page_chung():
    embed = discord.Embed(title='📖 Lệnh chung', color=0x00aaff)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 1/2 - Chọn "Casio tools" bên dưới để xem tiếp')
    embed.add_field(name=f'`{PREFIX}help`', value='Mở ra bảng hướng dẫn', inline=False)
    embed.add_field(name=f'`{PREFIX}ping`', value='Ping xem bot còn không', inline=False)
    embed.add_field(name=f'`{PREFIX}setchannel <id>`', value='Set kênh bot chỉ được hoạt động tại kênh đó (Chỉ có quyền admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}delchannel`', value='Xoá id kênh đó và bot có thể hoạt động ở mọi kênh (Chỉ có quyền admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}credit`', value='Giới thiệu', inline=False)
    return embed


def build_page_casio():
    embed = discord.Embed(title='🧮 Casio tools', color=0x00aaff)
    embed.set_footer(text=f'Prefix: {PREFIX} | Trang 2/2')
    embed.add_field(name=f'`{PREFIX}comp580 <asm>`', value='Compiler asm theo model 580vnx', inline=False)
    embed.add_field(name=f'`{PREFIX}comp880 <asm>`', value='Compiler asm theo model 880btg', inline=False)
    embed.add_field(name=f'`{PREFIX}decomp <model> <hex>`', value='Decomp theo model (580 hoặc 880)', inline=False)
    embed.add_field(name=f'`{PREFIX}vd`', value='Đưa ra 1 bảng lựa chọn ví dụ về các hàm phổ biến', inline=False)
    embed.add_field(name=f'`{PREFIX}phantich <asm>`', value='Phân tích asm đã đưa (demo) - file .txt hoặc dán trực tiếp, Chỉ dành cho 580vnx', inline=False)
    embed.add_field(name=f'`{PREFIX}p2b <ảnh>`', value='Dịch ảnh sang trắng đen theo 192x63 và đưa hex ra theo dạng .txt', inline=False)
    embed.add_field(name=f'`{PREFIX}h2b <hex>`', value='Dịch hex sang ảnh trắng đen theo 192x63', inline=False)
    embed.add_field(name=f'`{PREFIX}ganhex <hex>`', value='Gán hex đã đưa vào biến A, B, C', inline=False)
    embed.add_field(name=f'`{PREFIX}dichhex <580/880> <hex>`', value='Dịch hex sang token (580vnx/880btg)', inline=False)
    embed.add_field(name=f'`{PREFIX}set580 <id>`', value='Set id kênh bot sẽ tìm tin nhắn (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}set880 <id>`', value='Set id kênh bot sẽ tìm tin nhắn (Chỉ admin)', inline=False)
    embed.add_field(name=f'`{PREFIX}find580 <từ khoá>`', value='Tìm tin nhắn trong kênh đã set từ c!set580', inline=False)
    embed.add_field(name=f'`{PREFIX}find880 <từ khoá>`', value='Tìm tin nhắn trong kênh đã set từ c!set880', inline=False)
    return embed


class HelpSelect(discord.ui.Select):
    def __init__(self, pages):
        options = [
            discord.SelectOption(label='Lệnh chung', value='0', emoji='📖'),
            discord.SelectOption(label='Casio tools', value='1', emoji='🧮'),
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
    pages = [build_page_chung(), build_page_casio()]
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
            hexstr = data.hex()
            ts = int(time.time())
            txt_path = cl.save_output(f'p2b_{ts}.txt', hexstr)
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
    'ganhex': cmd_ganhex,
    'dichhex': cmd_dichhex,
    'set580': cmd_set580,
    'set880': cmd_set880,
    'find580': cmd_find580,
    'find880': cmd_find880,
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
    if not TOKEN:
        print('❌ Thiếu token (đặt biến môi trường TOKEN hoặc sửa config.json)')
    else:
        bot.run(TOKEN)
