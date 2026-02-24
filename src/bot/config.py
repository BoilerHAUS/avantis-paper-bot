from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RiskConfig:
    risk_pct: float = 0.01
    min_risk_usd: float = 5.0
    max_risk_usd: float = 50.0
    max_leverage: float = 2.0
    max_deployed_pct: float = 0.75
    daily_kill_switch_pct: float = -0.10
    min_collateral_usd: float = 10.0


@dataclass
class BotConfig:
    pair: str = "ETH/USD"
    tf_min: int = 15
    risk: RiskConfig = field(default_factory=RiskConfig)


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
        max_leverage=float(r.get("max_leverage", cfg.risk.max_leverage)),
        max_deployed_pct=float(r.get("max_deployed_pct", cfg.risk.max_deployed_pct)),
        daily_kill_switch_pct=float(r.get("daily_kill_switch_pct", cfg.risk.daily_kill_switch_pct)),
        min_collateral_usd=float(r.get("min_collateral_usd", cfg.risk.min_collateral_usd)),
    )

    return cfg


def as_dict(obj: Any) -> Any:
    if hasattr(obj, "__dict__"):
        return {k: as_dict(v) for k, v in obj.__dict__.items()}
    return obj
