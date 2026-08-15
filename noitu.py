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


def normalize(s):
    s = str(s).lower().replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z]', '', s)
    return s


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
                base_words = [normalize(t) for t in raw_words]
                base_words = [b for b in base_words if len(b) >= 2]
                if not base_words:
                    continue
                phrase_base = ' '.join(base_words)
                PHRASES.add(phrase_base)
                DISPLAY.setdefault(phrase_base, raw_line)
                START_BY_WORD.setdefault(base_words[0], set()).add(phrase_base)
                RAW.append(raw_line)
                for orig, b in zip(raw_words, [normalize(t) for t in raw_words]):
                    if len(b) >= 2:
                        WORDS.add(b)
                        WORD_DISPLAY.setdefault(b, orig)


def display_word(d):
    base = normalize(d)
    return WORD_DISPLAY.get(base, d)


def can_continue(word, used):
    for p in START_BY_WORD.get(word, ()):
        if p not in used:
            return True
    if word in WORDS and word not in used:
        return True
    return False


def pick_start():
    cand = [p for p in PHRASES if p.count(' ') == 1 and 3 <= len(p.replace(' ', '')) <= 8]
    if not cand:
        cand = list(PHRASES)
    random.shuffle(cand)
    for p in cand:
        if can_continue(p.split()[-1], set()):
            return DISPLAY.get(p, p)
    return DISPLAY.get(cand[0], cand[0]) if cand else 'con mèo'