# Decision Artifact Contract v1

## Version
- `artifact_contract_version`: `decision_artifact.v1`

This contract applies to live cycle journal rows, live snapshots, and replay cycle artifacts.

## Provenance
Each decision artifact MUST include a `provenance` object with:
- `artifact_contract_version`: repeated for local validation
- `strategy_id`: active strategy lane
- `strategy_fingerprint`: stable hash of the effective strategy/risk config used for the decision
- `pair`: market pair as configured for the run
- `symbol`: currently mirrors `pair` until runtime exposes a distinct symbol field
- `timeframe_min`: candle timeframe in minutes

## Effective runtime thresholds / config
Each decision artifact MUST include an `effective_config` object with compact decision-relevant runtime values:
- `risk.min_confidence_to_trade`
- `risk.risk_pct`, `risk.min_risk_usd`, `risk.max_risk_usd`
- `risk.max_deployed_pct`, `risk.max_leverage`, `risk.daily_kill_switch_pct`
- `signal.trend_weight`, `signal.trend_weight_in_regime`, `signal.mr_weight`
- `signal.adx_threshold`, `signal.regime_confidence_floor`
- `signal.tie_break_to_trend`, `signal.tie_break_min_confidence`

This object is intentionally compact: enough for forensic review to explain the effective thresholds in force without embedding the entire raw config blob.

## Canonical decision fields
Each decision artifact MUST include a `decision` object with:
- `regime`: machine-comparable regime label such as `trend_up`, `trend_down`, `range`, `transition`, `unknown`
- `setup_type`: machine-comparable setup label such as `trend_follow_long`, `trend_follow_short`, `regime_tie_break`, `no_trade`
- `decision_status`: canonical outcome for the cycle
- `decision_reason`: canonical positive-path reason code when the bot acts or intentionally holds a live position
- `block_reason`: canonical negative-path reason code when the bot skips or vetoes
- `exit_reason`: canonical exit reason code when the bot closes, flips, or is forced out

## `decision_status`
Allowed values in this slice:
- `open`
- `close`
- `flip`
- `scale`
- `hold`
- `skip`
- `veto`
- `forced_exit`

## Reason codes
Current reason codes emitted in this slice:
- `decision_reason`: `entry_signal`, `add_signal`, `reverse_signal`, `existing_position`
- `block_reason`: `no_market_data`, `signal_flat`, `no_setup`, `confidence_below_min`, `invalid_stop`, `risk_gate`
- `exit_reason`: `signal_flat`, `reverse_signal`, `position_exit`, `stop_loss`

## Notes vs canonical fields
Human-readable notes remain available for debugging:
- `regime_note`
- `signal_note`
- `plan_note`

These notes are secondary. Downstream consumers should key comparisons and logic off the canonical fields above, not free-form note text.

## Compatibility
- Replay artifacts keep `decision.status` and `decision.reason` as aliases of canonical values for a reversible migration.
- Existing `signal`, `plan`, `analysis`, and `state` payloads remain intact.
