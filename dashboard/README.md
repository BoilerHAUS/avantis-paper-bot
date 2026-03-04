# paper-bot-dashboard

VPS dashboard/control plane (v1 mostly read-only) for **Avantis Paper Bot**.

## What v1 does (real functionality)
- Reads snapshot + journal (JSON/JSONL) from the VPS.
- Displays:
  - current position (flat/long/short + notional/leverage if present)
  - last cycle timestamp + note
  - last trade time (last cycle where `plan.action != "hold"`) + time since last trade
  - equity + daily_pnl
  - candles_loaded
- Health indicators:
  - marks snapshot/journal stale if not updated in >20 minutes
  - shows last mtime + minutes stale
- Timeline:
  - last ~20 cycle events (from journal)

## What v1 does NOT do
- No live trading.
- No control-plane actions; controls are present but disabled and show “Not wired yet”.

## Run locally
```bash
npm install
npm start
# open http://127.0.0.1:3030
```

## Deploy
See [DEPLOY.md](./DEPLOY.md).
