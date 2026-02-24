"""Deterministic strategies (v0.1).

We start with simple, debuggable signals on 15m candles.
The goal is a baseline system the AI layer can *modify within bounds*,
not replace.

Trend (default):
- fast/slow SMA cross + slope proxy

Mean reversion:
- z-score of close vs SMA window

Both return a normalized Signal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .indicators import sma, zscore
from .models import Signal


@dataclass
class StrategyConfig:
    trend_fast: int = 20
    trend_slow: int = 50
    mr_window: int = 50
    mr_entry_z: float = 1.5


def trend_signal(closes: list[float], cfg: StrategyConfig) -> Signal:
    f = sma(closes, cfg.trend_fast)
    s = sma(closes, cfg.trend_slow)
    if f is None or s is None:
        return Signal(desired="flat", confidence=0.0, strategy="trend", note="insufficient candles")

    # crude slope proxy: fast SMA delta over 3 bars
    if len(closes) < cfg.trend_fast + 3:
        slope = 0.0
    else:
        f_prev = sma(closes[:-3], cfg.trend_fast) or f
        slope = (f - f_prev) / f_prev if f_prev else 0.0

    if f > s and slope > 0:
        conf = min(1.0, abs(slope) * 50)
        return Signal(desired="long", confidence=conf, strategy="trend", note=f"fast>slo & slope={slope:.4f}")
    if f < s and slope < 0:
        conf = min(1.0, abs(slope) * 50)
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


def choose_signal(closes: list[float], cfg: StrategyConfig | None = None) -> Signal:
    cfg = cfg or StrategyConfig()
    t = trend_signal(closes, cfg)
    m = mean_reversion_signal(closes, cfg)

    # Simple resolver:
    # - if both agree on direction, take it
    # - else prefer trend when trend confidence >= MR confidence
    if t.desired == m.desired and t.desired != "flat":
        return Signal(desired=t.desired, confidence=max(t.confidence, m.confidence), strategy="combo", note=f"agree: {t.note} | {m.note}")

    if t.confidence >= m.confidence:
        return t
    return m
