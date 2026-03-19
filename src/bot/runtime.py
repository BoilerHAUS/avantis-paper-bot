from __future__ import annotations

from dataclasses import replace

from .config import DEFAULT_STRATEGY_ID
from .models import PaperState, Position
from .strategies import StrategyConfig as SignalStrategyConfig


def effective_risk_cfg(cfg, strategy_id: str):
    p = cfg.strategy.profiles.get(strategy_id)
    if p is None:
        return cfg.risk

    return replace(
        cfg.risk,
        risk_pct=(cfg.risk.risk_pct if p.risk_pct is None else p.risk_pct),
        max_deployed_pct=(cfg.risk.max_deployed_pct if p.max_deployed_pct is None else p.max_deployed_pct),
        max_leverage=(cfg.risk.max_leverage if p.max_leverage is None else p.max_leverage),
        min_confidence_to_trade=(
            cfg.risk.min_confidence_to_trade
            if p.min_confidence_to_trade is None
            else p.min_confidence_to_trade
        ),
    )


def effective_signal_cfg(cfg, strategy_id: str) -> SignalStrategyConfig:
    p = cfg.strategy.profiles.get(strategy_id)
    scfg = SignalStrategyConfig()
    if p is None:
        return scfg

    if p.trend_weight_in_regime is not None:
        scfg.trend_weight_in_regime = p.trend_weight_in_regime
    if p.adx_threshold is not None:
        scfg.adx_threshold = p.adx_threshold
    scfg.tie_break_to_trend = p.tie_break_to_trend
    scfg.tie_break_min_confidence = p.tie_break_min_confidence
    scfg.regime_confidence_floor = p.regime_confidence_floor
    return scfg


def paper_state_from_raw(raw_state: dict) -> PaperState:
    pos_raw = raw_state.get("position")
    pos = None
    if isinstance(pos_raw, dict):
        pos = Position(
            side=pos_raw.get("side"),
            notional_usd=float(pos_raw.get("notional_usd", 0.0)),
            collateral_usd=float(pos_raw.get("collateral_usd", 0.0)),
            leverage=float(pos_raw.get("leverage", 0.0)),
            entry_price=float(pos_raw.get("entry_price", 0.0)),
            avg_price=float(pos_raw.get("avg_price", pos_raw.get("entry_price", 0.0))),
            stop_loss=pos_raw.get("stop_loss"),
            take_profit=pos_raw.get("take_profit"),
            opened_ts=int(pos_raw.get("opened_ts", 0)),
            initial_notional_usd=(
                None
                if pos_raw.get("initial_notional_usd") is None
                else float(pos_raw.get("initial_notional_usd"))
            ),
            partial_taken=bool(pos_raw.get("partial_taken", False)),
            trail_distance=(
                None if pos_raw.get("trail_distance") is None else float(pos_raw.get("trail_distance"))
            ),
        )

    return PaperState(
        equity=float(raw_state.get("equity", 0.0)),
        daily_pnl=float(raw_state.get("daily_pnl", 0.0)),
        position=pos,
        last_price=raw_state.get("last_price"),
    )


def default_paper_state(strategy_id: str = DEFAULT_STRATEGY_ID) -> dict:
    return {
        "strategy_id": strategy_id,
        "equity": 100.0,
        "position": None,
        "daily_pnl": 0.0,
        "last_price": None,
    }
