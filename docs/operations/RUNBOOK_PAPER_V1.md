# paper operations runbook v1

## metadata
- version: v1.0.0
- owner_role: operations_docs
- review_cadence: weekly
- next_review_due: 2026-03-17

## objective
Provide executable, operator-first steps to start, verify, recover, and rollback the paper bot safely.

## scope
- paper-mode runtime (`apb-feed`, `apb-cycle`, `apb-dashboard`)
- health verification and first-response recovery
- rollback to last-known-good compose/image state

## start checklist
1. confirm branch/deploy source is merged `Main`.
2. confirm config file exists and is valid:
```bash
python scripts/validate_config.py
```
3. start services:
```bash
docker compose up -d --build
```
4. confirm all services are running:
```bash
docker compose ps
```

## health verification (commands + expected output)
### feed freshness
```bash
tail -n 2 data/candles/ETH-USD-15m.jsonl
```
Expected: recent closed-candle entries with increasing timestamps.

### cycle freshness
```bash
tail -n 3 data/journal/$(date -u +%F).jsonl
```
Expected: cycle events with current UTC date and non-empty `plan/state` fields.

### dashboard health
```bash
curl -s http://localhost:3030/api/status | jq '.ok, .status.equity, .status.position.label'
```
Expected: `true` and parseable status fields.

## stop conditions (do NOT proceed)
Stop deploy/ops progression immediately if any are true:
- config validation fails
- candles are stale > 2 cycles
- cycle journal is not advancing
- dashboard API parse errors persist after service restart
- risk settings changed without reviewed PR and explicit approval

## recovery playbooks
### A) feed stale
1. check feed logs:
```bash
docker compose logs --tail=200 apb-feed
```
2. restart feed service:
```bash
docker compose restart apb-feed
```
3. verify candle file updates within one cycle.

### B) cycle stale
1. inspect cycle logs:
```bash
docker compose logs --tail=200 apb-cycle
```
2. run one manual cycle command in container/shell context.
3. if manual cycle succeeds, restart `apb-cycle`.

### C) mount/path mismatch
1. verify bind mounts in `docker-compose.yml`.
2. confirm expected files exist under mounted `data/` path.
3. restart services after correcting path mapping.

## rollback path (last-known-good)
1. identify last-known-good commit/image tag.
2. revert compose/image refs to known-good.
3. redeploy:
```bash
docker compose down
docker compose up -d
```
4. rerun health verification section fully before declaring recovery.

## post-incident evidence logging
Record at minimum:
- incident timestamp (UTC)
- failure signature/log snippet
- attempted actions + outcome
- final resolution and rollback status
- follow-up issue id

## ownership
- primary: boilermolt (docs/process)
- technical runtime review: boilerclaw
