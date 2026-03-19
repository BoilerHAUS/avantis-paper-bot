from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifacts import (
    ARTIFACT_CONTRACT_VERSION,
    build_decision_artifact,
    build_effective_config,
    build_provenance,
    strategy_fingerprint,
)
from .config import DEFAULT_STRATEGY_ID, as_dict, load_config
from .paper_engine import execute_paper_with_events
from .risk import compute_risk_budget, plan_from_signal
from .runtime import default_paper_state, effective_risk_cfg, effective_signal_cfg, paper_state_from_raw
from .strategies import analyze_signal
from .storage import candles_path, journal_path, snapshot_path, state_path
from .utils import jsonl_append, read_json, write_json


@dataclass
class CycleResult:
    ts: int
    pair: str
    tf_min: int
    status: str
    note: str


def _today() -> str:
    return datetime.now().date().isoformat()


def _load_recent_candles(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for ln in lines[-limit:]:
        try:
            import json

            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def main() -> None:
    cfg = load_config()

    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default=cfg.pair)
    ap.add_argument("--tf-min", type=int, default=cfg.tf_min)
    ap.add_argument("--candle-limit", type=int, default=200)
    ap.add_argument("--strategy-id", default=cfg.strategy.default_id)
    args = ap.parse_args()

    strategy_id = (args.strategy_id or DEFAULT_STRATEGY_ID).strip()
    if strategy_id not in cfg.strategy.allowed_ids:
        raise SystemExit(
            f"strategy_id '{strategy_id}' not allowed; allowed_ids={cfg.strategy.allowed_ids}"
        )

    cpath = candles_path(args.pair, args.tf_min)
    candles = _load_recent_candles(cpath, limit=args.candle_limit)

    raw_state = read_json(state_path(strategy_id), default=default_paper_state(strategy_id))
    paper = paper_state_from_raw(raw_state)

    now_ts = int(datetime.now().timestamp())

    effective_risk = effective_risk_cfg(cfg, strategy_id)
    signal_cfg = effective_signal_cfg(cfg, strategy_id)
    fingerprint = strategy_fingerprint(strategy_id, effective_risk, signal_cfg)
    provenance = build_provenance(
        strategy_id=strategy_id,
        strategy_fingerprint=fingerprint,
        pair=args.pair,
        tf_min=args.tf_min,
    )
    effective_config = build_effective_config(effective_risk=effective_risk, signal_cfg=signal_cfg)

    rb = compute_risk_budget(float(paper.equity), effective_risk)
    closes = [float(c["c"]) for c in candles if "c" in c]
    last_price = closes[-1] if closes else float(paper.last_price or 0.0)

    analysis = analyze_signal(candles, cfg=signal_cfg) if closes else None
    sig = None if analysis is None else analysis.signal

    if sig is None or last_price <= 0:
        plan = None
        action_note = "no candles yet"
    else:
        plan = plan_from_signal(signal=sig, candles=candles, last_price=last_price, rb=rb, cfg=effective_risk)
        # If we already have a position, upgrade open->scale/hold/flip/close based on direction.
        if paper.position is None:
            pass
        else:
            if sig.desired == "flat":
                plan.action = "close"
                plan.side = paper.position.side
            else:
                desired_side = "long" if sig.desired == "long" else "short"
                if desired_side != paper.position.side:
                    plan.action = "flip"
                    plan.side = desired_side
                else:
                    # for now: hold (later AI can decide scale)
                    plan.action = "hold"
                    plan.side = desired_side

        action_note = plan.note if plan else "no-plan"
    execution_events: list[dict[str, Any]] = []
    previous_position = None if paper.position is None else paper.position.__dict__.copy()

    # Execute paper (vol-based slippage is TODO; placeholder uses 2 bps)
    if plan and last_price > 0:
        paper, raw_events = execute_paper_with_events(paper, plan, last_price=last_price, slip_bps=2.0, ts=now_ts)
        execution_events = [event.__dict__ for event in raw_events]

    decision = build_decision_artifact(
        analysis=analysis,
        plan=plan,
        previous_position=previous_position,
        execution_events=execution_events,
        market_data_ready=bool(closes and last_price > 0),
    )

    res = CycleResult(
        ts=now_ts,
        pair=args.pair,
        tf_min=args.tf_min,
        status="ok",
        note=f"cycle: candles={len(candles)} last_price={last_price:.2f} decision={decision['decision_status']} action={action_note}",
    )

    jpath = journal_path(_today(), strategy_id=strategy_id)
    jsonl_append(
        jpath,
        {
            "type": "cycle",
            "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
            "provenance": provenance,
            "effective_config": effective_config,
            "decision": decision,
            "strategy_id": strategy_id,
            "fingerprint": fingerprint,
            "ts": res.ts,
            "pair": res.pair,
            "tf_min": res.tf_min,
            "status": res.status,
            "note": res.note,
            "config": as_dict(cfg),
            "risk_budget": rb.__dict__,
            "state": {
                "equity": paper.equity,
                "daily_pnl": paper.daily_pnl,
                "position": paper.position.__dict__ if paper.position else None,
                "last_price": paper.last_price,
            },
            "analysis": (
                None
                if analysis is None
                else {
                    "regime_label": analysis.regime_label,
                    "regime_note": analysis.regime_note,
                    "setup_label": analysis.setup_label,
                    "trend_signal": as_dict(analysis.trend_signal),
                    "mean_reversion_signal": as_dict(analysis.mean_reversion_signal),
                }
            ),
            "signal": sig.__dict__ if sig else None,
            "plan": plan.__dict__ if plan else None,
            "execution_events": execution_events,
            "candles_loaded": len(candles),
        },
    )

    # Snapshot for dashboard
    snapshot = {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "provenance": provenance,
        "effective_config": effective_config,
        "decision": decision,
        "ts": now_ts,
        "strategy_id": strategy_id,
        "fingerprint": fingerprint,
        "pair": args.pair,
        "tf_min": args.tf_min,
        "equity": paper.equity,
        "position": paper.position.__dict__ if paper.position else None,
        "daily_pnl": paper.daily_pnl,
        "risk_budget": rb.__dict__,
        "candles_loaded": len(candles),
        "analysis": (
            None
            if analysis is None
            else {
                "regime_label": analysis.regime_label,
                "regime_note": analysis.regime_note,
                "setup_label": analysis.setup_label,
                "trend_signal": as_dict(analysis.trend_signal),
                "mean_reversion_signal": as_dict(analysis.mean_reversion_signal),
            }
        ),
        "signal": sig.__dict__ if sig else None,
        "plan": plan.__dict__ if plan else None,
        "execution_events": execution_events,
        "status": "idle" if paper.position is None else "in_position",
        "note": res.note,
    }

    write_json(
        state_path(strategy_id),
        {
            "strategy_id": strategy_id,
            "equity": paper.equity,
            "daily_pnl": paper.daily_pnl,
            "position": paper.position.__dict__ if paper.position else None,
            "last_price": paper.last_price,
        },
    )
    write_json(snapshot_path(strategy_id), snapshot)

    print(f"[cycle] strategy={strategy_id} wrote journal={jpath} snapshot={snapshot_path(strategy_id)}")


if __name__ == "__main__":
    main()
