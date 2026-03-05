"""Deterministic strategies (v0.2).

Adds a weighted blend with trend-day regime detection:
- Trend signal (fast/slow SMA + slope)
- Mean-reversion signal (z-score)
- Regime gate combines MA-structure + ADX strength
"""

from __future__ import annotations

from dataclasses import dataclass

from .indicators import adx, sma, zscore
from .models import Signal


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


def _trend_regime(closes: list[float], highs: list[float], lows: list[float], cfg: StrategyConfig) -> tuple[bool, str]:
    f = sma(closes, cfg.trend_fast)
    s = sma(closes, cfg.trend_slow)
    if f is None or s is None or s == 0:
        return False, "insufficient ma"

    if len(closes) < cfg.trend_fast + 3:
        slope = 0.0
    else:
        f_prev = sma(closes[:-3], cfg.trend_fast) or f
        slope = (f - f_prev) / f_prev if f_prev else 0.0

    spread = abs((f - s) / s)
    a = adx(highs, lows, closes, n=cfg.adx_n)
    if a is None:
        return False, "insufficient adx"

    ok = a >= cfg.adx_threshold and spread >= cfg.min_spread_ratio and abs(slope) >= cfg.min_slope_ratio
    return ok, f"adx={a:.1f} spread={spread:.4f} slope={slope:.4f}"


def choose_signal(candles: list[dict], cfg: StrategyConfig | None = None) -> Signal:
    cfg = cfg or StrategyConfig()
    closes = [float(c["c"]) for c in candles if "c" in c]
    highs = [float(c["h"]) for c in candles if "h" in c]
    lows = [float(c["l"]) for c in candles if "l" in c]

    if not closes:
        return Signal(desired="flat", confidence=0.0, strategy="combo", note="no candles")

    t = trend_signal(closes, cfg)
    m = mean_reversion_signal(closes, cfg)
    regime_on, regime_note = _trend_regime(closes, highs, lows, cfg)

    tw = cfg.trend_weight_in_regime if regime_on else cfg.trend_weight
    mw = cfg.mr_weight

    long_score = 0.0
    short_score = 0.0

    if t.desired == "long":
        long_score += t.confidence * tw
    elif t.desired == "short":
        short_score += t.confidence * tw

    if m.desired == "long":
        long_score += m.confidence * mw
    elif m.desired == "short":
        short_score += m.confidence * mw

    if long_score <= 0 and short_score <= 0:
        return Signal(desired="flat", confidence=0.35, strategy="combo", note=f"both flat | {regime_note}")

    if long_score > short_score + 0.05:
        conf = min(1.0, long_score / (tw + mw))
        return Signal(desired="long", confidence=conf, strategy="combo", note=f"weighted long ({regime_note})")

    if short_score > long_score + 0.05:
        conf = min(1.0, short_score / (tw + mw))
        return Signal(desired="short", confidence=conf, strategy="combo", note=f"weighted short ({regime_note})")

    # tie/noisy area
    return Signal(desired="flat", confidence=0.4, strategy="combo", note=f"tie/noise ({regime_note})")
