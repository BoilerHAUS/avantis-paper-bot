from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from bot.artifacts import ARTIFACT_CONTRACT_VERSION, build_decision_artifact, build_effective_config
from bot.models import OrderPlan, Signal
from bot.run_cycle import main as run_cycle_main
from bot.storage import candles_path, journal_path, snapshot_path, state_path
from bot.strategies import SignalAnalysis
from bot.utils import read_json, stable_json_dumps


def _analysis(
    *,
    desired: str = "long",
    regime: str = "trend_up",
    setup: str = "trend_follow_long",
    note: str = "weighted long",
) -> SignalAnalysis:
    signal = Signal(desired=desired, confidence=0.8, strategy="combo", note=note)
    return SignalAnalysis(
        signal=signal,
        trend_signal=Signal(desired=desired, confidence=0.8, strategy="trend", note="trend"),
        mean_reversion_signal=Signal(desired="flat", confidence=0.4, strategy="mean_reversion", note="neutral"),
        regime_label=regime,
        regime_note="adx=25.0 spread=0.0100 slope=0.0050",
        setup_label=setup,
    )


def _plan(action: str, note: str = "combo conf=0.80") -> OrderPlan:
    return OrderPlan(
        action=action,
        side="long" if action != "close" else None,
        target_notional_usd=50.0,
        collateral_usd=25.0,
        leverage=2.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_usd=10.0,
        note=note,
    )


def test_effective_config_is_compact_and_stable() -> None:
    effective = build_effective_config(
        effective_risk=SimpleNamespace(
            risk_pct=0.01,
            min_risk_usd=10.0,
            max_risk_usd=25.0,
            max_deployed_pct=0.5,
            max_leverage=2.0,
            min_confidence_to_trade=0.6,
            daily_kill_switch_pct=-0.08,
        ),
        signal_cfg=SimpleNamespace(
            trend_weight=1.0,
            trend_weight_in_regime=1.8,
            mr_weight=0.8,
            adx_threshold=16.0,
            regime_confidence_floor=0.28,
            tie_break_to_trend=True,
            tie_break_min_confidence=0.55,
        ),
    )

    assert stable_json_dumps(effective) == """{
  \"risk\": {
    \"daily_kill_switch_pct\": -0.08,
    \"max_deployed_pct\": 0.5,
    \"max_leverage\": 2.0,
    \"max_risk_usd\": 25.0,
    \"min_confidence_to_trade\": 0.6,
    \"min_risk_usd\": 10.0,
    \"risk_pct\": 0.01
  },
  \"signal\": {
    \"adx_threshold\": 16.0,
    \"mr_weight\": 0.8,
    \"regime_confidence_floor\": 0.28,
    \"tie_break_min_confidence\": 0.55,
    \"tie_break_to_trend\": true,
    \"trend_weight\": 1.0,
    \"trend_weight_in_regime\": 1.8
  }
}
"""


def test_decision_contract_serialization_is_stable() -> None:
    cases = {
        "skip": build_decision_artifact(
            analysis=None,
            plan=None,
            previous_position=None,
            market_data_ready=False,
        ),
        "veto": build_decision_artifact(
            analysis=_analysis(),
            plan=_plan("hold", note="skip: conf=0.55 below threshold=0.60 (combo)"),
            previous_position=None,
        ),
        "hold": build_decision_artifact(
            analysis=_analysis(),
            plan=_plan("hold"),
            previous_position={"side": "long"},
        ),
        "close": build_decision_artifact(
            analysis=_analysis(desired="flat", regime="transition", setup="no_trade", note="both flat"),
            plan=_plan("close"),
            previous_position={"side": "long"},
        ),
        "forced_exit": build_decision_artifact(
            analysis=_analysis(),
            plan=_plan("hold"),
            previous_position={"side": "long"},
            execution_events=[{"kind": "stop_loss"}],
        ),
    }

    assert stable_json_dumps(cases) == """{
  "close": {
    "artifact_contract_version": "decision_artifact.v1",
    "block_reason": null,
    "decision_reason": null,
    "decision_status": "close",
    "exit_reason": "signal_flat",
    "plan_action": "close",
    "plan_note": "combo conf=0.80",
    "reason": "signal_flat",
    "regime": "transition",
    "regime_note": "adx=25.0 spread=0.0100 slope=0.0050",
    "setup_type": "no_trade",
    "signal_desired": "flat",
    "signal_note": "both flat",
    "status": "close"
  },
  "forced_exit": {
    "artifact_contract_version": "decision_artifact.v1",
    "block_reason": null,
    "decision_reason": null,
    "decision_status": "forced_exit",
    "exit_reason": "stop_loss",
    "plan_action": "hold",
    "plan_note": "combo conf=0.80",
    "reason": "stop_loss",
    "regime": "trend_up",
    "regime_note": "adx=25.0 spread=0.0100 slope=0.0050",
    "setup_type": "trend_follow_long",
    "signal_desired": "long",
    "signal_note": "weighted long",
    "status": "forced_exit"
  },
  "hold": {
    "artifact_contract_version": "decision_artifact.v1",
    "block_reason": null,
    "decision_reason": "existing_position",
    "decision_status": "hold",
    "exit_reason": null,
    "plan_action": "hold",
    "plan_note": "combo conf=0.80",
    "reason": "existing_position",
    "regime": "trend_up",
    "regime_note": "adx=25.0 spread=0.0100 slope=0.0050",
    "setup_type": "trend_follow_long",
    "signal_desired": "long",
    "signal_note": "weighted long",
    "status": "hold"
  },
  "skip": {
    "artifact_contract_version": "decision_artifact.v1",
    "block_reason": "no_market_data",
    "decision_reason": null,
    "decision_status": "skip",
    "exit_reason": null,
    "plan_action": null,
    "plan_note": null,
    "reason": "no_market_data",
    "regime": "unknown",
    "regime_note": null,
    "setup_type": "no_trade",
    "signal_desired": "flat",
    "signal_note": null,
    "status": "skip"
  },
  "veto": {
    "artifact_contract_version": "decision_artifact.v1",
    "block_reason": "confidence_below_min",
    "decision_reason": null,
    "decision_status": "veto",
    "exit_reason": null,
    "plan_action": "hold",
    "plan_note": "skip: conf=0.55 below threshold=0.60 (combo)",
    "reason": "confidence_below_min",
    "regime": "trend_up",
    "regime_note": "adx=25.0 spread=0.0100 slope=0.0050",
    "setup_type": "trend_follow_long",
    "signal_desired": "long",
    "signal_note": "weighted long",
    "status": "veto"
  }
}
"""


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "pair": "ETH/USD",
                "tf_min": 15,
                "strategy": {
                    "default_id": "conservative",
                    "allowed_ids": ["conservative"],
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def _write_trend_candles(path: Path) -> None:
    price = 100.0
    rows = []
    for idx in range(80):
        price += 0.9
        rows.append(
            {
                "start_ts": 1_700_000_000 + idx * 900,
                "tf_sec": 900,
                "o": price - 0.2,
                "h": price + 0.4,
                "l": price - 0.5,
                "c": price,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_run_cycle_writes_contract_to_journal_and_snapshot(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    monkeypatch.setenv("APB_CONFIG", str(config_path))
    monkeypatch.setenv("APB_DATA_DIR", str(tmp_path / "data"))

    data_root = Path(str(tmp_path / "data"))
    _write_trend_candles(candles_path("ETH/USD", 15))
    state_path("conservative").parent.mkdir(parents=True, exist_ok=True)
    state_path("conservative").write_text(
        json.dumps(
            {
                "strategy_id": "conservative",
                "equity": 100.0,
                "daily_pnl": 0.0,
                "last_price": 0.0,
                "position": {
                    "side": "long",
                    "notional_usd": 50.0,
                    "collateral_usd": 25.0,
                    "leverage": 2.0,
                    "entry_price": 120.0,
                    "avg_price": 120.0,
                    "stop_loss": 110.0,
                    "take_profit": 150.0,
                    "opened_ts": 1_700_000_000,
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["apb-cycle", "--pair", "ETH/USD", "--tf-min", "15"])
    run_cycle_main()

    today = datetime.now().date().isoformat()
    journal_rows = journal_path(today).read_text(encoding="utf-8").splitlines()
    journal_payload = json.loads(journal_rows[-1])
    snapshot = read_json(snapshot_path(), default={})

    assert data_root.exists()
    assert journal_payload["artifact_contract_version"] == ARTIFACT_CONTRACT_VERSION
    assert journal_payload["provenance"]["strategy_id"] == "conservative"
    assert journal_payload["provenance"]["strategy_fingerprint"] == snapshot["provenance"]["strategy_fingerprint"]
    assert journal_payload["decision"]["decision_status"] == "hold"
    assert journal_payload["decision"]["decision_reason"] == "existing_position"
    assert journal_payload["decision"]["regime"] == snapshot["decision"]["regime"]
    assert journal_payload["effective_config"]["risk"]["min_confidence_to_trade"] == 0.6
    assert snapshot["artifact_contract_version"] == ARTIFACT_CONTRACT_VERSION
    assert snapshot["decision"]["decision_status"] == "hold"
    assert snapshot["decision"]["setup_type"] == "trend_follow_long"
    assert snapshot["effective_config"]["signal"]["trend_weight_in_regime"] is not None
