# VPS Runbook (paper bot)

## Fast health checks
1) Containers up
- `docker ps | egrep "apb-|code-apb"`

2) Feed is producing candles
- `wc -l data/candles/ETH-USD-15m.jsonl`
- look for growth over time

3) Cycle is producing journal + snapshot
- `tail -n 1 data/journal/$(date -u +%F).jsonl`
- `ls -la data/state/snapshot.json`

## Common failures
### Candles stuck / not growing
- Check feed logs: `docker logs --since 10m <feed-container>`
- Hermes stream may drop; ensure feed auto-reconnects.

### Cycle crashing on bootstrap
- Ensure `bootstrap.json` is a file, not a directory.

## Monitoring expectations
- Trade event when `plan.action != hold` OR position changes.
- Summaries should include:
  - position + last action
  - time since last trade
  - any guardrail warnings
