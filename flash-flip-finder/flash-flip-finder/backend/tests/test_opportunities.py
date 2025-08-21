import respx, httpx
from backend.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def price_row(item, city, sell_min, ts='2024-02-12T16:57:59.000Z'):
    return {
        "item_id": item, "city": city.title(), "quality": 1,
        "sell_price_min": sell_min, "sell_price_min_date": ts,
        "buy_price_max": sell_min-1, "buy_price_max_date": ts
    }

@respx.mock
def test_buy_sell_route_surfaced():
    base = 'https://west.albion-online-data.com'
    respx.get(f"{base}/api/v2/stats/prices/T6_BAG", params={"locations":"LYMHURST,MARTLOCK"}).mock(
        return_value=httpx.Response(200, json=[
            price_row('T6_BAG','LYMHURST',12400),
            price_row('T6_BAG','MARTLOCK',15100)
        ])
    )
    respx.get(f"{base}/api/v2/stats/history/T6_BAG", params={"locations":"MARTLOCK","time-scale":1}).mock(
        return_value=httpx.Response(200, json=[{"location":"Martlock","data":[{"item_count":20,"avg_price":15000} for _ in range(48)]}])
    )
    r = client.get('/opportunities', params={
        'cities':'LYMHURST,MARTLOCK', 'tiers':'6-6', 'risk':'royal_only', 'capital':800000, 'min_roi':0.12, 'limit':20
    })
    assert r.status_code == 200
    body = r.json()
    assert any(o['buy_city']=='LYMHURST' and o['sell_city']=='MARTLOCK' and o['profit_per_hour']>0 for o in body)

@respx.mock
def test_profit_hour_ranking_prefers_shorter_route():
    base = 'https://west.albion-online-data.com'
    prices = [
        price_row('T6_BAG','LYMHURST',10000), price_row('T6_BAG','MARTLOCK',12000),
        price_row('T5_BAG','LYMHURST', 5000), price_row('T5_BAG','MARTLOCK', 6000)
    ]
    respx.get(f"{base}/api/v2/stats/prices/T6_BAG,T5_BAG", params={"locations":"LYMHURST,MARTLOCK"}).mock(
        return_value=httpx.Response(200, json=prices)
    )
    respx.get(f"{base}/api/v2/stats/history/T6_BAG", params={"locations":"MARTLOCK","time-scale":1}).mock(
        return_value=httpx.Response(200, json=[{"location":"Martlock","data":[{"item_count":30,"avg_price":1} for _ in range(48)]}])
    )
    respx.get(f"{base}/api/v2/stats/history/T5_BAG", params={"locations":"MARTLOCK","time-scale":1}).mock(
        return_value=httpx.Response(200, json=[{"location":"Martlock","data":[{"item_count":30,"avg_price":1} for _ in range(48)]}])
    )
    r = client.get('/opportunities', params={'cities':'LYMHURST,MARTLOCK','tiers':'5-6','risk':'royal_only'})
    assert r.status_code == 200
    body = r.json()
    assert body[0]['profit_per_hour'] >= body[-1]['profit_per_hour']

@respx.mock
def test_freshness_guard():
    base = 'https://west.albion-online-data.com'
    old_ts = '2020-02-12T16:57:59.000Z'
    respx.get(f"{base}/api/v2/stats/prices/T6_BAG", params={"locations":"LYMHURST,MARTLOCK"}).mock(
        return_value=httpx.Response(200, json=[
            price_row('T6_BAG','LYMHURST',12400, ts=old_ts),
            price_row('T6_BAG','MARTLOCK',15100, ts=old_ts)
        ])
    )
    respx.get(f"{base}/api/v2/stats/history/T6_BAG", params={"locations":"MARTLOCK","time-scale":1}).mock(
        return_value=httpx.Response(200, json=[{"location":"Martlock","data":[{"item_count":30,"avg_price":1} for _ in range(48)]}])
    )
    r = client.get('/opportunities', params={'cities':'LYMHURST,MARTLOCK','tiers':'6-6','risk':'royal_only'})
    assert r.status_code == 200
    assert r.json() == []
