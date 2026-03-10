# paper-bot-dashboard

VPS dashboard/control plane (v1 mostly read-only) for **Avantis Paper Bot**.

## What v1 does (real functionality)
- Reads snapshot + journal (JSON/JSONL) from the VPS.
- Supports strategy-aware views (`strategy_id`) with side-by-side strategy snapshot cards.
- Exposes benchmark metrics (`strategy_return`, `eth_bh_return`, `alpha`, `participation_ratio`) via API and UI.
- Displays:
  - current position (flat/long/short + notional/leverage if present)
  - last cycle timestamp + note
  - last trade time (last cycle where `plan.action != "hold"`) + time since last trade
  - equity + daily_pnl
  - candles_loaded
  - trade count / win rate / realized vs unrealized pnl (daily report)
- Health indicators:
  - marks snapshot/journal stale if not updated in >20 minutes
  - shows last mtime + minutes stale
- Timeline:
  - last ~20 cycle events (from journal)

## benchmark methodology (v1)
- window: same UTC day + strategy lane
- strategy return: `(latest_equity / first_cycle_equity) - 1`
- ETH buy-and-hold return: `(latest_price / first_cycle_price) - 1`
- alpha: `strategy_return - eth_bh_return`
- participation ratio: `strategy_return / eth_bh_return` (null when denominator is ~0)
- low-sample confidence flag: `low_sample=true` when `cycle_count < min_cycle_count_for_confidence` (default: 24 cycles)

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
