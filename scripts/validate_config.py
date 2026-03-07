#!/usr/bin/env python3
"""Validate config.example.json sanity constraints."""

from __future__ import annotations

import json
from pathlib import Path

CFG = Path("config.example.json")


def fail(msg: str) -> None:
    raise SystemExit(f"❌ {msg}")


def expect(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)


def main() -> None:
    expect(CFG.exists(), "config.example.json is missing")
    data = json.loads(CFG.read_text())

    expect(data.get("pair") == "ETH/USD", "pair must be ETH/USD for baseline")
    tf = data.get("tf_min")
    expect(isinstance(tf, int) and tf > 0, "tf_min must be a positive integer")

    risk = data.get("risk", {})
    rp = risk.get("risk_pct")
    expect(isinstance(rp, (int, float)) and 0 < rp <= 0.05, "risk_pct must be in (0, 0.05]")

    min_risk = risk.get("min_risk_usd")
    max_risk = risk.get("max_risk_usd")
    expect(isinstance(min_risk, (int, float)) and min_risk >= 0, "min_risk_usd must be >= 0")
    expect(isinstance(max_risk, (int, float)) and max_risk >= min_risk, "max_risk_usd must be >= min_risk_usd")

    lev = risk.get("max_leverage")
    expect(isinstance(lev, (int, float)) and 0 < lev <= 2.0, "max_leverage must be <= 2.0")

    deployed = risk.get("max_deployed_pct")
    expect(isinstance(deployed, (int, float)) and 0 < deployed <= 0.50, "max_deployed_pct must be <= 0.50")

    kill = risk.get("daily_kill_switch_pct")
    expect(isinstance(kill, (int, float)) and kill < 0 and kill >= -0.20, "daily_kill_switch_pct must be negative and >= -0.20")

    mc = risk.get("min_collateral_usd")
    expect(isinstance(mc, (int, float)) and mc >= 20.0, "min_collateral_usd must be >= 20")

    ai = data.get("ai", {})
    hard = ai.get("hard_limits", {})
    ai_lev = hard.get("max_leverage")
    expect(isinstance(ai_lev, (int, float)) and ai_lev <= lev, "ai.hard_limits.max_leverage must be <= risk.max_leverage")

    print("✅ config.example.json validation passed")


if __name__ == "__main__":
    main()
