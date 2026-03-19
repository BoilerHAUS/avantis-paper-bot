from __future__ import annotations

import hashlib
from typing import Any

from .config import as_dict

ARTIFACT_CONTRACT_VERSION = "decision_artifact.v1"

_FORCED_EXIT_KINDS = {
    "stop_loss": "stop_loss",
}


def strategy_fingerprint(strategy_id: str, effective_risk: Any, signal_cfg: Any) -> str:
    payload = {
        "strategy_id": strategy_id,
        "risk": as_dict(effective_risk),
        "signal": as_dict(signal_cfg),
    }
    digest = hashlib.sha256(
        _stable_fingerprint_payload(payload).encode("utf-8")
    ).hexdigest()
    return digest[:12]


def build_provenance(
    *,
    strategy_id: str,
    strategy_fingerprint: str,
    pair: str,
    tf_min: int,
) -> dict[str, Any]:
    return {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "strategy_id": strategy_id,
        "strategy_fingerprint": strategy_fingerprint,
        "pair": pair,
        "symbol": pair,
        "timeframe_min": tf_min,
    }


def build_effective_config(*, effective_risk: Any, signal_cfg: Any) -> dict[str, Any]:
    risk = as_dict(effective_risk)
    signal = as_dict(signal_cfg)
    return {
        "risk": {
            "risk_pct": risk.get("risk_pct"),
            "min_risk_usd": risk.get("min_risk_usd"),
            "max_risk_usd": risk.get("max_risk_usd"),
            "max_deployed_pct": risk.get("max_deployed_pct"),
            "max_leverage": risk.get("max_leverage"),
            "min_confidence_to_trade": risk.get("min_confidence_to_trade"),
            "daily_kill_switch_pct": risk.get("daily_kill_switch_pct"),
        },
        "signal": {
            "trend_weight": signal.get("trend_weight"),
            "trend_weight_in_regime": signal.get("trend_weight_in_regime"),
            "mr_weight": signal.get("mr_weight"),
            "adx_threshold": signal.get("adx_threshold"),
            "regime_confidence_floor": signal.get("regime_confidence_floor"),
            "tie_break_to_trend": signal.get("tie_break_to_trend"),
            "tie_break_min_confidence": signal.get("tie_break_min_confidence"),
            "trend_lane_min_confidence": signal.get("trend_lane_min_confidence"),
            "continuation_lookback": signal.get("continuation_lookback"),
        },
    }


def build_decision_artifact(
    *,
    analysis: Any | None,
    plan: Any | None,
    previous_position: Any | None,
    execution_events: list[dict[str, Any]] | None = None,
    market_data_ready: bool = True,
) -> dict[str, Any]:
    execution_events = execution_events or []
    regime = "unknown"
    regime_note = None
    setup_type = "no_trade"
    strategy_lane = "unknown"
    signal_desired = "flat"
    signal_note = None
    invalidation_reason = None
    plan_action = None
    plan_note = None

    if analysis is not None:
        regime = analysis.regime_label
        regime_note = analysis.regime_note
        setup_type = analysis.setup_label
        strategy_lane = analysis.strategy_lane
        signal_desired = analysis.signal.desired
        signal_note = analysis.signal.note
        invalidation_reason = analysis.invalidation_reason

    if plan is not None:
        plan_action = plan.action
        plan_note = plan.note

    decision_status = "skip"
    decision_reason = None
    block_reason = None
    exit_reason = None

    forced_exit_reason = _forced_exit_reason(execution_events)
    if not market_data_ready or analysis is None or plan is None:
        block_reason = "no_market_data"
    elif forced_exit_reason is not None and plan.action == "hold":
        decision_status = "forced_exit"
        exit_reason = forced_exit_reason
    elif plan.action == "open":
        decision_status = "open"
        decision_reason = "entry_signal"
    elif plan.action == "scale":
        decision_status = "scale"
        decision_reason = "add_signal"
    elif plan.action == "flip":
        decision_status = "flip"
        decision_reason = "reverse_signal"
        exit_reason = "reverse_signal"
    elif plan.action == "close":
        decision_status = "close"
        exit_reason = invalidation_reason or _close_exit_reason(signal_desired)
    elif previous_position is not None:
        decision_status = "hold"
        decision_reason = "existing_position"
    elif signal_desired == "flat":
        block_reason = invalidation_reason or _skip_reason(setup_type, signal_note)
    elif setup_type == "no_trade":
        block_reason = "no_setup"
    else:
        decision_status = "veto"
        block_reason = _veto_reason(plan_note)

    primary_reason = decision_reason or block_reason or exit_reason
    return {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "regime": regime,
        "setup_type": setup_type,
        "strategy_lane": strategy_lane,
        "decision_status": decision_status,
        "decision_reason": decision_reason,
        "block_reason": block_reason,
        "exit_reason": exit_reason,
        "invalidation_reason": invalidation_reason,
        "signal_desired": signal_desired,
        "plan_action": plan_action,
        "status": decision_status,
        "reason": primary_reason,
        "regime_note": regime_note,
        "signal_note": signal_note,
        "plan_note": plan_note,
    }


def _stable_fingerprint_payload(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _skip_reason(setup_type: str, signal_note: str | None) -> str:
    if setup_type == "no_trade":
        return "signal_flat"
    if signal_note and "tie/noise" in signal_note:
        return "no_setup"
    return "signal_flat"


def _veto_reason(plan_note: str | None) -> str:
    note = (plan_note or "").lower()
    if note.startswith("skip: conf="):
        return "confidence_below_min"
    if "invalid stop_pct" in note:
        return "invalid_stop"
    return "risk_gate"


def _close_exit_reason(signal_desired: str) -> str:
    if signal_desired == "flat":
        return "signal_flat"
    return "position_exit"


def _forced_exit_reason(execution_events: list[dict[str, Any]]) -> str | None:
    for event in execution_events:
        kind = str(event.get("kind", ""))
        if kind in _FORCED_EXIT_KINDS:
            return _FORCED_EXIT_KINDS[kind]
    return None
