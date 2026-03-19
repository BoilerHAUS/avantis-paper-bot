from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_STRATEGY_ID, as_dict, load_config
from .paper_engine import execute_paper
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

    rb = compute_risk_budget(float(paper.equity), effective_risk)
    closes = [float(c["c"]) for c in candles if "c" in c]
    last_price = closes[-1] if closes else float(paper.last_price or 0.0)

    analysis = analyze_signal(candles, cfg=signal_cfg) if closes else None
    sig = analysis.signal if analysis else None

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

    # Execute paper (vol-based slippage is TODO; placeholder uses 2 bps)
    if plan and last_price > 0:
        paper = execute_paper(paper, plan, last_price=last_price, slip_bps=2.0, ts=now_ts)

    res = CycleResult(
        ts=now_ts,
        pair=args.pair,
        tf_min=args.tf_min,
        status="ok",
        note=f"cycle: candles={len(candles)} last_price={last_price:.2f} action={action_note}",
    )

    jpath = journal_path(_today(), strategy_id=strategy_id)
    jsonl_append(
        jpath,
        {
            "type": "cycle",
            "strategy_id": strategy_id,
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
            "signal": sig.__dict__ if sig else None,
            "regime_classifier": (as_dict(analysis.regime) if analysis else None),
            "plan": plan.__dict__ if plan else None,
            "candles_loaded": len(candles),
        },
    )

    # Snapshot for dashboard
    snapshot = {
        "ts": now_ts,
        "strategy_id": strategy_id,
        "pair": args.pair,
        "tf_min": args.tf_min,
        "equity": paper.equity,
        "position": paper.position.__dict__ if paper.position else None,
        "daily_pnl": paper.daily_pnl,
        "risk_budget": rb.__dict__,
        "candles_loaded": len(candles),
        "signal": sig.__dict__ if sig else None,
        "regime_classifier": (as_dict(analysis.regime) if analysis else None),
        "plan": plan.__dict__ if plan else None,
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
