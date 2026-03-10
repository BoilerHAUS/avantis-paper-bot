# dashboard contract v1

## metadata
- version: v1.0.0
- owner_role: dashboard_docs
- review_cadence: weekly
- next_review_due: 2026-03-17

## objective
Lock metric definitions and API/UI behavior to prevent drift between backend summaries and dashboard rendering.

## endpoint contracts
### `/api/statuses`
- returns strategy-lane snapshot list
- each row includes `strategy_id`, snapshot metadata, and extracted status

### `/api/status?strategy_id=<id>`
- returns focused status for selected strategy id
- unknown id MUST normalize to default strategy id

### `/api/report/daily?strategy_id=<id>&date=<YYYY-MM-DD>`
summary fields include:
- `tradeCount`
- `winCount`
- `lossCount`
- `winRate`
- `realizedPnl`
- `unrealizedPnl`
- `strategy_return`
- `eth_bh_return`
- `alpha`
- `participation_ratio`

## metric formulas
- `winRate = winCount / tradeCount` (null when tradeCount = 0)
- `alpha = strategy_return - eth_bh_return`
- `participation_ratio = strategy_return / eth_bh_return` (null when denominator near zero)
- `realizedPnl` (v1 proxy) derived from equity deltas on realized events (`close|flip`)
- `unrealizedPnl` estimated from current position mark vs entry

## methodology constraints
- strategy and benchmark returns MUST use same UTC day window
- strategy return uses first vs latest cycle equity
- ETH buy-and-hold uses first vs latest cycle `last_price`

## UI rendering rules
- currency: 2 decimal places
- percentages: one decimal place where shown
- null values display as `—`
- stale-state indicators must remain visible when source data ages beyond threshold
- unknown strategy selection falls back to default id

## compatibility policy
- additive metrics are allowed if existing fields remain stable
- breaking field removals/renames require contract version bump + migration notes
- frontend must tolerate unknown extra fields without failing render

## validation
- compare API payload values against rendered UI for one selected day
- verify conservative/aggressive focused views produce lane-consistent values
- verify null/empty-state rendering on no-trade day

## related issues
- #9 strategy comparison view
- #10 benchmark panel
