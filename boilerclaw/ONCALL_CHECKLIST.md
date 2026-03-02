# On-call checklist (VPS: Avantis paper bot)

This is the **operator-facing** checklist for the VPS-resident agent.

## Source of truth
- Repo: https://github.com/boilermolt/avantis-paper-bot
- VPS clone: `/opt/boilerclaw/avantis-paper-bot`

## Deployed paths (current VPS)
These are the paths we actually observed on the VPS during setup.

- Compose dir (Dokploy):
  - `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/`
- Compose file:
  - `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/docker-compose.yml`
- Bootstrap config (must be a **file**, not a directory):
  - `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/bootstrap.json`
- Host data dir (mounted into containers as `/var/lib/avantis-paper-bot/data`):
  - `/etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/`

## What “healthy” looks like (15m cadence)
### A) Containers up
- `docker ps --format 'table {{.Names}}\t{{.Status}}' | egrep 'code-apb-(feed|cycle)'`

### B) Feed producing candles
- `wc -l /etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/candles/ETH-USD-15m.jsonl`
- Expect this to increase over time.

If candles stuck:
- `docker logs --since 15m code-apb-feed-1 | tail -n 80`
- Known failure mode: Hermes stream drops (RemoteProtocolError / incomplete chunked read). Repo now auto-reconnects; if you’re on an old image, rebuild.

### C) Cycle producing outputs
- Journal line appended roughly every 15m:
  - `tail -n 1 /etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/journal/$(date -u +%F).jsonl`
- Snapshot updated:
  - `ls -la /etc/dokploy/compose/avantis-paper-bot-nsnxrq/code/data/state/snapshot.json`

If cycle fails:
- `docker logs --since 60m code-apb-cycle-1 | tail -n 120`
- Common: bootstrap mount wrong (bootstrap.json accidentally became a directory).

## What counts as a trade event
Alert/report when:
- `plan.action != "hold"` (open/close/flip/scale)
- OR `state.position` changes vs previous cycle

## Monitoring scripts (VPS)
- Event monitor (15m): `/tmp/apb_notify_last_cycle.sh`
- Daily summaries: `/tmp/apb_daily_summary.sh` (05:30 + 17:30)
- Cron: `crontab -l`

## Boundaries
- Do not change risk params without explicit approval.
- No live trading.
- Prefer small, reversible changes.
