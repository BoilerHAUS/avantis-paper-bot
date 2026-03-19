# market regime classifier v1

## metadata
- schema_version: `regime_classifier.v1`
- owner_role: strategy_engine
- scope: classification only

## objective
Provide one deterministic regime classification object per cycle/replay decision path for the 15m ETH strategy engine.

## canonical labels
- `trend_up`
- `trend_down`
- `range`
- `transition`

`transition` is a first-class output. It is the expected label for boundary conditions, insufficient structure, and noisy/conflicted windows. It is not an error bucket.

## output schema
```json
{
  "schema_version": "regime_classifier.v1",
  "label": "transition",
  "confidence": 0.41,
  "probabilities": {
    "trend_up": 0.18,
    "trend_down": 0.11,
    "range": 0.30,
    "transition": 0.41
  },
  "stand_down": true,
  "uncertainty_score": 0.59,
  "note": "adx=18.4 spread=0.0011 slope=0.0003",
  "features": {
    "adx": 18.4,
    "adx_strength": 0.46,
    "spread_ratio": 0.0011,
    "spread_strength": 0.37,
    "slope_ratio": 0.0003,
    "slope_strength": 0.19,
    "trend_strength": 0.34,
    "trend_ready": true,
    "trend_desired": "flat",
    "trend_confidence": 0.30,
    "mean_reversion_desired": "short",
    "mean_reversion_confidence": 0.52,
    "conflict_score": 0.66
  }
}
```

## invariants
- exactly one classifier object per scored cycle
- `confidence`, each probability, and `uncertainty_score` are bounded to `[0.0, 1.0]`
- probabilities sum to `1.0` after deterministic rounding adjustment
- `label` is the argmax of `probabilities`
- `stand_down` is the downstream uncertainty signal and MUST be preserved in artifacts

## downstream use
- `run_cycle` journal rows include `regime_classifier`
- dashboard snapshot includes `regime_classifier`
- replay `cycles.jsonl` rows include `analysis.regime_classifier`
- replay manifest declares the classifier schema version

## rollback note
This change is reversible by removing `regime_classifier` fields and restoring the previous inline regime label resolver in `src/bot/strategies.py`.
