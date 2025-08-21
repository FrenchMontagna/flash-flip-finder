from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os, json

from services.ingest import fetch_prices_batched, fetch_history_collapsed
from services.scoring import compute_net_per_unit, recommend_qty, rank_profit_per_hour, velocity_from_history, build_confidence
from services.routing import best_route, load_city_graph, RiskMode

CFG_DIR = os.path.join(os.path.dirname(__file__), 'config')
with open(os.path.join(CFG_DIR, 'items.seed.json'), 'r') as f:
    ITEM_SEED = json.load(f)
with open(os.path.join(CFG_DIR, 'profile.defaults.json'), 'r') as f:
    PROFILE_DEFAULTS = json.load(f)
CITY_GRAPH = load_city_graph(os.path.join(CFG_DIR, 'city_graph.json'))

DEFAULT_CITIES = CITY_GRAPH['cities']
REGION = os.environ.get('ALBION_REGION', PROFILE_DEFAULTS.get('region', 'west'))
FRESHNESS_MAX_MIN = int(os.environ.get('FRESHNESS_MAX_MIN', '5'))
ALLOW_STALE = os.environ.get('ALLOW_STALE', 'false').lower() == 'true'

app = FastAPI(title='Flash Flip Finder API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get('/opportunities')
async def opportunities(
    cities: Optional[str] = Query(None, description='CSV city list'),
    tiers: Optional[str] = Query('4-6'),
    enchants: Optional[str] = Query('0,1'),
    min_roi: float = Query(0.10),
    region: str = Query(REGION),
    risk: RiskMode = Query(RiskMode.royal_only),
    capital: int = Query(1_000_000),
    limit: int = Query(25),
    allow_stale: Optional[bool] = Query(None),
):
    sel_cities = [c.strip().upper().replace(' ', '_') for c in (cities.split(',') if cities else DEFAULT_CITIES)]
    tiers_rng = tiers.split('-') if '-' in tiers else [tiers, tiers]
    tmin, tmax = int(tiers_rng[0]), int(tiers_rng[-1])

    # Filter seed items by tier range
    items = [iid for iid in ITEM_SEED if tmin <= int(iid.split('_')[0][1:]) <= tmax]

    fresh_threshold = FRESHNESS_MAX_MIN if (allow_stale is None) else (10_000 if allow_stale else FRESHNESS_MAX_MIN)

    price_rows = await fetch_prices_batched(items, sel_cities, region)

    prices = {}
    for row in price_rows:
        key = (row.get('item_id'), row.get('city').upper().replace(' ', '_'))
        prices.setdefault(key, []).append(row)

    def pick_latest_price(rows):
        if not rows: return None
        return sorted(rows, key=lambda r: (r.get('quality', 1), r.get('sell_price_min', 10**12)))[-1]

    opps = []
    for item in items:
        for src in sel_cities:
            src_row = pick_latest_price(prices.get((item, src), []))
            if not src_row: continue
            src_fresh_min = src_row.get('_freshness_min', 10_000)
            if src_fresh_min > fresh_threshold: continue

            for dest in sel_cities:
                if dest == src: continue
                dest_row = pick_latest_price(prices.get((item, dest), []))
                if not dest_row: continue
                dest_fresh_min = dest_row.get('_freshness_min', 10_000)
                if dest_fresh_min > fresh_threshold: continue

                buy_price = src_row.get('sell_price_min') or 0
                sell_price = dest_row.get('sell_price_min') or 0
                if buy_price <= 0 or sell_price <= 0: continue

                net_per_unit = compute_net_per_unit(buy_price, sell_price, PROFILE_DEFAULTS)
                net_roi = net_per_unit / buy_price if buy_price else 0
                if net_roi < min_roi: continue

                history = await fetch_history_collapsed(item, [dest], region, scale=1, hours=48)
                vel = velocity_from_history(history, horizon_hours=48)
                if vel < 10:  # demand guard
                    continue

                qty = recommend_qty(src_avail=10**9, dest_sold_per_horizon=int(vel), capital_cap=capital, buy_price=buy_price)
                if qty <= 0: continue

                route = best_route(src, dest, risk_mode=risk, mount=PROFILE_DEFAULTS['mount_type'], load_pct=PROFILE_DEFAULTS['avg_load_pct'])
                if not route: continue

                pph = rank_profit_per_hour(net_per_unit, qty, route['minutes_est'], listing_delay=30)
                conf = build_confidence(net_roi, vel, max(src_fresh_min, dest_fresh_min))

                opps.append({
                    'item_id': item,
                    'item_name': item.replace('_', ' ').title(),
                    'buy_city': src,
                    'buy_at_or_below': int(buy_price),
                    'sell_city': dest,
                    'sell_at_or_above': int(sell_price),
                    'net_per_unit': int(net_per_unit),
                    'net_roi': round(net_roi, 4),
                    'qty_recommended': int(qty),
                    'route': route,
                    'profit_per_hour': int(pph),
                    'confidence': round(conf, 2),
                    'freshness_min': int(max(src_fresh_min, dest_fresh_min)),
                })

    opps.sort(key=lambda x: x['profit_per_hour'], reverse=True)
    return opps[:limit]

@app.get('/route')
async def route(from_: str = Query(alias='from'), to: str = Query(...), risk: RiskMode = Query(RiskMode.royal_only), mount: str = Query('OX_T6'), load_pct: float = Query(0.6)):
    plan = best_route(from_.upper().replace(' ', '_'), to.upper().replace(' ', '_'), risk_mode=risk, mount=mount, load_pct=load_pct)
    if not plan:
        raise HTTPException(404, detail='No route found with current risk settings')
    return plan
