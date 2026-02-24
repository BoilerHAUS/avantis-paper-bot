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
All config is via env vars + CLI flags for now.

Planned:
- `config.yaml` for strategy + risk params
- separate process supervision (systemd/docker) for the feed listener

## Disclaimer
This code is for research/paper simulation. No financial advice.
