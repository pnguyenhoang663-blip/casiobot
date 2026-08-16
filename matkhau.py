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


NORMAL_OWN = [101, 102, 103, 104, 105, 107, 108, 109, 111, 112, 114, 115, 116, 117, 118, 119, 120]

LEVELS = {
    'easy': {'label': 'Dễ', 'rule_ids': EASY_IDS},
    'normal': {'label': 'Bình thường', 'rule_ids': EASY_NO_SPACE + NORMAL_OWN},
    'hard': {'label': 'Khó', 'rule_ids': []},
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