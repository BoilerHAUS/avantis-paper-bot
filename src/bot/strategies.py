"""Deterministic strategies (v0.2).

Adds a weighted blend with trend-day regime detection:
- Trend signal (fast/slow SMA + slope)
- Mean-reversion signal (z-score)
- Regime gate combines MA-structure + ADX strength
"""

from __future__ import annotations

from dataclasses import dataclass

from .indicators import adx, sma, zscore
from .models import MarketRegime, RegimeClassifierOutput, Signal

REGIME_CLASSIFIER_SCHEMA_VERSION = "regime_classifier.v1"


@dataclass
class StrategyConfig:
    trend_fast: int = 20
    trend_slow: int = 50
    mr_window: int = 50
    mr_entry_z: float = 1.5

    # Weighted blend behavior
    trend_weight: float = 1.0
    mr_weight: float = 1.0
    trend_weight_in_regime: float = 1.35  # medium priority

    # Combined trend-day regime filter
    adx_n: int = 14
    adx_threshold: float = 20.0
    min_spread_ratio: float = 0.0015  # |fast-slow|/slow
    min_slope_ratio: float = 0.0008

    # Aggressive-mode knobs
    tie_break_to_trend: bool = False
    tie_break_min_confidence: float = 0.0
    regime_confidence_floor: float = 0.0


@dataclass
class SignalAnalysis:
    signal: Signal
    trend_signal: Signal
    mean_reversion_signal: Signal
    regime: RegimeClassifierOutput
    setup_label: str

    @property
    def regime_label(self) -> str:
        return self.regime.label.value

    @property
    def regime_note(self) -> str:
        return self.regime.note


def trend_signal(closes: list[float], cfg: StrategyConfig) -> Signal:
    f = sma(closes, cfg.trend_fast)
    s = sma(closes, cfg.trend_slow)
    if f is None or s is None:
        return Signal(desired="flat", confidence=0.0, strategy="trend", note="insufficient candles")

    if len(closes) < cfg.trend_fast + 3:
        slope = 0.0
    else:
        f_prev = sma(closes[:-3], cfg.trend_fast) or f
        slope = (f - f_prev) / f_prev if f_prev else 0.0

    if f > s and slope > 0:
        conf = min(1.0, abs(slope) * 70)
        return Signal(desired="long", confidence=conf, strategy="trend", note=f"fast>slo & slope={slope:.4f}")
    if f < s and slope < 0:
        conf = min(1.0, abs(slope) * 70)
        return Signal(desired="short", confidence=conf, strategy="trend", note=f"fast<slo & slope={slope:.4f}")

    return Signal(desired="flat", confidence=0.3, strategy="trend", note=f"mixed (fast={f:.2f} slow={s:.2f} slope={slope:.4f})")


def mean_reversion_signal(closes: list[float], cfg: StrategyConfig) -> Signal:
    z = zscore(closes, cfg.mr_window)
    if z is None:
        return Signal(desired="flat", confidence=0.0, strategy="mean_reversion", note="insufficient candles")

    if z <= -cfg.mr_entry_z:
        conf = min(1.0, abs(z) / (cfg.mr_entry_z * 2))
        return Signal(desired="long", confidence=conf, strategy="mean_reversion", note=f"z={z:.2f} (oversold)")
    if z >= cfg.mr_entry_z:
        conf = min(1.0, abs(z) / (cfg.mr_entry_z * 2))
        return Signal(desired="short", confidence=conf, strategy="mean_reversion", note=f"z={z:.2f} (overbought)")

    return Signal(desired="flat", confidence=0.4, strategy="mean_reversion", note=f"z={z:.2f} (neutral)")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_scores(scores: dict[MarketRegime, float]) -> dict[str, float]:
    total = sum(max(0.0, score) for score in scores.values())
    if total <= 0:
        equal = round(1.0 / len(scores), 6)
        out = {regime.value: equal for regime in scores}
        remainder = round(1.0 - sum(out.values()), 6)
        out[MarketRegime.TRANSITION.value] = round(out[MarketRegime.TRANSITION.value] + remainder, 6)
        return out

    normalized = {
        regime.value: round(max(0.0, score) / total, 6)
        for regime, score in scores.items()
    }
    diff = round(1.0 - sum(normalized.values()), 6)
    top_regime = max(scores, key=scores.get).value
    normalized[top_regime] = round(normalized[top_regime] + diff, 6)
    return normalized


def _trend_features(
    closes: list[float], highs: list[float], lows: list[float], cfg: StrategyConfig
) -> tuple[dict[str, float | str | bool | None], str]:
    f = sma(closes, cfg.trend_fast)
    s = sma(closes, cfg.trend_slow)
    if f is None or s is None or s == 0:
        return (
            {
                "adx": None,
                "adx_strength": 0.0,
                "spread_ratio": 0.0,
                "spread_strength": 0.0,
                "slope_ratio": 0.0,
                "slope_strength": 0.0,
                "trend_strength": 0.0,
                "trend_ready": False,
            },
            "insufficient ma",
        )

    if len(closes) < cfg.trend_fast + 3:
        slope = 0.0
    else:
        f_prev = sma(closes[:-3], cfg.trend_fast) or f
        slope = (f - f_prev) / f_prev if f_prev else 0.0

    spread = abs((f - s) / s)
    a = adx(highs, lows, closes, n=cfg.adx_n)
    if a is None:
        return (
            {
                "adx": None,
                "adx_strength": 0.0,
                "spread_ratio": round(spread, 6),
                "spread_strength": _clamp01(spread / max(cfg.min_spread_ratio, 1e-9)),
                "slope_ratio": round(abs(slope), 6),
                "slope_strength": _clamp01(abs(slope) / max(cfg.min_slope_ratio, 1e-9)),
                "trend_strength": 0.0,
                "trend_ready": False,
            },
            "insufficient adx",
        )

    adx_strength = _clamp01(a / max(cfg.adx_threshold * 2.0, 1e-9))
    spread_strength = _clamp01(spread / max(cfg.min_spread_ratio * 2.0, 1e-9))
    slope_strength = _clamp01(abs(slope) / max(cfg.min_slope_ratio * 2.0, 1e-9))
    trend_strength = round((adx_strength + spread_strength + slope_strength) / 3.0, 6)
    return (
        {
            "adx": round(a, 6),
            "adx_strength": round(adx_strength, 6),
            "spread_ratio": round(spread, 6),
            "spread_strength": round(spread_strength, 6),
            "slope_ratio": round(abs(slope), 6),
            "slope_strength": round(slope_strength, 6),
            "trend_strength": trend_strength,
            "trend_ready": True,
        },
        f"adx={a:.1f} spread={spread:.4f} slope={slope:.4f}",
    )


def classify_regime(candles: list[dict], cfg: StrategyConfig | None = None) -> RegimeClassifierOutput:
    cfg = cfg or StrategyConfig()
    closes = [float(c["c"]) for c in candles if "c" in c]
    highs = [float(c["h"]) for c in candles if "h" in c]
    lows = [float(c["l"]) for c in candles if "l" in c]

    if not closes:
        probabilities = _normalize_scores(
            {
                MarketRegime.TREND_UP: 0.0,
                MarketRegime.TREND_DOWN: 0.0,
                MarketRegime.RANGE: 0.0,
                MarketRegime.TRANSITION: 1.0,
            }
        )
        return RegimeClassifierOutput(
            schema_version=REGIME_CLASSIFIER_SCHEMA_VERSION,
            label=MarketRegime.TRANSITION,
            confidence=1.0,
            probabilities=probabilities,
            stand_down=True,
            uncertainty_score=1.0,
            note="no candles",
            features={
                "trend_ready": False,
                "trend_desired": "flat",
                "trend_confidence": 0.0,
                "mean_reversion_desired": "flat",
                "mean_reversion_confidence": 0.0,
                "conflict_score": 1.0,
            },
        )

    trend = trend_signal(closes, cfg)
    mean_reversion = mean_reversion_signal(closes, cfg)
    trend_features, note = _trend_features(closes, highs, lows, cfg)

    trend_strength = float(trend_features["trend_strength"])
    mr_active = mean_reversion.desired in {"long", "short"}
    mr_strength = mean_reversion.confidence if mr_active else 0.0
    directional_conflict = trend.desired in {"long", "short"} and mr_active and trend.desired != mean_reversion.desired
    unresolved = trend.desired == "flat" and mean_reversion.desired == "flat"
    insufficient = not bool(trend_features["trend_ready"]) or trend.note.startswith("insufficient") or mean_reversion.note.startswith(
        "insufficient"
    )
    range_baseline = 0.55 if unresolved and trend_strength < 0.35 else 0.2

    scores = {
        MarketRegime.TREND_UP: (trend_strength * max(trend.confidence, 0.25)) if trend.desired == "long" else 0.0,
        MarketRegime.TREND_DOWN: (trend_strength * max(trend.confidence, 0.25)) if trend.desired == "short" else 0.0,
        MarketRegime.RANGE: (1.0 - trend_strength) * max(mr_strength, range_baseline),
        MarketRegime.TRANSITION: 0.0,
    }
    scores[MarketRegime.TRANSITION] = max(
        0.02,
        1.0 - max(scores[MarketRegime.TREND_UP], scores[MarketRegime.TREND_DOWN], scores[MarketRegime.RANGE]),
        0.8 if insufficient else 0.0,
        0.7 if directional_conflict else 0.0,
        0.4 if unresolved else 0.0,
    )

    probabilities = _normalize_scores(scores)
    label = max(scores, key=scores.get)
    confidence = probabilities[label.value]
    uncertainty_score = round(1.0 - confidence, 6)
    stand_down = label is MarketRegime.TRANSITION or uncertainty_score >= 0.45

    features = {
        **trend_features,
        "trend_desired": trend.desired,
        "trend_confidence": round(trend.confidence, 6),
        "mean_reversion_desired": mean_reversion.desired,
        "mean_reversion_confidence": round(mean_reversion.confidence, 6),
        "conflict_score": round(
            max(
                0.0,
                1.0 if insufficient else 0.0,
                0.8 if directional_conflict else 0.0,
                0.4 if unresolved else 0.0,
                1.0 - max(scores[MarketRegime.TREND_UP], scores[MarketRegime.TREND_DOWN], scores[MarketRegime.RANGE]),
            ),
            6,
        ),
    }
    if not features["trend_ready"]:
        note = f"{note}; transition by classifier"

    return RegimeClassifierOutput(
        schema_version=REGIME_CLASSIFIER_SCHEMA_VERSION,
        label=label,
        confidence=round(confidence, 6),
        probabilities=probabilities,
        stand_down=stand_down,
        uncertainty_score=uncertainty_score,
        note=note,
        features=features,
    )


def analyze_signal(candles: list[dict], cfg: StrategyConfig | None = None) -> SignalAnalysis:
    cfg = cfg or StrategyConfig()
    closes = [float(c["c"]) for c in candles if "c" in c]

    if not closes:
        empty = Signal(desired="flat", confidence=0.0, strategy="combo", note="no candles")
        regime = classify_regime(candles, cfg)
        return SignalAnalysis(
            signal=empty,
            trend_signal=Signal(desired="flat", confidence=0.0, strategy="trend", note="no candles"),
            mean_reversion_signal=Signal(
                desired="flat",
                confidence=0.0,
                strategy="mean_reversion",
                note="no candles",
            ),
            regime=regime,
            setup_label="no_trade",
        )

    t = trend_signal(closes, cfg)
    m = mean_reversion_signal(closes, cfg)
    regime = classify_regime(candles, cfg)

    regime_on = regime.label in {MarketRegime.TREND_UP, MarketRegime.TREND_DOWN}
    tw = cfg.trend_weight_in_regime if regime_on else cfg.trend_weight
    mw = cfg.mr_weight

    long_score = 0.0
    short_score = 0.0
    setup_label = "no_trade"

    if t.desired == "long":
        long_score += t.confidence * tw
    elif t.desired == "short":
        short_score += t.confidence * tw

    if m.desired == "long":
        long_score += m.confidence * mw
    elif m.desired == "short":
        short_score += m.confidence * mw

    if long_score <= 0 and short_score <= 0:
        signal = Signal(desired="flat", confidence=0.35, strategy="combo", note=f"both flat | {regime.note}")
        return SignalAnalysis(
            signal=signal,
            trend_signal=t,
            mean_reversion_signal=m,
            regime=regime,
            setup_label=setup_label,
        )

    if long_score > short_score + 0.05:
        conf = min(1.0, long_score / (tw + mw))
        if regime_on and cfg.regime_confidence_floor > 0:
            conf = max(conf, cfg.regime_confidence_floor)
        if t.desired == "long" and m.desired == "long":
            setup_label = "trend_plus_mean_reversion_long"
        elif t.desired == "long":
            setup_label = "trend_follow_long"
        elif m.desired == "long":
            setup_label = "mean_reversion_long"
        signal = Signal(desired="long", confidence=conf, strategy="combo", note=f"weighted long ({regime.note})")
        return SignalAnalysis(
            signal=signal,
            trend_signal=t,
            mean_reversion_signal=m,
            regime=regime,
            setup_label=setup_label,
        )

    if short_score > long_score + 0.05:
        conf = min(1.0, short_score / (tw + mw))
        if regime_on and cfg.regime_confidence_floor > 0:
            conf = max(conf, cfg.regime_confidence_floor)
        if t.desired == "short" and m.desired == "short":
            setup_label = "trend_plus_mean_reversion_short"
        elif t.desired == "short":
            setup_label = "trend_follow_short"
        elif m.desired == "short":
            setup_label = "mean_reversion_short"
        signal = Signal(desired="short", confidence=conf, strategy="combo", note=f"weighted short ({regime.note})")
        return SignalAnalysis(
            signal=signal,
            trend_signal=t,
            mean_reversion_signal=m,
            regime=regime,
            setup_label=setup_label,
        )

    # tie/noisy area
    if regime_on and cfg.tie_break_to_trend and t.desired in {"long", "short"} and t.confidence >= cfg.tie_break_min_confidence:
        conf = max(t.confidence, cfg.regime_confidence_floor)
        signal = Signal(
            desired=t.desired,
            confidence=min(1.0, conf),
            strategy="combo",
            note=f"regime tie-break via trend ({regime.note})",
        )
        return SignalAnalysis(
            signal=signal,
            trend_signal=t,
            mean_reversion_signal=m,
            regime=regime,
            setup_label="regime_tie_break",
        )

    signal = Signal(desired="flat", confidence=0.4, strategy="combo", note=f"tie/noise ({regime.note})")
    return SignalAnalysis(
        signal=signal,
        trend_signal=t,
        mean_reversion_signal=m,
        regime=regime,
        setup_label=setup_label,
    )


def choose_signal(candles: list[dict], cfg: StrategyConfig | None = None) -> Signal:
    return analyze_signal(candles, cfg).signal
