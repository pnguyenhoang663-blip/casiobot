import os
import random
import re
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE, 'tudien.txt')

PHRASES = set()
WORDS = set()
START_BY_WORD = {}
DISPLAY = {}
WORD_DISPLAY = {}
RAW = []

_NUM = re.compile(r'^\d+$')


def canon(s):
    """Chuẩn hoá NHƯNG GIỮ dấu tiếng Việt (NFC, lowercase, chỉ giữ chữ cái)."""
    s = unicodedata.normalize('NFC', str(s).lower())
    return ''.join(c for c in s if c.isalpha())


def load(path=DICT_PATH):
    global PHRASES, WORDS, START_BY_WORD, DISPLAY, WORD_DISPLAY, RAW
    PHRASES = set()
    WORDS = set()
    START_BY_WORD = {}
    DISPLAY = {}
    WORD_DISPLAY = {}
    RAW = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line:
                    continue
                raw_words = raw_line.split()
                cw = [canon(t) for t in raw_words]
                cw = [w for w in cw if len(w) >= 2]
                if not cw:
                    continue
                phrase = ' '.join(cw)
                PHRASES.add(phrase)
                DISPLAY.setdefault(phrase, raw_line)
                START_BY_WORD.setdefault(cw[0], set()).add(phrase)
                RAW.append(raw_line)
                for orig, w in zip(raw_words, cw):
                    WORDS.add(w)
                    WORD_DISPLAY.setdefault(w, orig)


def display_word(d):
    return WORD_DISPLAY.get(canon(d), str(d))


def can_continue(word, used):
    for p in START_BY_WORD.get(word, ()):
        if p not in used:
            return True
    if word in WORDS and word not in used:
        return True
    return False


def pick_start():
    cand = [
        p for p in PHRASES
        if p.count(' ') == 1
        and 3 <= len(p.replace(' ', '')) <= 8
        and len(set(p.split())) == len(p.split())
    ]
    if not cand:
        cand = list(PHRASES)
    random.shuffle(cand)
    for p in cand:
        if can_continue(p.split()[-1], set()):
            return DISPLAY.get(p, p)
    return DISPLAY.get(cand[0], cand[0]) if cand else 'con mèo'