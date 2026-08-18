import time
from datetime import datetime, timedelta
from urllib.parse import quote

import aiohttp

CACHE = {}
TTL = 600
NUM_WEB = 5
NUM_IMG = 3


class GgError(Exception):
    pass


class GgQuotaError(GgError):
    pass


def _ck(kind, q):
    return (kind, q.strip().lower())


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
            if r.status in (403, 429):
                raise GgQuotaError()
            if r.status != 200:
                raise GgError(f'Google trả lỗi HTTP {r.status}')
            return await r.json()


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