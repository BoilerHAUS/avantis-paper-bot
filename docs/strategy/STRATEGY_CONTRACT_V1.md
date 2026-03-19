# strategy contract v1

## metadata
- version: v1.0.0
- owner_role: strategy_docs
- review_cadence: weekly
- next_review_due: 2026-03-17

## objective
Define auditable strategy-lane behavior and profile configuration for `conservative` and `aggressive` modes.

## active directional lane
The current tradeable lane is `trend_continuation`.

- trade only when the regime classifier confirms `trend_up` or `trend_down`
- `trend_up`: entries are restricted to `pullback_long` or `breakout_long`
- `trend_down`: entries are restricted to `failed_bounce_short` or `breakdown_short`
- `range` and `transition` do not have a trade lane in this slice; runtime MUST stand down
- once the trend lane is active, counter-trend entries are not allowed
- open positions may be held between entry candles, but MUST stand down and close on deterministic invalidation

## deterministic invalidation / stand-down
- `transition_stand_down`: classifier marks the window uncertain or transitional
- `confidence_collapse`: regime confidence falls below the trend-lane minimum
- `regime_not_confirmed`: classifier is not in a confirmed trend regime
- `trend_structure_lost`: fast/slow trend structure no longer points in the regime direction

When one of these reasons is active:
- no new entry may be opened
- an existing position in the lane MUST close rather than flip directly into the opposite side

## strategy ids and fallback
- allowed ids come from `strategy.allowed_ids`
- default id comes from `strategy.default_id`
- unknown strategy id MUST normalize to default id at API/UI boundaries

## profile schema (strategy.profiles.<id>)
- `risk_pct`
- `max_deployed_pct`
- `max_leverage`
- `min_confidence_to_trade`
- `trend_weight_in_regime`
- `adx_threshold`
- `tie_break_to_trend`
- `tie_break_min_confidence`
- `regime_confidence_floor`
- `trend_lane_min_confidence`
- `continuation_lookback`

If a field is omitted in profile, runtime MUST use global base risk/signal defaults.

## non-overridable global risk boundaries
Profile tuning MUST NOT bypass these invariants:
- daily kill switch (`risk.daily_kill_switch_pct`)
- min collateral floor (`risk.min_collateral_usd`)
- hard leverage/deployment safety checks in runtime sizing path

## config knob -> behavior mapping
| knob | runtime effect |
|---|---|
| `min_confidence_to_trade` | lower than threshold => hold/skip |
| `max_deployed_pct` | caps target notional vs equity |
| `max_leverage` | caps leverage selected in tiered sizing |
| `trend_weight_in_regime` | increases trend influence in regime resolver |
| `adx_threshold` | controls regime activation sensitivity |
| `tie_break_to_trend` | resolves tie/noise toward trend direction in regime |
| `regime_confidence_floor` | minimum confidence in confirmed regime decisions |
| `trend_lane_min_confidence` | minimum classifier confidence required before the continuation lane may trade |
| `continuation_lookback` | breakout/breakdown lookback used by continuation setups |

## required journaling fields
Each cycle/trade artifact MUST include:
- `strategy_id`
- `regime_classifier`: schema_version, label, confidence, probabilities, stand_down, uncertainty_score
- `analysis.setup_label`, `analysis.strategy_lane`, `analysis.invalidation_reason`
- signal: desired/confidence/strategy/note
- plan: action, leverage, risk_usd, stop/take fields
- state: equity, daily_pnl, position, last_price

## regime classifier contract
- classifier schema version: `regime_classifier.v1`
- canonical labels: `trend_up`, `trend_down`, `range`, `transition`
- `transition` MUST be preserved as a first-class outcome
- downstream consumers MAY stand down when `regime_classifier.stand_down == true`
- strategy changes in this lane MUST NOT silently introduce alternate regime labels

## versioning + changelog
### profile changelog
- conservative v1.0.0: baseline defensive defaults
- aggressive v1.0.0: lower confidence gate + higher deploy/risk profile with regime tie-break capability

Any profile behavior change MUST:
1. bump version (doc + config release note)
2. include replay/validation evidence in PR
3. annotate expected KPI impact

## validation checklist
- replay conservative vs aggressive on same window
- compare exposure, drawdown, realized pnl, benchmark alpha
- confirm fallback behavior for missing/unknown strategy id

## related issues
- #7 dual-strategy foundation
- #8 aggressive mode v1
- #9 strategy-side dashboard
- #10 benchmark/alpha panel
