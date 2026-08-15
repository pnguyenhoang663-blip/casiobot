import os
import random
import re
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE, 'tudien.txt')

PHRASES = set()
WORDS = set()
PHRASE_START = {}
BY_LETTER = {}
RAW = []


def normalize(s):
    s = s.lower().replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z]', '', s)
    return s


def load(path=DICT_PATH):
    global PHRASES, WORDS, PHRASE_START, BY_LETTER, RAW
    PHRASES = set()
    WORDS = set()
    PHRASE_START = {}
    BY_LETTER = {}
    RAW = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line:
                    continue
                base_words = [normalize(t) for t in raw_line.split()]
                base_words = [b for b in base_words if len(b) >= 2]
                if not base_words:
                    continue
                phrase = ' '.join(base_words)
                PHRASES.add(phrase)
                PHRASE_START.setdefault(phrase[0], set()).add(phrase)
                RAW.append(raw_line)
                for b in base_words:
                    WORDS.add(b)
                    BY_LETTER.setdefault(b[0], set()).add(b)


def can_continue(letter, used):
    for w in PHRASE_START.get(letter, ()):
        if w not in used:
            return True
    for w in BY_LETTER.get(letter, ()):
        if w not in used:
            return True
    return False


def pick_start():
    cand = [p for p in PHRASES if p.count(' ') == 1 and 3 <= len(p.replace(' ', '')) <= 8]
    if not cand:
        cand = list(PHRASES)
    random.shuffle(cand)
    for p in cand:
        if can_continue(p[-1], set()):
            return p
    return cand[0] if cand else 'anh em'