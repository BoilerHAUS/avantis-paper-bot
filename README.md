# Avantis Paper Bot (v0)

Paper-first trading bot scaffold for **Avantis perps** (starting with **ETH/USD**) with:
- Continuous **Pyth/Avantis feed → 15m candle builder**
- **Deterministic** strategies (trend + mean reversion) — *stubbed in v0*
- **Risk manager**: 1% equity risk/trade, max 2x leverage, max 75% deployed, -10% daily kill switch — *stubbed in v0*
- **Paper execution engine** (sim fills + vol-based slippage) — *stubbed in v0*
- Append-only **journal** + dashboard **snapshot** outputs

This repo is intentionally built so the 15-minute trade loop can run **without any LLM dependency**. AI monitoring can be layered on later as a slower observer.

## Status
This is a **scaffold**: feed listener + candle aggregation + storage layout are implemented; strategies/risk/paper executor are placeholders.

## Quickstart
### 1) Create a venv + install deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Run the feed listener (continuous)
You need a websocket endpoint for the Avantis/Pyth feed.

Set:
- `AVANTIS_WS_URL` (e.g. `wss://...`)

Then:
```bash
export AVANTIS_WS_URL="wss://YOUR_ENDPOINT"
python -m bot.feed_listener --pair "ETH/USD" --tf-min 15
```

This writes append-only candles to:
- `data/candles/ETH-USD-15m.jsonl`

### 3) Run one cycle (manual)
```bash
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15
```

Outputs:
- `data/journal/YYYY-MM-DD.jsonl`
- `data/state/current.json`
- `data/state/snapshot.json`

## Config
Config is loaded from an optional JSON file:

- set `APB_CONFIG=/path/to/config.json`
- see `config.example.json`

This is what fixes the "$100 equity → $1 risk" problem: we use **1% risk** with a **USD floor** (e.g., $5) and a **USD ceiling** (e.g., $50), plus a minimum collateral.

Planned:
- switch to YAML later if we want
- add stronger supervision/alerts around the long-running services

## Docker (no runtime pip install)

Note: the Hermes stream can occasionally drop. The feed listener auto-reconnects with exponential backoff.
This repo includes a Docker image build that installs both dependencies and the package at image build time.
Containers run the bot directly and do **not** `pip install` on startup, so the runtime pip warning spam is removed.

Prereqs:
- `bootstrap.json` should exist (you can copy from `config.example.json`)

Build and run:
```bash
cp config.example.json bootstrap.json
docker compose build
docker compose up -d
```

Services:
- `apb-feed`: `python -m bot.feed_listener --pair ETH/USD --tf-min 15`
- `apb-cycle`: runs `python -m bot.run_cycle --pair ETH/USD --tf-min 15` every 15 minutes

Both services mount:
- `./data` → `/var/lib/avantis-paper-bot/data`
- `./bootstrap.json` → `/var/lib/avantis-paper-bot/bootstrap.json` (read-only)

## GOAT knowledge base (trading doctrine)
This repo includes optional tooling to index and query the **GOAT Crypto Trading Agent Pack** (reading list + checklists) as a local-first knowledge base.

Tools live in:
- `tools/goat_kb/`

Quick start:
```bash
python3 tools/goat_kb/goat_kb_index.py \
  --root /home/boilerrat/clawd/knowledge/GOAT_Crypto_Trading_Agent_Pack \
  --db  /home/boilerrat/clawd/state/goat_kb.db

python3 tools/goat_kb/goat_kb_query.py --q "PBO" --limit 5
```

Notes:
- This is a **keyword (SQLite+FTS5) index**; vector/embeddings can be added later if needed.
- The pack itself is not committed here by default.

## Disclaimer
This code is for research/paper simulation. No financial advice.
