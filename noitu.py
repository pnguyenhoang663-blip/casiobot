import os
import re
import random
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE, 'tudien.txt')

WORDS = set()
BY_LETTER = {}
RAW = []


def normalize(s):
    s = s.lower().replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z]', '', s)
    return s


def load(path=DICT_PATH):
    global WORDS, BY_LETTER, RAW
    WORDS = set()
    BY_LETTER = {}
    RAW = []
    seen = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                for tok in line.split():
                    b = normalize(tok)
                    if len(b) < 2:
                        continue
                    if tok not in seen:
                        seen.add(tok)
                        RAW.append(tok)
                    WORDS.add(b)
                    BY_LETTER.setdefault(b[0], set()).add(b)


def can_continue(letter, used):
    return any(w not in used for w in BY_LETTER.get(letter, ()))


def pick_start():
    cand = [tok for tok in RAW if 3 <= len(normalize(tok)) <= 6]
    random.shuffle(cand)
    for tok in cand:
        if can_continue(normalize(tok)[-1], set()):
            return tok
    return cand[0] if cand else 'anh'