# Product Requirements (v1)

**User story**: As a trader, tell me **what to buy**, **where to sell**, **the route**, and **how much**, to make silver fast with acceptable risk.

### In scope
Royal cities + Caerleon; AOD current prices + history; Net/Unit, ROI, Qty, Profit/hr; risk-adjusted routing; filters; CSV export.

### Success
TTFP <30m; ≥80% fills in horizon; median net ROI ≥15%.

### Data source
AOD endpoints: prices + history (hourly/daily); servers west/east/europe; rate limits 180/min & 300/5min; use gzip + batching.

### Risk
`royal_only` blocks red/black; `balanced/aggressive` penalize but allow. Guard stale >5m, anomalous spreads, low velocity.

### Ranking
Profit/hr = (NetPerUnit × Qty) / (TripMinutes + listing_delay). Velocity via recency-weighted item_count.
