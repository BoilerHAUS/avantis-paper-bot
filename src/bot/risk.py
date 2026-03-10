"""Risk manager (v0.1)

Right now we only implement the *risk budget math* needed to avoid the
"$100 equity → $1 risk" silliness.

v1 will convert Signal -> OrderPlan + sizing based on stop distance.

Constraints (intended):
- per-trade risk = 1% equity (default)
- BUT with a floor/ceiling in USD for small accounts
- max leverage = 2x (starter)
- max deployed = 75% equity
- daily kill switch at -10% equity
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import RiskConfig
from .indicators import atr
from .models import OrderPlan, Signal


@dataclass
class RiskBudget:
    equity_usd: float
    risk_usd: float
    risk_pct_effective: float
    min_collateral_usd: float


def compute_risk_budget(equity_usd: float, cfg: RiskConfig) -> RiskBudget:
    if equity_usd <= 0:
        return RiskBudget(
            equity_usd=equity_usd,
            risk_usd=0.0,
            risk_pct_effective=0.0,
            min_collateral_usd=cfg.min_collateral_usd,
        )

    raw = equity_usd * cfg.risk_pct

    # Clamp by USD bounds first
    min_usd = cfg.min_risk_usd
    max_usd = cfg.max_risk_usd

    # Optional % of equity clamps (bootstrap mode)
    if cfg.min_risk_pct is not None:
        min_usd = max(min_usd, equity_usd * cfg.min_risk_pct)
    if cfg.max_risk_pct is not None:
        max_usd = min(max_usd, equity_usd * cfg.max_risk_pct)

    # Safety: ensure max >= min
    max_usd = max(max_usd, min_usd)

    risk_usd = max(min_usd, min(max_usd, raw))
    risk_pct_effective = risk_usd / equity_usd

    return RiskBudget(
        equity_usd=equity_usd,
        risk_usd=risk_usd,
        risk_pct_effective=risk_pct_effective,
        min_collateral_usd=cfg.min_collateral_usd,
    )


def plan_from_signal(
    *,
    signal: Signal,
    candles: list[dict],
    last_price: float,
    rb: RiskBudget,
    cfg: RiskConfig,
) -> OrderPlan:
    """Convert a Signal into a bounded OrderPlan.

    v0.1:
    - ATR stop distance
    - size so max loss at stop ~= risk_usd
    - enforce max leverage + max deployed + min collateral
    """

    if signal.desired == "flat":
        return OrderPlan(
            action="hold",
            side=None,
            target_notional_usd=0.0,
            collateral_usd=0.0,
            leverage=0.0,
            stop_loss=None,
            take_profit=None,
            risk_usd=0.0,
            note=f"flat: {signal.strategy} ({signal.note})",
        )

    side = "long" if signal.desired == "long" else "short"

    # ATR on candle dicts
    highs = [float(c["h"]) for c in candles if "h" in c]
    lows = [float(c["l"]) for c in candles if "l" in c]
    closes = [float(c["c"]) for c in candles if "c" in c]

    a = atr(highs, lows, closes, n=14) if len(closes) >= 20 else None
    if a is None:
        # fallback: 0.75% stop
        stop_dist = last_price * 0.0075
        note_atr = "atr=na fallback_stop=0.75%"
    else:
        stop_dist = a * 2.0  # ATR multiplier (tune later)
        note_atr = f"atr14={a:.2f} stop_dist={stop_dist:.2f}"

    # stop price
    # v1 management: partial TP at 1.5R, remaining half trails by ~2 ATR
    if side == "long":
        stop = last_price - stop_dist
        tp = last_price + stop_dist * 1.5
    else:
        stop = last_price + stop_dist
        tp = last_price - stop_dist * 1.5

    # position notional such that loss at stop ~= risk_usd
    stop_pct = abs((last_price - stop) / last_price)
    if stop_pct <= 0:
        return OrderPlan(
            action="hold",
            side=None,
            target_notional_usd=0.0,
            collateral_usd=0.0,
            leverage=0.0,
            stop_loss=None,
            take_profit=None,
            risk_usd=0.0,
            note="invalid stop_pct",
        )

    raw_notional = rb.risk_usd / stop_pct

    # cap by max deployed
    max_notional = cfg.max_deployed_pct * rb.equity_usd
    target_notional = min(raw_notional, max_notional)

    # pick leverage up to cap; set collateral accordingly
    # Tier leverage by confidence (bootstrap): 5x should be rare.
    conf = float(getattr(signal, "confidence", 0.0) or 0.0)

    def _tiered_max(confidence: float) -> float:
        if confidence < cfg.min_confidence_to_trade:
            return 0.0
        if confidence < 0.74:
            return 2.0
        if confidence < 0.84:
            return 3.0
        if confidence < 0.92:
            return 4.0
        return 5.0

    tier_cap = _tiered_max(conf)

    # Strategy-specific caps
    strat = str(getattr(signal, "strategy", ""))
    if "mean_reversion" in strat:
        tier_cap = min(tier_cap, 3.0)

    max_lev_allowed = min(cfg.max_leverage, tier_cap if tier_cap > 0 else cfg.max_leverage)

    leverage = min(max_lev_allowed, max(1.0, target_notional / cfg.min_collateral_usd))
    # If tiering says "skip", force a hold.
    if max_lev_allowed <= 0:
        return OrderPlan(
            action="hold",
            side=None,
            target_notional_usd=0.0,
            collateral_usd=0.0,
            leverage=0.0,
            stop_loss=None,
            take_profit=None,
            risk_usd=0.0,
            note=f"skip: conf={conf:.2f} below threshold={cfg.min_confidence_to_trade:.2f} ({signal.strategy})",
        )

    collateral = max(cfg.min_collateral_usd, target_notional / leverage)
    leverage = target_notional / collateral if collateral > 0 else 0.0

    return OrderPlan(
        action="open",
        side=side,
        target_notional_usd=float(target_notional),
        collateral_usd=float(collateral),
        leverage=float(leverage),
        stop_loss=float(stop),
        take_profit=float(tp),
        risk_usd=float(rb.risk_usd),
        note=f"{signal.strategy} conf={signal.confidence:.2f} {note_atr} tp=1.5R trail=2ATR",
    )
