# Boilerclaw — Memory Seed (facts to preload)

- Repo source of truth: `https://github.com/boilermolt/avantis-paper-bot`
- Asset/pair: **ETH/USD**
- Cadence: **15 minutes**
- Risk defaults (bootstrap):
  - per-trade risk target: 1% equity, clamped $10–$50
  - max leverage: 2x
  - max deployed: 75% equity
  - daily kill switch: -10% equity
- Feed default: **Pyth Hermes** (HTTP streaming)
- AI is observer-only by default (`ai.enabled=false` in config)

## What counts as a trade event
- `plan.action` is `open|close|flip|scale` (anything but `hold`)
- OR `state.position` differs vs previous cycle

## Where to look for truth
- Journal: `data/journal/YYYY-MM-DD.jsonl`
- Snapshot: `data/state/snapshot.json`
- Candles: `data/candles/ETH-USD-15m.jsonl`
