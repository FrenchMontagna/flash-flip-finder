# Flash Flip Finder (Albion Online)

MVP web service + thin UI that recommends **what to buy, where to sell, and the optimal route** to maximize **expected profit per hour**, using Albion Online Data APIs.

## Features
- Royal cities + Caerleon (config-driven graph).
- Pulls current prices and recent history from Albion Online Data API (AOD).
- Computes Net/Unit, ROI, recommended quantity, and Profit/Hour.
- Risk-adjusted Dijkstra routing between cities.
- Filters: cities, tiers/enchant, min ROI, risk mode, capital cap.
- CSV export from the minimal frontend.

## Quickstart

### Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export ALBION_REGION=west   # or east|europe
uvicorn backend.app:app --reload --port 8080
```

### Frontend
Open `frontend/index.html` in a browser (or run a static server: `python -m http.server 5500 -d frontend`).

### Tests
```bash
pytest -q
```
