import httpx, os, time
from typing import List, Dict, Any
from cachetools import TTLCache
from datetime import datetime

REGION = os.environ.get('ALBION_REGION', 'west')
BASES = {
    'west': 'https://west.albion-online-data.com',
    'east': 'https://east.albion-online-data.com',
    'europe': 'https://europe.albion-online-data.com',
}

_price_cache = TTLCache(maxsize=2048, ttl=90)
_hist_cache = TTLCache(maxsize=2048, ttl=300)

async def _get_json(url: str, params: Dict[str, Any]):
    async with httpx.AsyncClient(timeout=20, headers={'Accept-Encoding': 'gzip'}) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

async def fetch_prices_batched(item_ids: List[str], cities: List[str], region: str = REGION) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    base = f"{BASES[region]}/api/v2/stats/prices/"
    items_remaining = list(item_ids)
    while items_remaining:
        batch = []
        url_len = len(base) + len('?locations=') + len(','.join(cities))
        while items_remaining:
            candidate = items_remaining[0]
            if url_len + len(candidate) + 1 > 4000:
                break
            batch.append(items_remaining.pop(0))
            url_len += len(candidate) + 1
        if not batch:
            batch.append(items_remaining.pop(0))
        cache_key = (region, tuple(batch), tuple(cities))
        cached = _price_cache.get(cache_key)
        if cached:
            results.extend(cached); continue
        url = base + ','.join(batch)
        params = {'locations': ','.join(cities)}
        data = await _get_json(url, params)
        now = time.time()
        for row in data:
            ts = row.get('sell_price_min_date') or row.get('buy_price_max_date') or row.get('sell_price_max_date') or row.get('buy_price_min_date')
            fresh_min = 10_000
            if ts and isinstance(ts, str) and len(ts) >= 16:
                try:
                    dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
                    fresh_min = (now - dt.timestamp())/60.0
                except Exception:
                    pass
            row['_freshness_min'] = fresh_min
        _price_cache[cache_key] = data
        results.extend(data)
    return results

async def fetch_history_collapsed(item_id: str, cities: List[str], region: str = REGION, scale: int = 1, hours: int = 48) -> List[Dict[str, Any]]:
    cache_key = (region, item_id, tuple(cities), scale, hours)
    cached = _hist_cache.get(cache_key)
    if cached: return cached
    base = f"{BASES[region]}/api/v2/stats/history/{item_id}"
    params = {'locations': ','.join(cities), 'time-scale': scale}
    data = await _get_json(base, params)
    points = []
    for loc in data:
        for p in (loc.get('data') or []):
            points.append({'item_count': p.get('item_count', 0) or 0, 'avg_price': p.get('avg_price', 0) or 0, 'timestamp': p.get('timestamp')})
    points = points[-hours:]
    _hist_cache[cache_key] = points
    return points
