# avantis paper bot

paper-first trading system for **avantis perps** (currently `ETH/USD`) focused on reliability, risk controls, and observable operations.

---

## what this repo is

this repo runs a complete paper-trading loop:

1. **feed listener** ingests live price stream and closes 15m candles
2. **cycle runner** evaluates strategy + risk + execution plan every 15m
3. **paper execution** updates position/equity state (no live capital)
4. **journal + snapshot** persist every cycle for auditability
5. **dashboard** visualizes current state and recent behavior

all core decisions run without LLM dependency in the hot path.

---

## current status

- ✅ `apb-feed`, `apb-cycle`, and `apb-dashboard` running in production-like paper mode
- ✅ data path standardized on host bind mount:
  - `/var/lib/avantis-paper-bot/data`
- ✅ dashboard and chart flow recovered and stable after mount-path fixes
- ✅ issue-first collaboration workflow active in `BoilerHAUS`
- ⚠️ still paper-first; live trading remains gated by runbook/checklist

see:
- `boilerclaw/LIVE_RUNBOOK.md`
- `/home/boiler/.openclaw/workspace/LIVE_CHECKLIST.md` (ops companion checklist)
- `docs/strategy/EXPERIMENTATION_FRAMEWORK_V1.md` (scientific experimentation doctrine)
- `docs/strategy/EXPERIMENT_GOVERNANCE_POLICY_V1.md` (review, promotion, rejection, and rollback policy)
- `docs/roadmap/EXPERIMENTATION_ROADMAP_STATUS.md` (generated roadmap / distance-to-readiness status)
- `docs/README.md` (canonical docs index)

---

## architecture (high level)

```text
market stream
   -> feed listener
   -> candles (jsonl)
   -> cycle (strategy + risk + paper execution)
   -> journal/state snapshot
   -> dashboard
```

key persisted outputs:
- `data/candles/ETH-USD-15m.jsonl`
- conservative lane (default/backward-compatible):
  - `data/journal/YYYY-MM-DD.jsonl`
  - `data/state/current.json`
  - `data/state/snapshot.json`
- non-default strategy lanes:
  - `data/strategies/<strategy_id>/journal/YYYY-MM-DD.jsonl`
  - `data/strategies/<strategy_id>/state/current.json`
  - `data/strategies/<strategy_id>/state/snapshot.json`

---

## quickstart (local)

### 1) install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) run feed listener

```bash
export AVANTIS_WS_URL="wss://YOUR_ENDPOINT"
python -m bot.feed_listener --pair "ETH/USD" --tf-min 15
```

### 3) run one cycle manually

```bash
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15 --strategy-id conservative
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15 --strategy-id aggressive
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15 --strategy-id super_aggressive
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15 --strategy-id edge_filtered
```

### 4) run a deterministic fixed-window replay

```bash
python3 -m bot.replay \
  --pair "ETH/USD" \
  --tf-min 15 \
  --strategy-id conservative \
  --compare-strategy-id aggressive \
  --candles-file data/candles/ETH-USD-15m.jsonl \
  --start-ts 1700000000 \
  --end-ts 1700863200
```

artifacts are written under `data/replays/<pair>-<tf>m/<start>-<end>/...` with stable names:
- `manifest.json`
- `summary.json`
- `cycles.jsonl`
- `trades.jsonl`
- `equity.jsonl`

the replay path uses stored candles only, records skips/vetoes plus regime/setup labels, and avoids volatile timestamps in diff-critical outputs.
Decision artifact field meanings and versioning live in [docs/ARTIFACT_CONTRACT_V1.md](docs/ARTIFACT_CONTRACT_V1.md).

---

## docker deployment

```bash
cp config.example.json bootstrap.json
docker compose build
docker compose up -d
```

services:
- `apb-feed`
- `apb-cycle`
- `apb-dashboard` (port `3030`)

notes:
- hermes stream drops can occur; feed listener auto-reconnects.
- runtime is designed to avoid pip-install-on-start noise.

---

## config

- baseline config file: `config.example.json`
- runtime config path: `APB_CONFIG=/path/to/config.json`

risk controls are explicit and should be treated as first-class change surfaces:
- leverage caps
- deployed capital caps
- kill-switch thresholds
- sizing bounds
- confidence thresholds (`min_confidence_to_trade`)

strategy behavior can be profile-driven (`strategy.profiles`), so aggressive mode can use
higher deployment + lower confidence gates while conservative remains unchanged.

`edge_filtered` is an additive paper experiment lane using a stricter confidence gate
(`min_confidence_to_trade: 0.60`) to skip lower-conviction entries.

any change to these should go through reviewed PRs only.

---

## collaboration workflow (required)

for work in `BoilerHAUS/avantis-paper-bot`:

1. open/create issue
2. create branch on agent fork
3. open PR to `Main`
4. human approval required
5. merge
6. issue closes (`Closes #...`)

no direct pushes to protected `Main`.

see:
- `docs/REPO_UPDATE_PROCESS.md`
- `scripts/apply-branch-protection.sh`
- `scripts/check-branch-protection.sh`

---

## disclaimer

research + paper simulation only. not financial advice.
