CREATE TABLE IF NOT EXISTS item (
  item_id   TEXT PRIMARY KEY,
  name      TEXT,
  tier      INTEGER,
  enchant   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS city (
  city_id   TEXT PRIMARY KEY,
  name      TEXT
);
CREATE TABLE IF NOT EXISTS route_edge (
  edge_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  from_city     TEXT REFERENCES city(city_id),
  to_city       TEXT REFERENCES city(city_id),
  zone_type     TEXT CHECK(zone_type IN ('blue','yellow','red','black')),
  distance_hops INTEGER,
  base_minutes  NUMERIC,
  risk_factor   NUMERIC,
  UNIQUE(from_city,to_city)
);
CREATE TABLE IF NOT EXISTS user_profile (
  user_id          TEXT PRIMARY KEY,
  capital_cap      NUMERIC,
  risk_mode        TEXT CHECK(risk_mode IN ('royal_only','balanced','aggressive')),
  buy_order_fee    NUMERIC,
  sell_order_fee   NUMERIC,
  sales_tax        NUMERIC,
  transport_buffer NUMERIC,
  mount_type       TEXT,
  avg_load_pct     NUMERIC
);
CREATE TABLE IF NOT EXISTS price_snapshot (
  snap_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc         TIMESTAMP NOT NULL,
  item_id        TEXT REFERENCES item(item_id),
  city_id        TEXT REFERENCES city(city_id),
  quality        INTEGER DEFAULT 1,
  sell_price_min NUMERIC,
  sell_price_max NUMERIC,
  buy_price_min  NUMERIC,
  buy_price_max  NUMERIC,
  source         TEXT DEFAULT 'rest'
);
CREATE TABLE IF NOT EXISTS history_snapshot (
  snap_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc      TIMESTAMP NOT NULL,
  item_id     TEXT REFERENCES item(item_id),
  city_id     TEXT REFERENCES city(city_id),
  price_avg   NUMERIC,
  item_count  INTEGER
);
CREATE TABLE IF NOT EXISTS route_path_cache (
  from_city   TEXT REFERENCES city(city_id),
  to_city     TEXT REFERENCES city(city_id),
  risk_mode   TEXT,
  node_list   TEXT,
  minutes_est NUMERIC,
  risk_label  TEXT,
  PRIMARY KEY (from_city,to_city,risk_mode)
);
CREATE TABLE IF NOT EXISTS opportunity (
  opp_id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc           TIMESTAMP NOT NULL,
  item_id          TEXT REFERENCES item(item_id),
  buy_city         TEXT REFERENCES city(city_id),
  sell_city        TEXT REFERENCES city(city_id),
  buy_at_or_below  NUMERIC,
  sell_at_or_above NUMERIC,
  gross_spread     NUMERIC,
  net_per_unit     NUMERIC,
  net_roi          NUMERIC,
  velocity_score   NUMERIC,
  qty_recommended  INTEGER,
  route_minutes    NUMERIC,
  route_risk       TEXT,
  profit_per_hour  NUMERIC,
  confidence       NUMERIC,
  route_nodes      TEXT
);
