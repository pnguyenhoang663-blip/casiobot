import json
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import html as htmllib

import aiohttp

CACHE = {}
TTL = 600
NUM_WEB = 5
NUM_IMG = 3
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


class GgError(Exception):
    pass


class GgQuotaError(GgError):
    pass


def quota_msg():
    now = datetime.now()
    target = now.replace(hour=15, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    sec = int((target - now).total_seconds())
    h, rem = divmod(sec, 3600)
    m = rem // 60
    return f'🚫 Hết API key rồi! Chờ 14h-15h (giờ VN) để search tiếp — còn {h} giờ {m} phút nữa nhé 😪'


async def _get_json(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            status = r.status
            try:
                data = await r.json()
            except Exception:
                data = {}
            msg = ((data.get('error') or {}).get('message')) or ''
            low = msg.lower()
            is_quota = status == 429 or any(k in low for k in ('quota', 'dailylimit', 'ratelimit'))
            if is_quota:
                raise GgQuotaError(msg)
            if status != 200:
                if msg:
                    raise GgError(f'HTTP {status}: {msg}')
                raise GgError(f'Google trả lỗi HTTP {status}')
            return data


async def search_web(key, cx, query):
    ck = _ck('web', query)
    now = time.time()
    if ck in CACHE and now - CACHE[ck][0] < TTL:
        return CACHE[ck][1]
    url = ('https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s&num=%d'
           % (key, cx, quote(query), NUM_WEB))
    data = await _get_json(url)
    items = data.get('items', []) or []
    res = [{'title': it.get('title', ''),
            'link': it.get('link', ''),
            'snippet': it.get('snippet', '')} for it in items[:NUM_WEB]]
    CACHE[ck] = (now, res)
    return res


async def search_images(key, cx, query):
    ck = _ck('img', query)
    now = time.time()
    if ck in CACHE and now - CACHE[ck][0] < TTL:
        return CACHE[ck][1]
    url = ('https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s&searchType=image&num=%d'
           % (key, cx, quote(query), NUM_IMG))
    data = await _get_json(url)
    items = data.get('items', []) or []
    res = [{'title': it.get('title', ''),
            'link': it.get('link', ''),
            'thumb': (it.get('image') or {}).get('thumbnailLink', '')} for it in items[:NUM_IMG]]
    CACHE[ck] = (now, res)
    return res


def _ck(kind, q):
    return (kind, q.strip().lower())


def relax_queries(q):
    out = [q.strip()]
    words = q.split()
    general = [w for w in words if not re.search(r'\d', w)]
    for cand in (' '.join(general), general[0] if general else None):
        if cand and cand not in out:
            out.append(cand)
    return out


async def _fetch(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={'User-Agent': UA}, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                raise GgError(f'HTTP {r.status}')
            return await r.read()


async def search_web_free(query):
    ck = _ck('web-free', query)
    now = time.time()
    if ck in CACHE and now - CACHE[ck][0] < TTL:
        return CACHE[ck][1]
    url = 'https://html.duckduckgo.com/html/?q=' + quote(query[:80])
    data = await _fetch(url)
    txt = data.decode('utf-8', errors='replace')
    parts = re.split(r'<a rel="nofollow" class="result__a"', txt)
    res = []
    for part in parts[1:]:
        m = re.search(r'href="([^"]+)"[^>]*>(.*?)</a>', part, re.S)
        if not m:
            continue
        href = m.group(1)
        if 'ad_domain' in href:
            continue
        uddg = re.search(r'uddg=([^&]+)', href)
        link = unquote(uddg.group(1)) if uddg else href
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', part, re.S)
        title = re.sub('<.*?>', '', m.group(2))
        snippet = re.sub('<.*?>', '', snip.group(1)) if snip else ''
        res.append({'title': htmllib.unescape(title).strip(),
                    'link': link,
                    'snippet': htmllib.unescape(snippet).strip()})
        if len(res) >= NUM_WEB:
            break
    CACHE[ck] = (now, res)
    return res


async def search_images_free(query):
    ck = _ck('img-free', query)
    now = time.time()
    if ck in CACHE and now - CACHE[ck][0] < TTL:
        return CACHE[ck][1]
    url = 'https://api.openverse.org/v1/images?q=%s&page_size=%d' % (quote(query), NUM_IMG)
    data = await _fetch(url)
    js = json.loads(data)
    res = []
    for it in (js.get('results') or []):
        res.append({'title': it.get('title') or '',
                    'link': it.get('foreign_landing_url') or it.get('url') or '',
                    'thumb': it.get('url') or ''})
    CACHE[ck] = (now, res)
    return res