from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import as_dict, load_config
from .risk import compute_risk_budget
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
    args = ap.parse_args()

    cpath = candles_path(args.pair, args.tf_min)
    candles = _load_recent_candles(cpath, limit=args.candle_limit)

    # Minimal paper state for v0
    state = read_json(state_path(), default={"equity": 10_000.0, "position": None, "daily_pnl": 0.0})

    # v0: do nothing; later: strategy->risk->paper executor
    now_ts = int(datetime.now().timestamp())

    rb = compute_risk_budget(float(state.get("equity", 0.0)), cfg.risk)
    res = CycleResult(
        ts=now_ts,
        pair=args.pair,
        tf_min=args.tf_min,
        status="ok",
        note=f"v0 scaffold: loaded {len(candles)} candles from {cpath}; no trades executed.",
    )

    jpath = journal_path(_today())
    jsonl_append(
        jpath,
        {
            "type": "cycle",
            "ts": res.ts,
            "pair": res.pair,
            "tf_min": res.tf_min,
            "status": res.status,
            "note": res.note,
            "config": as_dict(cfg),
            "risk_budget": rb.__dict__,
            "state": state,
            "candles_loaded": len(candles),
        },
    )

    # Snapshot for dashboard
    snapshot = {
        "ts": now_ts,
        "pair": args.pair,
        "tf_min": args.tf_min,
        "equity": state.get("equity"),
        "position": state.get("position"),
        "daily_pnl": state.get("daily_pnl"),
        "risk_budget": rb.__dict__,
        "candles_loaded": len(candles),
        "status": "idle",
        "note": "v0 scaffold (no trading yet)",
    }

    write_json(state_path(), state)
    write_json(snapshot_path(), snapshot)

    print(f"[cycle] wrote journal={jpath} snapshot={snapshot_path()}")


if __name__ == "__main__":
    main()
