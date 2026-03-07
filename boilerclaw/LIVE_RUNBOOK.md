# LIVE_RUNBOOK.md — Avantis Bot

Operational runbook for pre-live drills and early live trading.

## 1) Preflight (every deploy)

1. Confirm containers are up:
   - `docker ps | egrep "code-apb|apb-"`
2. Confirm bind mount is live:
   - `docker inspect code-apb-cycle-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'`
   - Expect `/var/lib/avantis-paper-bot/data -> /var/lib/avantis-paper-bot/data`
3. Confirm fresh writes on host path:
   - `stat /var/lib/avantis-paper-bot/data/state/snapshot.json`
   - `tail -n 1 /var/lib/avantis-paper-bot/data/journal/$(date -u +%F).jsonl`
4. Confirm candle growth:
   - `wc -l /var/lib/avantis-paper-bot/data/candles/ETH-USD-15m.jsonl`
   - Repeat in ~15m; line count should increase.

---

## 2) Kill-switch drill (paper)

Goal: verify hard stop behavior before live.

1. Set a test kill-switch threshold that triggers quickly.
2. Let cycle run until halted state is reached.
3. Verify:
   - no new entries are opened
   - state/journal show halted condition clearly
   - dashboard reflects halted state
4. Revert to intended production threshold.

Pass if all 3 verification points are true.

---

## 3) Feed-stall drill (paper)

Goal: verify automatic recovery from stale feed.

1. Temporarily stop feed container:
   - `docker stop code-apb-feed-1`
2. Wait until stale condition is detected.
3. Start feed:
   - `docker start code-apb-feed-1`
4. Verify:
   - candles resume
   - cycle recovers without manual state repair
   - no broken JSON lines in journal/snapshot

Pass if recovery is automatic and clean.

---

## 4) Execution sanity (before first live order)

1. Validate order-size constraints match venue min/max.
2. Validate tick/step rounding behavior.
3. Validate rejection handling path (simulate/force one reject if possible).
4. Validate slippage assumptions vs actual fills.

Pass if no silent failures and no invalid orders.

---

## 5) Tiny-live phase (24–72h)

- Min practical notional only
- Max 1 concurrent position
- No strategy/config changes during window
- Daily reconciliation:
  - position
  - fills
  - PnL
  - journal vs account state

Escalate to larger size only after clean window.

---

## 6) Incident response

### A) Candles stale
- Check feed logs: `docker logs --since 20m code-apb-feed-1`
- Restart feed only: `docker restart code-apb-feed-1`
- Confirm candle growth returns.

### B) Cycle not writing
- Check cycle logs: `docker logs --since 20m code-apb-cycle-1`
- Confirm snapshot/journal paths are writable.
- Restart cycle: `docker restart code-apb-cycle-1`

### C) Dashboard stale but bot healthy
- Confirm host files are fresh first.
- Restart dashboard: `docker restart code-apb-dashboard-1`

---

## 7) Non-negotiables

- Never push directly to `main`.
- Never deploy unreviewed risk changes.
- One change set per PR (small, reversible).
- If behavior is unexplained, stop and investigate before continuing.
