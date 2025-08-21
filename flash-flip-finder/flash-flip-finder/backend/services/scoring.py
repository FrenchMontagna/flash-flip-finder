from typing import List, Dict
import numpy as np

def compute_net_per_unit(buy_price: float, sell_price: float, profile: Dict) -> float:
    sales_tax = profile.get('sales_tax', 0.065)
    sell_fee = profile.get('sell_order_fee', 0.015)
    buy_fee = 0.0  # instant buy path by default
    transport_buf = profile.get('transport_buffer', 0.03)
    gross = sell_price - buy_price
    fees = sell_price * (sales_tax + sell_fee) + buy_price * buy_fee
    transport = sell_price * transport_buf
    return gross - fees - transport

def velocity_from_history(points: List[Dict], horizon_hours: int = 48) -> float:
    if not points: return 0.0
    w = np.linspace(1.0, 2.0, num=len(points))
    counts = np.array([float(p.get('item_count', 0) or 0) for p in points])
    return float((w * counts).sum() / len(points))

def recommend_qty(src_avail: int, dest_sold_per_horizon: int, capital_cap: int, buy_price: float) -> int:
    cap_qty = int(capital_cap // max(1, int(buy_price)))
    return max(0, min(int(src_avail), int(dest_sold_per_horizon), cap_qty))

def rank_profit_per_hour(net_per_unit: float, qty: int, minutes: float, listing_delay: int = 30) -> float:
    total_profit = max(0.0, net_per_unit) * max(0, qty)
    hours = max(0.1, (minutes + listing_delay) / 60.0)
    return total_profit / hours

def build_confidence(net_roi: float, velocity: float, freshness_min: float) -> float:
    a = min(1.0, max(0.0, net_roi / 0.3))
    b = min(1.0, velocity / 50.0)
    c = 1.0 if freshness_min <= 5 else max(0.0, 1.0 - (freshness_min - 5)/20.0)
    return 0.4*a + 0.4*b + 0.2*c
