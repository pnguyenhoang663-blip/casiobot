import random
import re


def _is_prime(n):
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _pal_digits(s):
    s = str(s)
    return s == s[::-1]


# ---- dữ liệu tra cứu ----
MONTHS_EN = ['january', 'february', 'march', 'april', 'may', 'june',
             'july', 'august', 'september', 'october', 'november', 'december']
MONTHS_VI = ['thang mot', 'thang hai', 'thang ba', 'thang tu', 'thang nam', 'thang sau',
             'thang bay', 'thang tam', 'thang chin', 'thang muoi', 'thang muoi mot', 'thang muoi hai']

ROMAN_VAL = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
NOBLE_GAS = ['He', 'Ne', 'Ar', 'Kr', 'Xe', 'Rn']
PLANETS = ['mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune',
           'sao thuy', 'sao kim', 'sao hoa', 'sao moc', 'sao tho', 'sao thien vuong', 'sao hai vuong', 'trai dat']
SE_ASIA = ['vietnam', 'viet nam', 'thailand', 'thai lan', 'laos', 'lao', 'campuchia', 'cambodia',
           'myanmar', 'mien dien', 'indonesia', 'philippines', 'philippin', 'malaysia', 'singapore',
           'timor', 'brunei']
LANGS = ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c sharp', 'go', 'rust', 'php',
         'ruby', 'swift', 'kotlin', 'html', 'css', 'lua', 'perl', 'dart', 'scala', 'haskell', 'basic', 'pascal']
FRUITS = '🍎🍏🍌🍇🍉🍊🍋🍒🍓🍑🍍🥝🥥🍐🍈🥭🍅🍆🌽'
SUITS = ['♠', '♣', '♥', '♦']
SPECIAL = "!@#$%^&*()_+-=[]{};:'\",.<>/?\\|`~"
HIST_FIGURES = ['alexander', 'napoleon', 'caesar', 'hannibal', 'genghis', 'ramses', 'cleopatra', 'quizotep',
                'ho chi minh', 'thanh cat han', 'cung de', 'pittheus', 'tutankhamun', 'confucius', 'socrates']
FOREIGN_PHRASES = ['bonjour', 'merci', 'bonsoir', 'salut', 'danke', 'hallo', 'guten tag', 'auf wiedersehen',
                   'bienvenue', 'merci beaucoup', 'je ne sais pas']
DATA_STR = ['array', 'linkedlist', 'stack', 'queue', 'tree', 'graph', 'hashmap', 'heap']
OSCAR_FILMS = ['parasite', 'everything everywhere', 'oppenheimer', 'the shape of water', 'moonlight', 'la la land',
               'birdman', '12 years a slave', 'the artist', 'the king speech', 'nomadland', 'green book', 'spotlight']
LATIN_NAMES = ['homo sapiens', 'canis lupus', 'felis catus', 'panthera leo', 'bos taurus', 'gallus gallus',
               'equus caballus', 'orcinus orca', 'ursus arctos', 'panthera tigris']
SORT_ALGOS = ['bubble', 'merge', 'quick', 'insertion', 'selection', 'heap', 'radix', 'shell', 'counting', 'bucket']


def _fib_triples():
    f = [0, 1]
    while f[-1] < 100000:
        f.append(f[-1] + f[-2])
    out = []
    for i in range(len(f) - 2):
        out.append(str(f[i]) + str(f[i + 1]) + str(f[i + 2]))
    return out


FIB_TRIPLES = _fib_triples()


# ---- registry ----
RULES = {}


def rule(rid, name):
    def deco(fn):
        RULES[rid] = {'id': rid, 'name': name, 'fn': fn}
        return fn
    return deco


# ================= DỄ (1-10) =================

@rule(1, 'Mật khẩu phải dài ít nhất 10 ký tự')
def r1(pw, data=None):
    return len(pw) >= 10


@rule(2, 'Phải chứa ít nhất 1 chữ hoa, 1 chữ thường và 1 chữ số')
def r2(pw, data=None):
    return (any(c.isupper() for c in pw)
            and any(c.islower() for c in pw)
            and any(c.isdigit() for c in pw))


@rule(3, 'Phải chứa ít nhất 1 ký tự đặc biệt')
def r3(pw, data=None):
    return any(c in '!@#$%^&*' for c in pw)


@rule(4, 'Không được chứa khoảng trắng')
def r4(pw, data=None):
    return ' ' not in pw


@rule(5, 'Phải chứa tên một tháng trong năm')
def r5(pw, data=None):
    low = pw.lower()
    return any(m in low for m in MONTHS_EN) or any(m in low for m in MONTHS_VI)


@rule(6, 'Tổng các chữ số trong mật khẩu phải đúng bằng 20')
def r6(pw, data=None):
    return sum(int(c) for c in pw if c.isdigit()) == 20


@rule(7, 'Ký tự đầu tiên và ký tự cuối cùng phải giống hệt nhau')
def r7(pw, data=None):
    return len(pw) >= 1 and pw[0] == pw[-1]


@rule(8, 'Phải chứa một năm nhuận')
def r8(pw, data=None):
    for m in re.finditer(r'\d{4}', pw):
        y = int(m.group())
        if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
            return True
    return False


@rule(9, 'Phải chứa ít nhất 3 nguyên âm')
def r9(pw, data=None):
    return sum(c in 'aeiouAEIOU' for c in pw) >= 3


@rule(10, 'Phải chứa ít nhất 2 emoji bất kỳ')
def r10(pw, data=None):
    return len(re.findall(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\uFE0F\u00A9\u00AE]', pw)) >= 2


EASY_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
EASY_NO_SPACE = [1, 2, 3, 5, 6, 7, 8, 9, 10]


# ================= BÌNH THƯỜNG (101-120, bỏ 106/110/113) =================

@rule(101, 'Phải chứa một số La Mã')
def r101(pw, data=None):
    return any(c in 'IVXLCDM' for c in pw.upper())


@rule(102, 'Tổng giá trị các số La Mã trong mật khẩu phải đúng bằng 35')
def r102(pw, data=None):
    return sum(ROMAN_VAL[c] for c in pw.upper() if c in ROMAN_VAL) == 35


@rule(103, 'Phải chứa ký hiệu một nguyên tố khí hiếm')
def r103(pw, data=None):
    return any(g in pw for g in NOBLE_GAS)


@rule(104, 'Số chữ hoa phải gấp đôi số chữ thường')
def r104(pw, data=None):
    return sum(c.isupper() for c in pw) == 2 * sum(c.islower() for c in pw)


@rule(105, 'Phải chứa một mã màu hex hợp lệ')
def r105(pw, data=None):
    return bool(re.search(r'#[0-9a-fA-F]{6}', pw))


@rule(107, 'Phải chứa tên một hành tinh trong Hệ Mặt Trời')
def r107(pw, data=None):
    low = pw.lower()
    return any(p in low for p in PLANETS)


@rule(108, 'Phải chứa 3 số liên tiếp thuộc dãy Fibonacci')
def r108(pw, data=None):
    return any(t in pw for t in FIB_TRIPLES)


@rule(109, 'Không được chứa nguyên âm viết thường')
def r109(pw, data=None):
    return not any(c in 'aeiou' for c in pw if c.islower())


@rule(111, 'Độ dài mật khẩu phải là một số nguyên tố')
def r111(pw, data=None):
    return _is_prime(len(pw))


@rule(112, 'Phải chứa đúng 3 emoji trái cây khác nhau')
def r112(pw, data=None):
    return len(set(c for c in pw if c in FRUITS)) == 3


@rule(114, 'Số ký tự đặc biệt phải bằng số chữ số')
def r114(pw, data=None):
    return sum(c in SPECIAL for c in pw) == sum(c.isdigit() for c in pw)


@rule(115, 'Phải chứa một định dạng markdown')
def r115(pw, data=None):
    return bool(re.search(r'\*\*[^*]+\*\*', pw)
                or re.search(r'(?<!\*)\*[^*]+\*(?!\*)', pw)
                or re.search(r'`[^`]+`', pw))


@rule(116, 'Phải chứa tên một ngôn ngữ lập trình')
def r116(pw, data=None):
    low = pw.lower()
    return any(lang in low for lang in LANGS)


@rule(117, 'Phải chứa tên một quốc gia Đông Nam Á')
def r117(pw, data=None):
    low = pw.lower()
    return any(c in low for c in SE_ASIA)


@rule(118, 'Ký tự ở vị trí trung tâm của mật khẩu phải là chữ số')
def r118(pw, data=None):
    return len(pw) >= 1 and pw[len(pw) // 2].isdigit()


@rule(119, 'Phải chứa ký hiệu cả 4 nước bài Tây')
def r119(pw, data=None):
    return all(s in pw for s in SUITS)


@rule(120, 'Phải chứa một từ tiếng Anh có đúng 5 chữ cái')
def r120(pw, data=None):
    return any(len(tok) == 5 for tok in re.findall(r'[A-Za-z]+', pw))


@rule(106, 'Phải chứa ít nhất 2 từ tiếng Anh khác nhau')
def r106(pw, data=None):
    return len(set(re.findall(r'[A-Za-z]+', pw))) >= 2


@rule(110, 'Phải chứa đúng 2 khoảng trắng')
def r110(pw, data=None):
    return pw.count(' ') == 2


@rule(113, 'Phải chứa ít nhất 4 ký tự đặc biệt khác nhau')
def r113(pw, data=None):
    return len(set(c for c in pw if c in SPECIAL)) >= 4


NORMAL_OWN = [105, 106, 110, 112, 113, 114, 115, 116, 118, 119, 120]


ANIMALS = '🐣🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🐔🐧🐦🦆🦅🦉🦇🐺🐗🐴🦄🐝🦋🐌🐞🐢🐍🦎🦑🦀🐙🦞🦐🐠🐟🐬🐳🐋🦈🦭'
GREEK_CYR = set('λΩΔπθΣΦΨξδβγζηκμνρστφχψωЖДШЩЧЦФЫЗЪЭЁЬЪБВГДЕЖЗИЙКЛ')
VOWELS = 'aeiouAEIOU'
VICTORY_CAESAR = 'YLFWRUB'
MORSE_HELP = '.... . .-.. .--.'
CHESS_RE = re.compile(r'^(?:K|Q|R|B|N)?(?:[a-h])?x?[a-h][1-8][+#]?$')


# ================= KHÓ (201-230) =================

@rule(201, 'Phải chứa một nước đi cờ vua theo chuẩn notation')
def r201(pw, data=None):
    for tok in re.findall(r'[^ ]+', pw):
        if CHESS_RE.match(tok):
            return True
    return False


@rule(202, 'Phải chứa đúng số ký tự hiện tại của mật khẩu')
def r202(pw, data=None):
    return str(len(pw)) in pw


@rule(203, 'Ký tự thứ 15 của mật khẩu phải là chữ Z')
def r203(pw, data=None):
    return len(pw) >= 15 and pw[14] == 'Z'


@rule(204, 'Tổng mã ASCII của các chữ hoa phải chia hết cho 7')
def r204(pw, data=None):
    return sum(ord(c) for c in pw if c.isupper()) % 7 == 0


@rule(205, 'Không được có 2 chữ cái liền nhau trong bảng chữ cái')
def r205(pw, data=None):
    letters = [c.lower() for c in pw if c.isalpha()]
    return all(abs(ord(b) - ord(a)) != 1 for a, b in zip(letters, letters[1:]))


@rule(206, 'Số emoji phải bằng số ký tự La Mã')
def r206(pw, data=None):
    emoji_count = len(re.findall(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\uFE0F\u00A9\u00AE]', pw))
    roman_count = sum(c in 'IVXLCDM' for c in pw.upper())
    return emoji_count == roman_count


@rule(207, 'Phải chứa một ký tự Hy Lạp hoặc Nga')
def r207(pw, data=None):
    return any(c in GREEK_CYR for c in pw)


@rule(208, 'Phải chứa mã Base64 của từ PASSWORD')
def r208(pw, data=None):
    return 'UEFTU1dPUkQ=' in pw


@rule(209, 'Tổng số âm tiết các từ tiếng Anh phải đúng bằng 8')
def r209(pw, data=None):
    def syllables(w):
        groups = [g for g in re.findall(r'[aeiouy]+', w.lower()) if g]
        n = len(groups)
        if len(w) > 1 and w.lower().endswith('e') and n > 1:
            n -= 1
        return max(n, 1)
    return sum(syllables(w) for w in re.findall(r'[A-Za-z]+', pw)) == 8


@rule(210, 'Phải chứa tên một nhân vật lịch sử')
def r210(pw, data=None):
    low = pw.lower()
    return any(h in low for h in HIST_FIGURES)


@rule(211, 'Phải chứa một dòng lệnh Assembly cơ bản')
def r211(pw, data=None):
    return bool(re.search(r'\b(MOV|ADD|SUB|NOP|PUSH|POP|JMP|CALL|CMP|RT)\b', pw, re.I))


@rule(212, 'Phải chứa công thức định lý Pythagoras')
def r212(pw, data=None):
    return 'a^2+b^2=c^2' in pw or 'a^2 + b^2 = c^2' in pw or 'a2+b2=c2' in pw


@rule(213, 'Phải chứa một cụm từ tiếng Pháp hoặc tiếng Đức')
def r213(pw, data=None):
    low = pw.lower()
    return any(p in low for p in FOREIGN_PHRASES)


@rule(214, 'Tổng các chữ số khi cộng lại phải là số đối xứng')
def r214(pw, data=None):
    return _pal_digits(sum(int(c) for c in pw if c.isdigit()))


@rule(215, 'Phải chứa tên một cấu trúc dữ liệu')
def r215(pw, data=None):
    low = pw.lower()
    return any(d in low for d in DATA_STR)


@rule(216, 'Phải chứa một mã ISBN 13 chữ số')
def r216(pw, data=None):
    return bool(re.search(r'\d{13}', pw))


@rule(217, 'Phải chứa mã Caesar (+3) của chữ VICTORY')
def r217(pw, data=None):
    return VICTORY_CAESAR in pw.upper()


@rule(218, 'Phải chứa mã Morse của chữ HELP')
def r218(pw, data=None):
    return MORSE_HELP in pw


@rule(219, 'Phải chứa một số nguyên tố lớn hơn 1000')
def r219(pw, data=None):
    for tok in re.findall(r'\d+', pw):
        n = int(tok)
        if n > 1000 and _is_prime(n):
            return True
    return False


@rule(220, 'Phải chứa tên khoa học (Latin) của một loài động vật')
def r220(pw, data=None):
    low = pw.lower()
    return any(l in low for l in LATIN_NAMES)


@rule(221, 'Phải chứa tên của 3 thuật toán sắp xếp khác nhau')
def r221(pw, data=None):
    low = pw.lower()
    return sum(1 for s in SORT_ALGOS if s in low) >= 3


@rule(222, 'Phải chứa ít nhất 1 emoji động vật')
def r222(pw, data=None):
    return any(c in ANIMALS for c in pw)


@rule(223, 'Phải chứa ít nhất 5 chữ số')
def r223(pw, data=None):
    return sum(c.isdigit() for c in pw) >= 5


@rule(224, 'Phải chứa một từ palindrome')
def r224(pw, data=None):
    return any(tok.lower() == tok.lower()[::-1] for tok in re.findall(r'[A-Za-z]{3,}', pw))


@rule(225, 'Không được chứa chữ số 0')
def r225(pw, data=None):
    return '0' not in pw


@rule(226, 'Phải chứa ít nhất 3 nguyên âm liên tiếp nhau')
def r226(pw, data=None):
    return bool(re.search(r'[aeiouAEIOU]{3}', pw))


@rule(227, 'Phải chứa một ký tự lặp lại ít nhất 2 lần')
def r227(pw, data=None):
    return len(pw) - len(set(pw)) >= 1


@rule(228, 'Phải chứa một số chia hết cho 21')
def r228(pw, data=None):
    return any(int(tok) % 21 == 0 for tok in re.findall(r'\d+', pw))


@rule(229, 'Phải chứa một ký tự đặc biệt lặp lại ít nhất 3 lần')
def r229(pw, data=None):
    return any(sum(c == s for c in pw) >= 3 for s in set(c for c in pw if c in SPECIAL))


@rule(230, 'Phải chứa tên một vị vua hoặc nhân vật nổi tiếng trong lịch sử')
def r230(pw, data=None):
    low = pw.lower()
    return any(h in low for h in HIST_FIGURES)


HARD_OWN = [202, 203, 204, 205, 206, 209, 210, 211, 212, 213, 214, 215, 222, 223, 224, 225, 226, 227, 228, 229, 230]

LEVELS = {
    'easy': {'label': 'Dễ', 'rule_ids': EASY_IDS},
    'normal': {'label': 'Bình thường', 'rule_ids': EASY_NO_SPACE + NORMAL_OWN},
    'hard': {'label': 'Khó', 'rule_ids': EASY_NO_SPACE + HARD_OWN},
    'hardcore': {'label': 'Siêu khó', 'rule_ids': []},
}


def parse_level(s):
    s = (s or '').strip().lower()
    aliases = {
        'easy': ('easy', 'e', 'de', 'dễ'),
        'normal': ('normal', 'binh thuong', 'binhthuong', 'binh', 'n', 'tb'),
        'hard': ('hard', 'kho', 'khó', 'h'),
        'hardcore': ('hardcore', 'sieu kho', 'siêu khó', 'sieu', 'hc', 'sk'),
    }
    for lev, al in aliases.items():
        if s in al:
            return lev
    return None


def start(level):
    data = {}
    rules = []
    for rid in LEVELS[level]['rule_ids']:
        spec = RULES[rid]
        rules.append({'id': rid, 'name': spec['name'], 'fn': spec['fn']})
    return rules, data


def check(pw, rules, prev_passed=frozenset(), data=None):
    prev = set(prev_passed)
    cur = set()
    missing = []
    for pos, r in enumerate(rules, start=1):
        try:
            good = bool(r['fn'](pw, data))
        except Exception:
            good = False
        if good:
            cur.add(pos)
        else:
            missing.append((pos, r['name']))
    lost = bool(prev - cur)
    return {
        'ok': not missing,
        'first_pos': missing[0][0] if missing else None,
        'missing': missing,
        'passed': cur,
        'lost': lost,
    }