import os
import re
import sys
import time
import subprocess
import io

BASE = os.path.dirname(os.path.abspath(__file__))
COMPILER_DIR = os.path.join(BASE, 'hdcompiler_vn')
OUTPUT_DIR = os.path.join(BASE, 'outputs')

MODEL_DIRS = {'580': '580vnx', '880': '880btg'}

if COMPILER_DIR not in sys.path:
    sys.path.insert(0, COMPILER_DIR)

_gadgets_cache = {}
_labels_cache = {}

HEX_RE = re.compile(r'(?:[0-9a-f]{2}[ ]?)+\Z')


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_hex(text):
    return ''.join(ch for ch in (text or '') if ch in '0123456789abcdefABCDEF')


def compile_asm(model, asm_text):
    if not any(line.strip().lower().startswith('org ') for line in asm_text.splitlines()):
        asm_text = 'org 0xE9E0\n' + asm_text
    script = os.path.normpath(os.path.join(MODEL_DIRS[model], 'compiler_.py'))
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run(
        [sys.executable, script, '-f', 'hex'],
        input=asm_text.encode('utf-8'),
        capture_output=True, cwd=COMPILER_DIR, env=env, timeout=120)
    out = proc.stdout.decode('utf-8', errors='replace')
    err = proc.stderr.decode('utf-8', errors='replace')
    hex_line = None
    home = None
    end = None
    for line in out.splitlines():
        s = line.strip()
        m = re.match(r'^===\s*0x([0-9a-f]+)\s*->\s*0x([0-9a-f]+)\s*===?$', s)
        if m:
            home, end = m.group(1), m.group(2)
            continue
        if re.fullmatch(r'(?:[0-9a-f]{2}[ ]?)+[0-9a-f]{2}', s):
            hex_line = s.replace(' ', '')
    return hex_line, home, end, out, err


def load_gadgets(model):
    if model in _gadgets_cache:
        return _gadgets_cache[model]
    path = os.path.join(COMPILER_DIR, MODEL_DIRS[model], 'gadgets')
    result = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([0-9a-fA-F]+)\s+(.+)$', line)
            if m:
                result[int(m.group(1), 16)] = m.group(2)
    _gadgets_cache[model] = result
    return result


def load_labels(model):
    if model in _labels_cache:
        return _labels_cache[model]
    path = os.path.join(COMPILER_DIR, MODEL_DIRS[model], 'labels')
    result = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([0-9a-fA-F]+)\s+([\w.]+)', line)
            if m:
                result[int(m.group(1), 16)] = m.group(2)
    _labels_cache[model] = result
    return result


def decomp_hex(model, hexstr):
    b = bytes.fromhex(clean_hex(hexstr))
    gadgets = load_gadgets(model)
    labels = load_labels(model)
    out = []
    i = 0
    n = len(b)
    while i < n:
        if i + 3 < n and b[i + 3] == 0x30 and 0x30 <= b[i + 2] <= 0x3F:
            v = b[i] | (b[i + 1] << 8) | (b[i + 2] << 16) | (b[i + 3] << 24)
            adr = v - 0x30300000
            if adr in gadgets:
                out.append(gadgets[adr])
                i += 4
                continue
        if i + 1 < n:
            w = b[i] | (b[i + 1] << 8)
            if w in labels:
                out.append(labels[w])
                i += 2
                continue
        if i + 1 < n:
            out.append('0x%02x%02x' % (b[i], b[i + 1]))
            i += 2
        else:
            out.append('0x%02x' % b[i])
            i += 1
    return '\n'.join(out)


def analyze_asm(asm_text, model='580'):
    gset = set()
    for g in load_gadgets(model).values():
        gset.add(g.strip().lower().replace(' ', ''))
    for v in load_labels(model).values():
        gset.add(v.strip().lower().replace(' ', ''))
    info = {'org': [], 'labels': [], 'calls': [], 'strings': [],
            'hex_lines': 0, 'others': []}
    seen_calls = set()
    for raw in asm_text.splitlines():
        s = raw.strip()
        if not s or s.startswith('#') or s.startswith(';'):
            continue
        core = re.split(r'\s*#', s, 1)[0].strip()
        low = core.lower()
        if core.endswith(':'):
            info['labels'].append(core[:-1].strip())
            continue
        if low.startswith('org '):
            m = re.search(r'(0x[0-9a-fA-F]+)', low)
            info['org'].append(m.group(1) if m else core)
            continue
        if low.startswith('str ') or low.startswith('str"'):
            info['strings'].append(core)
            continue
        if low.startswith('call '):
            t = core[5:].strip()
            if t not in seen_calls:
                seen_calls.add(t)
                info['calls'].append(t)
            continue
        if low.startswith('bl '):
            t = 'BL ' + core[3:].strip()
            if t not in seen_calls:
                seen_calls.add(t)
                info['calls'].append(t)
            continue
        if low.startswith('hex ') or low.startswith('0x'):
            info['hex_lines'] += 1
            continue
        if low.replace(' ', '') in gset:
            if core not in seen_calls:
                seen_calls.add(core)
                info['calls'].append(core)
            continue
        info['others'].append(core)
    return info


HUMAN_EXPLAIN = {
    'setlr': 'Lưu địa chỉ trả về (link register) để chương trình không bị treo khi gọi hàm có BL/rt',
    'setsfr': 'Khởi tạo màn hình và bàn phím',
    'setlr_pc': 'Kết hợp setlr và nhảy chương trình',
    'di,rt': 'Tắt ngắt (DI) rồi trả về (RT)',
    'buffer_clear': 'Xoá sạch nội dung màn hình',
    'render.ddd4': 'Cập nhật màn hình sau khi vẽ/in chữ (bắt buộc gọi)',
    'printline': 'In 1 dòng chữ font to (0E) lên màn hình tại linepos',
    'smallprint': 'In chữ font nhỏ (08 / 0a / 0e) lên màn hình',
    'render_bitmap': 'Vẽ ảnh bitmap vào bộ đệm màn hình theo x, y, rộng, cao',
    'line_draw': 'Vẽ đường thẳng từ (x1,y1) đến (x2,y2)',
    'waitshift': 'Tạm dừng và chờ người dùng nhấn phím SHIFT',
    'calc_func': 'Thực hiện phép tính dạng token, lưu kết quả dạng NUM (10 byte)',
    'cmp_ea': 'So sánh ER0 với từng mục 4-byte trong bảng (EA trỏ tới), EA trỏ đến dữ liệu của mục khớp',
    'getkey': 'Đọc phím (không chờ), lưu keycode KI/KO 2 byte vào địa chỉ trong er0',
    'getscancode_nodelay': 'Đọc phím không chờ (giống getkey)',
    'getscancode': 'Đọc phím có chờ, dừng cho tới khi có phím bấm',
    'delay': 'Tạm dừng chương trình theo giá trị er0 (vd 0x1f40 ~ 1 giây)',
    'strcpy': 'Sao chép chuỗi từ er2 → er0, dừng khi gặp 0x00',
    'memcpy': 'Sao chép một khối bộ nhớ',
    'memzero': 'Xoá một vùng nhớ về 0',
    'verify_eq': 'So sánh bằng (==), đúng thì er0=00 01',
    'verify_ne': 'So sánh khác (!=)',
    'verify_gt': 'So sánh lớn hơn (>)',
    'verify_lt': 'So sánh bé hơn (<)',
    'verify_ge': 'So sánh lớn hơn hoặc bằng (>=)',
    'verify_le': 'So sánh bé hơn hoặc bằng (<=)',
}

_dismap_cache = {}


def get_dismap(model):
    if model in _dismap_cache:
        return _dismap_cache[model]
    path = os.path.join(COMPILER_DIR, MODEL_DIRS[model], 'disas.txt')
    d = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^\s*\t(.*?)\s*;\s*([0-9a-fA-F]+)\s*\|', line)
            if m:
                d[int(m.group(2), 16)] = m.group(1)
    _dismap_cache[model] = d
    return d


def _norm_code(s):
    s = s.strip().lower().replace(' ', '')
    if s.startswith('bl'):
        s = s[2:]
    return s


def _strip_rt(s):
    if s.endswith(',rt'):
        return s[:-3]
    return s


def gadget_info(model, code):
    code2 = _norm_code(code)
    code_match = _strip_rt(code2)
    gads = load_gadgets(model)
    labels = load_labels(model)
    addr = None
    for a, name in gads.items():
        if _strip_rt(_norm_code(name)) == code_match:
            addr = a
            break
    if addr is None:
        for a, name in labels.items():
            if _strip_rt(_norm_code(name)) == code_match:
                addr = a
                break

    explain = HUMAN_EXPLAIN.get(code2) or HUMAN_EXPLAIN.get(code_match)
    if not explain:
        if code2.startswith('pop'):
            reg = code2[3:]
            s = 'Lấy dữ liệu từ đỉnh stack vào %s' % (reg.upper() if reg else 'thanh ghi')
            n = {'XR0': 4, 'XR4': 4, 'XR8': 4, 'QR0': 8, 'QR8': 8}.get(reg.upper(), 2)
            if reg.upper() in ('XR0', 'XR4', 'XR8'):
                s = 'Lấy 4 byte từ đỉnh stack vào %s' % reg.upper()
            elif reg.upper() in ('QR0', 'QR8'):
                s = 'Lấy 8 byte từ đỉnh stack vào %s' % reg.upper()
            explain = s
        elif code2.startswith('sp='):
            explain = 'Đổi SP sang thanh ghi chỉ định rồi pop liên tiếp để nhảy tới địa chỉ trên stack (kỹ thuật stack pivot)'
        elif '[' in code2 and '=' in code2:
            explain = 'Thao tác đọc/ghi bộ nhớ qua thanh ghi (kiểu [erN] = rX)'
        else:
            explain = '(không có giải thích riêng, xem asm tham khảo)'

    dis = []
    if addr is not None:
        dismap = get_dismap(model)
        a = addr
        for _ in range(6):
            ins = dismap.get(a)
            if not ins:
                break
            dis.append('%05X: %s' % (a, ins))
            a += 2
            low_ins = ins.lower()
            if low_ins.startswith('pop pc') or 'rt' in low_ins.split() or low_ins.rstrip().endswith('rt'):
                break
    return addr, explain, dis


def classify_line(model, core, gset=None, extra=None):
    low = core.lower()
    if core.endswith(':'):
        return 'Label'
    if low.startswith('org '):
        return 'Địa chỉ của program'
    if low.startswith('str ') or low.startswith('str"'):
        return 'Chuỗi ký tự'
    if low.startswith('hex ') or low.startswith('0x'):
        return 'Dữ liệu'
    if low.startswith('goto '):
        return 'Nhảy tới label ' + core[5:].strip()
    name = core
    if low.startswith('call '):
        name = core[5:].strip()
    elif low.startswith('bl '):
        name = core[3:].strip()
    if extra is not None:
        e = extra.get(_norm_code(name))
        if e:
            return e
    _, explain, _ = gadget_info(model, name)
    if not explain.startswith('('):
        return explain
    if low.startswith('call ') or low.startswith('bl '):
        return 'Gọi hàm ' + name
    if gset is not None and low.replace(' ', '') in gset:
        return 'Gọi gadget'
    if '=' in core:
        return 'Gán thanh ghi'
    return ''


def annotate_asm(asm_text, model='580'):
    gset = set()
    for g in load_gadgets(model).values():
        gset.add(g.strip().lower().replace(' ', ''))
    for v in load_labels(model).values():
        gset.add(v.strip().lower().replace(' ', ''))
    extra = {}
    asm_lines = []
    for raw in asm_text.splitlines():
        stripped = raw.strip()
        if not stripped:
            asm_lines.append('')
            continue
        m = re.match(r'^(.*?)\s*[:：]\s*(.+)$', stripped)
        if m and m.group(2).strip():
            extra[_norm_code(m.group(1).strip())] = m.group(2).strip()
            continue
        if '#' in stripped:
            asm_lines.append(stripped)
            continue
        asm_lines.append(re.split(r'\s*#', stripped, 1)[0].strip())
    out = []
    for stripped in asm_lines:
        if not stripped:
            out.append('')
            continue
        if '#' in stripped:
            out.append(stripped)
            continue
        clean = stripped
        if clean.endswith(':') and not re.match(r'^[\w.\-]+:$', clean):
            clean = clean[:-1].rstrip()
        note = classify_line(model, clean, gset, extra)
        if note:
            out.append(clean + '    # ' + note)
        else:
            out.append(stripped)
    return '\n'.join(out)


def save_output(filename, content):
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def image_to_hex_bytes(img):
    from PIL import Image
    img = img.convert('L').resize((192, 63), Image.LANCZOS)
    px = img.load()
    out = bytearray()
    for y in range(63):
        for bx in range(24):
            v = 0
            for k in range(8):
                x = bx * 8 + k
                v = (v << 1) | (1 if px[x, y] < 128 else 0)
            out.append(v)
    return bytes(out)


def hex_bytes_to_image(data):
    from PIL import Image
    if len(data) < 1512:
        data += b'\x00' * (1512 - len(data))
    data = data[:1512]
    img = Image.new('L', (192, 63), 255)
    px = img.load()
    for y in range(63):
        for bx in range(24):
            byte = data[y * 24 + bx]
            for k in range(8):
                x = bx * 8 + k
                if byte & (1 << (7 - k)):
                    px[x, y] = 0
    return img


_REAL_580 = {
    0x19: '▯', 0x20: '𝒊', 0x21: '𝒆', 0x22: '𝜋', 0x23: ':', 0x24: '$', 0x25: '?',
    0x2C: ',', 0x2D: 'x10', 0x2E: '.',
    0x30: '0', 0x31: '1', 0x32: '2', 0x33: '3', 0x34: '4', 0x35: '5', 0x36: '6', 0x37: '7', 0x38: '8', 0x39: '9',
    0x3A: '𝗔', 0x3B: '𝗕', 0x3C: '𝗖', 0x3D: '𝗗', 0x3E: '𝗘', 0x3F: '𝗙',
    0x40: 'M', 0x41: 'Ans', 0x42: 'A', 0x43: 'B', 0x44: 'C', 0x45: 'D', 0x46: 'E', 0x47: 'F',
    0x48: '𝒙', 0x49: '𝒚', 0x4A: 'PreAns', 0x4B: '𝒛', 0x4C: '𝜃',
    0x50: '∑(', 0x51: '∫(', 0x52: 'd/d𝒙(', 0x53: '∏(',
    0x58: 'Min(', 0x59: 'Max(', 0x5A: 'Mean(', 0x5B: 'Sum(',
    0x60: '(', 0x61: 'P(', 0x62: 'Q(', 0x63: 'R(',
    0x64: 'Not(', 0x65: 'Neg(', 0x66: 'Conjg(', 0x67: 'Arg(', 0x68: 'Abs(', 0x69: 'Rnd(',
    0x6A: 'Det(', 0x6B: 'Trn(',
    0x6C: 'sinh(', 0x6D: 'cosh(', 0x6E: 'tanh(', 0x6F: 'sinh-1(',
    0x70: 'cosh-1(', 0x71: 'tanh-1(', 0x72: '𝒆^(',
    0x74: '√(', 0x75: 'ln(', 0x76: '³√(', 0x77: 'sin(', 0x78: 'cos(', 0x79: 'tan(',
    0x7A: 'sin-1(', 0x7B: 'cos-1(', 0x7C: 'tan-1(', 0x7D: 'log(', 0x7E: 'Pol(', 0x7F: 'Rec(',
    0x83: 'Int(', 0x84: 'Intg(', 0x85: 'Ref(', 0x86: 'Rref(',
    0x87: 'RanInt#(', 0x88: 'GCD(', 0x89: 'LCM(', 0x8A: 'RndFix(',
    0x8F: 'ReP(', 0x90: 'ImP(', 0x91: 'Identity(', 0x92: 'UnitV(', 0x93: 'Angle(',
    0xA0: 'or', 0xA1: 'xor', 0xA2: 'xnor', 0xA3: 'and',
    0xA5: '=', 0xA6: '+', 0xA7: '-', 0xA8: '×', 0xA9: '÷', 0xAA: '÷R', 0xAB: '⋅', 0xAC: '∠', 0xAD: '𝗣', 0xAE: '𝗖',
    0xC0: '−', 0xC1: 'b', 0xC2: 'o', 0xC3: 'd', 0xC4: 'h',
    0xC8: '⌟', 0xC9: '^(',
    0xD0: ')', 0xD1: '▸t', 0xD2: '▸a+b𝒊', 0xD3: '▸r∠𝜃',
    0xD5: '²', 0xD6: '³', 0xD7: '%', 0xD8: '!', 0xD9: '°', 0xDA: 'ʳ', 0xDB: 'ᵍ', 0xDC: '▫',
    0xDD: '𝐄', 0xDE: '𝐏', 0xDF: '𝐓', 0xE0: '𝐆', 0xE1: '𝐌', 0xE2: '𝐤', 0xE3: '𝐦',
    0xE4: '𝝁', 0xE5: '𝐧', 0xE6: '𝐩', 0xE7: '𝐟',
    0xE9: '▸Simp ',
}


def _build_table(at_fills, real):
    d = {}
    for item in at_fills:
        if isinstance(item, tuple):
            for v in range(item[0], item[1] + 1):
                d[v] = '@'
        else:
            d[item] = '@'
    for k, v in real.items():
        d[k] = v
    return d


_AT_580 = [
    0x00, (0x02, 0x18), (0x1A, 0x1F), (0x26, 0x2B), 0x2F,
    (0x4D, 0x4F), (0x54, 0x57), (0x5C, 0x5F), (0x80, 0x82), (0x8B, 0x8E),
    (0x94, 0x9F), 0xA4, (0xAF, 0xB7), (0xBC, 0xBF), (0xC5, 0xC7),
    (0xCB, 0xCF), 0xE8, (0xEA, 0xEF),
]

_AT_880 = [
    0x00, (0x02, 0x18), (0x1A, 0x1F), (0x26, 0x2B), 0x2F,
    0x4C, (0x4D, 0x4F), (0x54, 0x57), (0x5C, 0x5F), (0x80, 0x82), (0x8B, 0x8E),
    0x94, (0x97, 0x9F), 0xA4, (0xAF, 0xB7), (0xBC, 0xBF), (0xC5, 0xC7),
    (0xCB, 0xCF), 0xE8, (0xEA, 0xEC),
]

_REAL_880 = dict(_REAL_580)
del _REAL_880[0x40]
del _REAL_880[0x41]
del _REAL_880[0x47]
del _REAL_880[0x48]
del _REAL_880[0x49]
del _REAL_880[0x4B]
del _REAL_880[0x4C]
_REAL_880[0x40] = 'Ans'
_REAL_880[0x41] = 'A'
_REAL_880[0x47] = '𝒙'
_REAL_880[0x48] = '𝒚'
_REAL_880[0x49] = '𝒛'
_REAL_880[0x4B] = '𝜃'
_REAL_880[0x95] = 'f('
_REAL_880[0x96] = 'g('

DICHTABLES = {
    '580': _build_table(_AT_580, _REAL_580),
    '880': _build_table(_AT_880, _REAL_880),
}


def hex_to_tokens(model, hexstr):
    table = DICHTABLES.get(str(model).strip(), DICHTABLES['580'])
    hexchars = []
    flags = []
    space = False
    for ch in (hexstr or '').upper():
        if ch in '0123456789ABCDEF':
            hexchars.append(ch)
            flags.append(space)
            space = False
        else:
            space = True
    if len(hexchars) % 2 != 0:
        hexchars = hexchars[:-1]
        flags = flags[:-1]
    bytes_in = [(hexchars[i] + hexchars[i + 1], flags[i]) for i in range(0, len(hexchars), 2)]
    out = []
    i = 0
    n = len(bytes_in)
    while i < n:
        byte, sp = bytes_in[i]
        if byte in ('FD', 'FE'):
            if i + 1 < n:
                out.append(('<' + byte + bytes_in[i + 1][0] + '>', sp))
                i += 2
            else:
                out.append(('<' + byte + '>', sp))
                i += 1
            continue
        val = int(byte, 16)
        if val in table:
            res = table[val]
            if res == '@':
                out.append(('@(0x' + byte + ')', sp))
            else:
                out.append((res, sp))
        else:
            out.append(('<' + byte + '>', sp))
        i += 1
    result = ''
    for tok, sp in out:
        if sp and result:
            result += ' '
        result += tok
    return result


def list_examples():
    folder = os.path.join(COMPILER_DIR, '580vnx_ropchain')
    if not os.path.isdir(folder):
        return []
    names = sorted(f for f in os.listdir(folder) if f.endswith('.asm'))
    return names


def read_example(name):
    folder = os.path.join(COMPILER_DIR, '580vnx_ropchain')
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
