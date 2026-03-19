# Architecture & Trading Logic (Avantis Paper Bot)

This repo is a **paper-first** scaffold for trading **Avantis perps** (starting with **ETH/USD**) on a **fixed 15-minute cadence**, with a strict separation:

- **Feed (real-time)**: price stream → build OHLC candles (default: Pyth Hermes)
- **Cycle (every 15m)**: read recent candles → generate deterministic signal → size via risk manager → paper-execute → write journal + snapshot
- **AI/agent (optional)**: *observer/summarizer* only in v0; not required for trading decisions

## Data flow

1) `bot.feed_listener`
   - Default mode: `FEED_MODE=hermes`
   - Resolves `ETH/USD` → a Pyth price id
   - Streams updates and aggregates them into OHLC candles via `CandleBuilder`
   - Writes closed candles as JSONL:
     - `data/candles/ETH-USD-15m.jsonl`

2) `bot.run_cycle` (every 900s)
   - Loads last N candles (default 200)
   - Loads `PaperState` from `data/state/current.json` (equity/position/daily_pnl)
   - Computes a bounded `RiskBudget`
   - Computes one deterministic `regime_classifier` object
   - Computes a deterministic `Signal` (long/short/flat)
   - Converts `Signal → OrderPlan` (ATR stops + size + leverage cap)
   - Executes the plan in the paper engine (sim fills + slippage)
   - Appends a single **cycle event** to the journal:
     - `data/journal/YYYY-MM-DD.jsonl`
   - Writes dashboard snapshot:
     - `data/state/snapshot.json`

3) `bot.replay` (offline fixed-window evaluation)
   - Loads stored candles from JSONL only
   - Replays one strategy, or two strategies on the same frozen window, without feed or live execution dependencies
   - Writes deterministic artifacts under `data/replays/...`:
     - `manifest.json`
     - `summary.json`
     - `cycles.jsonl`
     - `trades.jsonl`
     - `equity.jsonl`
  - Artifact rows include explicit regime classifier output, setup labels, skips/vetoes, execution events, and strategy/config fingerprints

## What decides long vs short?

### Signals (`src/bot/strategies.py`)
`choose_signal(closes)` combines two deterministic strategies:

- **Trend (default bias)**
  - fast/slow SMA cross (20 vs 50)
  - plus a crude slope proxy (fast SMA delta over 3 bars)
  - Long when: `fast > slow` AND `slope > 0`
  - Short when: `fast < slow` AND `slope < 0`

- **Mean reversion**
  - z-score of close vs SMA window (50)
  - Long when: `z <= -1.5` (oversold)
  - Short when: `z >= +1.5` (overbought)

Resolver:
- if both agree (non-flat), take that direction
- else prefer the one with higher confidence

### Regime classifier (`src/bot/strategies.py`)
`classify_regime(candles)` produces one deterministic object with schema version `regime_classifier.v1`:

- canonical labels: `trend_up`, `trend_down`, `range`, `transition`
- bounded `confidence` plus normalized class probabilities
- `stand_down` for uncertain/transition windows
- interpretable features (`adx`, spread, slope, trend strength, conflict score)

`transition` is the normal output for regime boundaries, insufficient structure, and noisy conflict. It is not treated as an error.

### Risk sizing (`src/bot/risk.py`)
`plan_from_signal(...)` converts the signal into an order plan with hard bounds:

- Stop distance: ATR(14) * 2.0 (fallback 0.75%)
- Position notional sized so loss at stop ≈ `risk_usd`
- Caps:
  - `max_deployed_pct` (default 75% equity)
  - `max_leverage` (default 2x)
  - `min_collateral_usd`
- Leverage tiering by confidence (bootstrap):
  - below 0.60 confidence → skip (hold)
  - 0.60–0.74 → 2x
  - 0.74–0.84 → 3x
  - 0.84–0.92 → 4x
  - ≥0.92 → 5x
  - plus strategy-specific cap: mean reversion max 3x

### Paper execution (`src/bot/paper_engine.py`)
- Single position at a time
- Implements `open`, `close`, `flip`, `scale`, `hold`
- Simulated fills via slippage (currently fixed bps in the cycle)
- Updates equity + daily PnL

## Journal schema (v0)

The journal is JSONL with one event per cycle:

- `type`: always `"cycle"` currently
- `ts`: unix timestamp seconds
- `signal`: `{desired,long|short|flat, confidence, strategy, note}`
- `regime_classifier`: `{schema_version, label, confidence, probabilities, stand_down, uncertainty_score, note, features}`
- `plan`: `{action, side, target_notional_usd, collateral_usd, leverage, stop_loss, take_profit, risk_usd, note}`
- `state`: `{equity, daily_pnl, position, last_price}`

A "trade event" is inferred when:
- `plan.action != "hold"` OR
- `state.position` changes vs previous cycle

## Replay artifact contract (v0)

The replay harness is the deterministic evidence path for strategy evaluation on a fixed candle window.

- `manifest.json`
  - replay contract version
  - symbol/timeframe/window
  - strategy id + strategy/config fingerprint
  - effective risk/signal config snapshot
  - classifier schema version
- `summary.json`
  - ending equity / net pnl / return
  - max drawdown
  - decision counts (`trade`, `skip`, `veto`)
  - regime and setup coverage counts
- `cycles.jsonl`
  - one deterministic decision row per candle in the scored window
  - includes signal, plan, explicit `regime_classifier`, regime/setup labels, risk budget, execution events, and resulting paper state
- `trades.jsonl`
  - flattened execution events (`open`, `close`, `flip_*`, `stop_loss`, `take_profit_partial`, `scale`)
- `equity.jsonl`
  - replay equity curve aligned to the fixed candle window

Boundary for this first slice:
- one symbol/timeframe per replay
- one candle file per replay
- same-window two-strategy comparison is supported via paired single-strategy bundles plus one comparison JSON

## AI / Agent involvement

Config includes an `ai` block (see `config.example.json`) but it is **disabled by default**.

Design intent:
- The deterministic engine runs on schedule without any LLM dependency.
- The agent’s job is:
  - monitoring (trade happened? position change? risk breach?)
  - summaries (morning/evening)
  - suggestions *within hard limits*

In v0, the agent should be treated as **observer-only**.

## Known operational pitfalls (VPS learnings)

- Hermes stream may drop (e.g. `RemoteProtocolError incomplete chunked read`). The feed listener should auto-reconnect.
- Be explicit about where `data/` lives (host path vs container path). Prefer a single source of truth.
- Ensure `bootstrap.json` is a **file**, not a directory, when mounting into containers.
