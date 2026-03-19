from __future__ import annotations

from bot.strategies import StrategyConfig, analyze_signal, apply_position_management
from bot.models import OrderPlan


def _candles_from_closes(closes: list[float], *, tf_sec: int = 900) -> list[dict]:
    return [
        {
            "start_ts": 1_700_200_000 + idx * tf_sec,
            "tf_sec": tf_sec,
            "o": close - 0.4,
            "h": close + 0.8,
            "l": close - 0.8,
            "c": close,
        }
        for idx, close in enumerate(closes)
    ]


def _plan(side: str | None = "long") -> OrderPlan:
    return OrderPlan(
        action="open",
        side=side,
        target_notional_usd=50.0,
        collateral_usd=25.0,
        leverage=2.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_usd=10.0,
        note="trend lane",
    )


def test_trend_lane_opens_breakout_long_in_confirmed_uptrend() -> None:
    closes = [100.0 + i * 1.0 for i in range(75)] + [174.2, 175.3, 176.5, 177.8, 179.4]

    analysis = analyze_signal(_candles_from_closes(closes))

    assert analysis.strategy_lane == "trend_continuation"
    assert analysis.regime_label == "trend_up"
    assert analysis.signal.desired == "long"
    assert analysis.setup_label == "breakout_long"
    assert analysis.invalidation_reason is None


def test_trend_lane_opens_breakdown_short_in_confirmed_downtrend() -> None:
    closes = [200.0 - i * 1.0 for i in range(75)] + [125.8, 124.9, 123.7, 122.5, 121.0]

    analysis = analyze_signal(_candles_from_closes(closes))

    assert analysis.strategy_lane == "trend_continuation"
    assert analysis.regime_label == "trend_down"
    assert analysis.signal.desired == "short"
    assert analysis.setup_label == "breakdown_short"
    assert analysis.invalidation_reason is None


def test_trend_lane_stands_down_in_chop() -> None:
    closes = [100.0 + ((i % 4) - 1.5) * 0.55 for i in range(80)]

    analysis = analyze_signal(_candles_from_closes(closes))

    assert analysis.signal.desired == "flat"
    assert analysis.setup_label == "no_trade"
    assert analysis.strategy_lane == "stand_down"
    assert analysis.invalidation_reason in {"transition_stand_down", "regime_not_confirmed", "confidence_collapse"}


def test_trend_lane_never_takes_countertrend_signal_in_confirmed_uptrend() -> None:
    cfg = StrategyConfig(mr_window=10, mr_entry_z=1.0)
    closes = [100.0 + i * 0.9 for i in range(75)] + [168.0, 170.0, 172.0, 176.0, 181.0]

    analysis = analyze_signal(_candles_from_closes(closes), cfg)

    assert analysis.regime_label == "trend_up"
    assert analysis.signal.desired != "short"
    assert analysis.setup_label in {"breakout_long", "no_trade"}


def test_trend_lane_never_takes_countertrend_signal_in_confirmed_downtrend() -> None:
    cfg = StrategyConfig(mr_window=10, mr_entry_z=1.0)
    closes = [200.0 - i * 0.9 for i in range(75)] + [132.0, 130.0, 128.0, 124.0, 119.0]

    analysis = analyze_signal(_candles_from_closes(closes), cfg)

    assert analysis.regime_label == "trend_down"
    assert analysis.signal.desired != "long"
    assert analysis.setup_label in {"breakdown_short", "no_trade"}


def test_position_management_holds_without_fresh_setup_but_closes_on_invalidation() -> None:
    hold_analysis = analyze_signal(_candles_from_closes([100.0 + i * 1.0 for i in range(80)]))
    hold_analysis.signal.desired = "flat"
    hold_analysis.setup_label = "no_trade"
    hold_analysis.invalidation_reason = None

    hold_plan = apply_position_management(_plan("long"), hold_analysis, "long")

    assert hold_plan.action == "hold"
    assert hold_plan.side == "long"

    close_analysis = analyze_signal(_candles_from_closes([100.0 + ((i % 4) - 1.5) * 0.55 for i in range(80)]))
    close_plan = apply_position_management(_plan("long"), close_analysis, "long")

    assert close_plan.action == "close"
    assert close_plan.side == "long"
    assert "stand_down" in close_plan.note or "confirmed" in close_plan.note
