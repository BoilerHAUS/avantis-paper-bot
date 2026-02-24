---
name: avantis-paper-bot
description: Run the Avantis paper bot (feed listener, candle builder, and 15m cycle) and report status/snapshots.
version: 0.0.1
---

# Avantis Paper Bot (Skill scaffold)

This is an **OpenClaw Skill scaffold** for operating the repo.

## What it does
- Start/stop a **continuous feed listener** that builds **15m candles** for ETH/USD.
- Run one **paper cycle** (deterministic) that writes:
  - journal JSONL
  - state JSON
  - snapshot JSON

## Safety
- Paper-only: no on-chain signing or tx broadcast.
- The trade loop must never require an LLM call.

## Commands (manual for now)
From the repo root:

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### Run feed listener
```bash
export AVANTIS_WS_URL="wss://..."
python -m bot.feed_listener --pair "ETH/USD" --tf-min 15
```

### Run one cycle
```bash
python -m bot.run_cycle --pair "ETH/USD" --tf-min 15
```

## Planned: OpenClaw integration
- Provide a thin command wrapper so the agent can:
  - check latest snapshot
  - tail journal
  - restart feed listener
