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
    risk_usd = max(cfg.min_risk_usd, min(cfg.max_risk_usd, raw))
    risk_pct_effective = risk_usd / equity_usd

    return RiskBudget(
        equity_usd=equity_usd,
        risk_usd=risk_usd,
        risk_pct_effective=risk_pct_effective,
        min_collateral_usd=cfg.min_collateral_usd,
    )
