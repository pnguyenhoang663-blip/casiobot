import re

EMOJI_RE = re.compile(
    '[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\uFE0F\u00A9\u00AE]'
)

MONTHS_EN = ['january', 'february', 'march', 'april', 'may', 'june',
             'july', 'august', 'september', 'october', 'november', 'december']
MONTHS_VI = ['thang mot', 'thang hai', 'thang ba', 'thang tu', 'thang nam', 'thang sau',
             'thang bay', 'thang tam', 'thang chin', 'thang muoi', 'thang muoi mot', 'thang muoi hai']


def _leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


RULES = {}


def rule(rid, name):
    def deco(fn):
        RULES[rid] = {'id': rid, 'name': name, 'fn': fn}
        return fn
    return deco


@rule(1, 'Mật khẩu phải dài ít nhất 10 ký tự')
def r1(pw):
    return len(pw) >= 10


@rule(2, 'Phải chứa ít nhất 1 chữ hoa, 1 chữ thường và 1 chữ số')
def r2(pw):
    return (any(c.isupper() for c in pw)
            and any(c.islower() for c in pw)
            and any(c.isdigit() for c in pw))


@rule(3, 'Phải chứa ít nhất 1 ký tự đặc biệt')
def r3(pw):
    return any(c in '!@#$%^&*' for c in pw)


@rule(4, 'Không được chứa khoảng trắng')
def r4(pw):
    return ' ' not in pw


@rule(5, 'Phải chứa tên một tháng trong năm')
def r5(pw):
    low = pw.lower()
    return any(m in low for m in MONTHS_EN) or any(m in low for m in MONTHS_VI)


@rule(6, 'Tổng các chữ số trong mật khẩu phải đúng bằng 20')
def r6(pw):
    return sum(int(c) for c in pw if c.isdigit()) == 20


@rule(7, 'Ký tự đầu tiên và ký tự cuối cùng phải giống hệt nhau')
def r7(pw):
    return len(pw) >= 1 and pw[0] == pw[-1]


@rule(8, 'Phải chứa một năm nhuận')
def r8(pw):
    for m in re.finditer(r'\d{4}', pw):
        if _leap(int(m.group())):
            return True
    return False


@rule(9, 'Phải chứa ít nhất 3 nguyên âm')
def r9(pw):
    return sum(c in 'aeiouAEIOU' for c in pw) >= 3


@rule(10, 'Phải chứa ít nhất 2 emoji bất kỳ')
def r10(pw):
    return len(EMOJI_RE.findall(pw)) >= 2


LEVELS = {
    'easy': {'label': 'Dễ', 'rule_ids': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
    'normal': {'label': 'Bình thường', 'rule_ids': []},
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


def build_rules(level):
    return [RULES[i] for i in LEVELS[level]['rule_ids']]


def check(pw, rules, prev_passed=frozenset()):
    prev_passed = set(prev_passed)
    current_passed = set()
    missing = []
    for r in rules:
        rid, name, fn = r['id'], r['name'], r['fn']
        try:
            good = bool(fn(pw))
        except Exception:
            good = False
        if good:
            current_passed.add(rid)
        else:
            missing.append((rid, name))
    lost = bool(prev_passed - current_passed)
    return {
        'ok': not missing,
        'first_id': missing[0][0] if missing else None,
        'missing': missing,
        'passed': current_passed,
        'lost': lost,
    }