from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

Side = Literal["long", "short"]
Desired = Literal["long", "short", "flat"]


class MarketRegime(str, Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    TRANSITION = "transition"


@dataclass
class Signal:
    desired: Desired
    confidence: float
    strategy: str
    note: str = ""


@dataclass
class RegimeClassifierOutput:
    schema_version: str
    label: MarketRegime
    confidence: float
    probabilities: dict[str, float]
    stand_down: bool
    uncertainty_score: float
    note: str
    features: dict[str, float | str | bool | None]


@dataclass
class OrderPlan:
    action: Literal["open", "close", "hold", "flip", "scale"]
    side: Optional[Side]  # none for hold
    target_notional_usd: float
    collateral_usd: float
    leverage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_usd: float
    note: str = ""


@dataclass
class Position:
    side: Side
    notional_usd: float
    collateral_usd: float
    leverage: float
    entry_price: float
    avg_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_ts: int
    # v0.2 trade management
    initial_notional_usd: Optional[float] = None
    partial_taken: bool = False
    trail_distance: Optional[float] = None


@dataclass
class PaperState:
    equity: float
    daily_pnl: float
    position: Optional[Position]
    last_price: Optional[float] = None
