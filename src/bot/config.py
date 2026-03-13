from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_STRATEGY_ID = "conservative"


@dataclass
class RiskConfig:
    # Baseline risk target (still clamped by min/max below)
    risk_pct: float = 0.01

    # Risk clamps (USD)
    min_risk_usd: float = 10.0
    max_risk_usd: float = 50.0

    # Optional risk clamps as % of equity (bootstrap mode)
    # If set, effective clamp becomes:
    #   min = max(min_risk_usd, equity * min_risk_pct)
    #   max = min(max_risk_usd, equity * max_risk_pct)
    min_risk_pct: float | None = None
    max_risk_pct: float | None = None

    # Leverage caps
    max_leverage: float = 2.0

    # Execution / exposure caps
    max_deployed_pct: float = 0.75
    daily_kill_switch_pct: float = -0.10
    min_collateral_usd: float = 20.0

    # Confidence gate for opening/scaling positions.
    min_confidence_to_trade: float = 0.60


@dataclass
class StrategyProfileConfig:
    risk_pct: float | None = None
    max_deployed_pct: float | None = None
    max_leverage: float | None = None
    min_confidence_to_trade: float | None = None

    trend_weight_in_regime: float | None = None
    adx_threshold: float | None = None
    tie_break_to_trend: bool = False
    tie_break_min_confidence: float = 0.0
    regime_confidence_floor: float = 0.0


@dataclass
class StrategyConfig:
    default_id: str = DEFAULT_STRATEGY_ID
    allowed_ids: list[str] = field(default_factory=lambda: [DEFAULT_STRATEGY_ID])
    profiles: dict[str, StrategyProfileConfig] = field(default_factory=dict)


@dataclass
class BotConfig:
    pair: str = "ETH/USD"
    tf_min: int = 15
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)


def load_config() -> BotConfig:
    """Load config from JSON file path in APB_CONFIG or defaults.

    Keep it dependency-free (no yaml) for now.
    """

    cfg = BotConfig()

    p = os.environ.get("APB_CONFIG")
    if not p:
        return cfg

    path = Path(p).expanduser()
    data = json.loads(path.read_text(encoding="utf-8"))

    cfg.pair = data.get("pair", cfg.pair)
    cfg.tf_min = int(data.get("tf_min", cfg.tf_min))

    r = data.get("risk", {}) or {}
    cfg.risk = RiskConfig(
        risk_pct=float(r.get("risk_pct", cfg.risk.risk_pct)),
        min_risk_usd=float(r.get("min_risk_usd", cfg.risk.min_risk_usd)),
        max_risk_usd=float(r.get("max_risk_usd", cfg.risk.max_risk_usd)),
        min_risk_pct=(None if r.get("min_risk_pct") is None else float(r.get("min_risk_pct"))),
        max_risk_pct=(None if r.get("max_risk_pct") is None else float(r.get("max_risk_pct"))),
        max_leverage=float(r.get("max_leverage", cfg.risk.max_leverage)),
        max_deployed_pct=float(r.get("max_deployed_pct", cfg.risk.max_deployed_pct)),
        daily_kill_switch_pct=float(r.get("daily_kill_switch_pct", cfg.risk.daily_kill_switch_pct)),
        min_collateral_usd=float(r.get("min_collateral_usd", cfg.risk.min_collateral_usd)),
        min_confidence_to_trade=float(r.get("min_confidence_to_trade", cfg.risk.min_confidence_to_trade)),
    )

    s = data.get("strategy", {}) or {}
    allowed = s.get("allowed_ids", [cfg.strategy.default_id])
    if not isinstance(allowed, list) or not allowed:
        allowed = [cfg.strategy.default_id]
    allowed_ids = [str(x).strip() for x in allowed if str(x).strip()]
    if DEFAULT_STRATEGY_ID not in allowed_ids:
        allowed_ids.insert(0, DEFAULT_STRATEGY_ID)

    default_id = str(s.get("default_id", cfg.strategy.default_id)).strip() or DEFAULT_STRATEGY_ID
    if default_id not in allowed_ids:
        allowed_ids.insert(0, default_id)

    profiles_raw = s.get("profiles", {}) or {}
    profiles: dict[str, StrategyProfileConfig] = {}
    for sid in allowed_ids:
        raw = profiles_raw.get(sid, {}) or {}
        profiles[sid] = StrategyProfileConfig(
            risk_pct=(None if raw.get("risk_pct") is None else float(raw.get("risk_pct"))),
            max_deployed_pct=(None if raw.get("max_deployed_pct") is None else float(raw.get("max_deployed_pct"))),
            max_leverage=(None if raw.get("max_leverage") is None else float(raw.get("max_leverage"))),
            min_confidence_to_trade=(None if raw.get("min_confidence_to_trade") is None else float(raw.get("min_confidence_to_trade"))),
            trend_weight_in_regime=(None if raw.get("trend_weight_in_regime") is None else float(raw.get("trend_weight_in_regime"))),
            adx_threshold=(None if raw.get("adx_threshold") is None else float(raw.get("adx_threshold"))),
            tie_break_to_trend=bool(raw.get("tie_break_to_trend", False)),
            tie_break_min_confidence=float(raw.get("tie_break_min_confidence", 0.0)),
            regime_confidence_floor=float(raw.get("regime_confidence_floor", 0.0)),
        )

    cfg.strategy = StrategyConfig(default_id=default_id, allowed_ids=allowed_ids, profiles=profiles)

    return cfg


def as_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: as_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [as_dict(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return {k: as_dict(v) for k, v in obj.__dict__.items()}
    return obj
