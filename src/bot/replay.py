from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .artifacts import ARTIFACT_CONTRACT_VERSION, build_decision_artifact, build_provenance, strategy_fingerprint
from .config import DEFAULT_STRATEGY_ID, as_dict, load_config
from .paper_engine import execute_paper_with_events
from .risk import compute_risk_budget, plan_from_signal
from .runtime import default_paper_state, effective_risk_cfg, effective_signal_cfg, paper_state_from_raw
from .storage import candles_path
from .strategies import analyze_signal
from .utils import data_dir, jsonl_write, write_json_stable


@dataclass
class ReplayBundle:
    strategy_id: str
    fingerprint: str
    output_dir: Path
    manifest: dict[str, Any]
    summary: dict[str, Any]
    cycles: list[dict[str, Any]]
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]


def _sanitize_pair(pair: str) -> str:
    return pair.replace("/", "-").replace(" ", "")


def _load_candles(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing candles file: {path}")

    rows: list[tuple[int, dict[str, Any]]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append((idx, payload))

    rows.sort(key=lambda item: (int(item[1].get("start_ts", 0)), item[0]))
    return [row for _, row in rows]


def _window_candles(
    candles: list[dict[str, Any]],
    *,
    start_ts: int | None,
    end_ts: int | None,
) -> tuple[list[dict[str, Any]], int, int]:
    selected = [
        candle
        for candle in candles
        if (start_ts is None or int(candle.get("start_ts", 0)) >= start_ts)
        and (end_ts is None or int(candle.get("start_ts", 0)) <= end_ts)
    ]
    if not selected:
        raise ValueError("no candles matched the requested replay window")

    first_ts = int(selected[0]["start_ts"])
    last_ts = int(selected[-1]["start_ts"])
    return selected, first_ts, last_ts


def _artifact_dir(
    *,
    output_root: Path,
    pair: str,
    tf_min: int,
    strategy_id: str,
    fingerprint: str,
    start_ts: int,
    end_ts: int,
) -> Path:
    pair_slug = _sanitize_pair(pair)
    return output_root / f"{pair_slug}-{tf_min}m" / f"{start_ts}-{end_ts}" / f"{strategy_id}-{fingerprint}"


def _paper_state_dict(state) -> dict[str, Any]:
    return {
        "equity": state.equity,
        "daily_pnl": state.daily_pnl,
        "position": (None if state.position is None else as_dict(state.position)),
        "last_price": state.last_price,
    }


def _max_drawdown(equity_curve: list[dict[str, Any]]) -> float:
    peak = None
    max_dd = 0.0
    for point in equity_curve:
        equity = float(point["equity"])
        if peak is None or equity > peak:
            peak = equity
        if peak and peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd


def replay_fixed_window(
    *,
    strategy_id: str,
    candles_file: Path,
    pair: str,
    tf_min: int,
    output_root: Path,
    start_ts: int | None = None,
    end_ts: int | None = None,
    initial_equity: float = 100.0,
    slip_bps: float = 2.0,
) -> ReplayBundle:
    cfg = load_config()
    strategy_id = (strategy_id or DEFAULT_STRATEGY_ID).strip()
    if strategy_id not in cfg.strategy.allowed_ids:
        raise ValueError(f"strategy_id '{strategy_id}' not allowed; allowed_ids={cfg.strategy.allowed_ids}")

    all_candles = _load_candles(candles_file)
    window_candles, window_start_ts, window_end_ts = _window_candles(
        all_candles,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    by_ts = {int(candle["start_ts"]): idx for idx, candle in enumerate(all_candles)}

    effective_risk = effective_risk_cfg(cfg, strategy_id)
    signal_cfg = effective_signal_cfg(cfg, strategy_id)
    fingerprint = strategy_fingerprint(strategy_id, effective_risk, signal_cfg)
    provenance = build_provenance(
        strategy_id=strategy_id,
        strategy_fingerprint=fingerprint,
        pair=pair,
        tf_min=tf_min,
    )
    output_dir = _artifact_dir(
        output_root=output_root,
        pair=pair,
        tf_min=tf_min,
        strategy_id=strategy_id,
        fingerprint=fingerprint,
        start_ts=window_start_ts,
        end_ts=window_end_ts,
    )

    raw_state = default_paper_state(strategy_id)
    raw_state["equity"] = float(initial_equity)
    state = paper_state_from_raw(raw_state)

    cycles: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []
    decision_counter: Counter[str] = Counter()
    setup_counter: Counter[str] = Counter()
    regime_counter: Counter[str] = Counter()

    for candle in window_candles:
        candle_ts = int(candle["start_ts"])
        candle_idx = by_ts[candle_ts]
        history = all_candles[: candle_idx + 1]
        last_price = float(candle["c"])
        rb = compute_risk_budget(float(state.equity), effective_risk)
        analysis = analyze_signal(history, cfg=signal_cfg)
        plan = plan_from_signal(
            signal=analysis.signal,
            candles=history,
            last_price=last_price,
            rb=rb,
            cfg=effective_risk,
        )

        previous_position = None if state.position is None else asdict(state.position)
        if state.position is not None:
            if analysis.signal.desired == "flat":
                plan.action = "close"
                plan.side = state.position.side
            else:
                desired_side = "long" if analysis.signal.desired == "long" else "short"
                if desired_side != state.position.side:
                    plan.action = "flip"
                    plan.side = desired_side
                else:
                    plan.action = "hold"
                    plan.side = desired_side

        state, execution_events = execute_paper_with_events(
            state,
            plan,
            last_price=last_price,
            slip_bps=slip_bps,
            ts=candle_ts,
        )
        execution_payload = [asdict(event) for event in execution_events]
        decision = build_decision_artifact(
            analysis=analysis,
            plan=plan,
            previous_position=previous_position,
            execution_events=execution_payload,
        )
        decision_counter[decision["decision_status"]] += 1
        setup_counter[analysis.setup_label] += 1
        regime_counter[analysis.regime_label] += 1
        trades.extend(execution_payload)
        equity_curve.append(
            {
                "ts": candle_ts,
                "equity": state.equity,
                "daily_pnl": state.daily_pnl,
                "position_side": (None if state.position is None else state.position.side),
                "position_notional_usd": (0.0 if state.position is None else state.position.notional_usd),
            }
        )
        cycles.append(
            {
                "ts": candle_ts,
                "candle": {
                    "start_ts": candle_ts,
                    "o": float(candle["o"]),
                    "h": float(candle["h"]),
                    "l": float(candle["l"]),
                    "c": last_price,
                    "tf_sec": int(candle.get("tf_sec", tf_min * 60)),
                },
                "analysis": {
                    "regime_label": analysis.regime_label,
                    "regime_note": analysis.regime_note,
                    "setup_label": analysis.setup_label,
                    "trend_signal": as_dict(analysis.trend_signal),
                    "mean_reversion_signal": as_dict(analysis.mean_reversion_signal),
                },
                "signal": as_dict(analysis.signal),
                "plan": as_dict(plan),
                "decision": decision,
                "risk_budget": as_dict(rb),
                "execution_events": execution_payload,
                "state": _paper_state_dict(state),
                "provenance": provenance,
            }
        )

    summary = {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "strategy_id": strategy_id,
        "fingerprint": fingerprint,
        "provenance": provenance,
        "pair": pair,
        "tf_min": tf_min,
        "window": {
            "start_ts": window_start_ts,
            "end_ts": window_end_ts,
            "candles": len(window_candles),
        },
        "initial_equity": initial_equity,
        "ending_equity": state.equity,
        "net_pnl": state.equity - initial_equity,
        "return_pct": (0.0 if initial_equity == 0 else (state.equity / initial_equity - 1.0)),
        "max_drawdown_pct": _max_drawdown(equity_curve),
        "decision_counts": dict(sorted(decision_counter.items())),
        "setup_counts": dict(sorted(setup_counter.items())),
        "regime_counts": dict(sorted(regime_counter.items())),
        "execution_event_count": len(trades),
        "trade_count": sum(1 for trade in trades if trade["kind"] in {"open", "flip_open", "scale"}),
        "close_count": sum(
            1 for trade in trades if trade["kind"] in {"close", "flip_close", "stop_loss", "take_profit_partial"}
        ),
    }
    manifest = {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "contract_version": "replay.v1",
        "strategy_id": strategy_id,
        "fingerprint": fingerprint,
        "provenance": provenance,
        "pair": pair,
        "tf_min": tf_min,
        "window": summary["window"],
        "inputs": {
            "candles_file": str(candles_file),
            "slip_bps": slip_bps,
            "initial_equity": initial_equity,
        },
        "effective_config": {
            "risk": as_dict(effective_risk),
            "signal": as_dict(signal_cfg),
        },
        "artifacts": {
            "summary": "summary.json",
            "manifest": "manifest.json",
            "cycles": "cycles.jsonl",
            "trades": "trades.jsonl",
            "equity_curve": "equity.jsonl",
        },
    }

    write_json_stable(output_dir / "manifest.json", manifest)
    write_json_stable(output_dir / "summary.json", summary)
    jsonl_write(output_dir / "cycles.jsonl", cycles, stable=True)
    jsonl_write(output_dir / "trades.jsonl", trades, stable=True)
    jsonl_write(output_dir / "equity.jsonl", equity_curve, stable=True)

    return ReplayBundle(
        strategy_id=strategy_id,
        fingerprint=fingerprint,
        output_dir=output_dir,
        manifest=manifest,
        summary=summary,
        cycles=cycles,
        trades=trades,
        equity_curve=equity_curve,
    )


def write_comparison(output_root: Path, baseline: ReplayBundle, candidate: ReplayBundle) -> Path:
    comparison = {
        "contract_version": "replay-compare.v1",
        "window": baseline.summary["window"],
        "baseline": {
            "strategy_id": baseline.strategy_id,
            "fingerprint": baseline.fingerprint,
            "summary": baseline.summary,
            "artifact_dir": str(baseline.output_dir),
        },
        "candidate": {
            "strategy_id": candidate.strategy_id,
            "fingerprint": candidate.fingerprint,
            "summary": candidate.summary,
            "artifact_dir": str(candidate.output_dir),
        },
        "delta": {
            "net_pnl": candidate.summary["net_pnl"] - baseline.summary["net_pnl"],
            "return_pct": candidate.summary["return_pct"] - baseline.summary["return_pct"],
            "max_drawdown_pct": candidate.summary["max_drawdown_pct"] - baseline.summary["max_drawdown_pct"],
            "trade_count": candidate.summary["trade_count"] - baseline.summary["trade_count"],
            "close_count": candidate.summary["close_count"] - baseline.summary["close_count"],
        },
        "boundary": "Comparison is deterministic for one symbol/timeframe/window under one candle file and one config snapshot.",
    }
    path = (
        output_root
        / f"{_sanitize_pair(baseline.summary['pair'])}-{baseline.summary['tf_min']}m"
        / f"{baseline.summary['window']['start_ts']}-{baseline.summary['window']['end_ts']}"
        / f"compare-{baseline.strategy_id}-vs-{candidate.strategy_id}.json"
    )
    write_json_stable(path, comparison)
    return path


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default=cfg.pair)
    ap.add_argument("--tf-min", type=int, default=cfg.tf_min)
    ap.add_argument("--strategy-id", default=cfg.strategy.default_id)
    ap.add_argument("--compare-strategy-id", default=None)
    ap.add_argument("--candles-file", default=None)
    ap.add_argument("--start-ts", type=int, default=None)
    ap.add_argument("--end-ts", type=int, default=None)
    ap.add_argument("--initial-equity", type=float, default=100.0)
    ap.add_argument("--slip-bps", type=float, default=2.0)
    ap.add_argument("--output-dir", default=str(data_dir() / "replays"))
    args = ap.parse_args()

    candle_file = Path(args.candles_file) if args.candles_file else candles_path(args.pair, args.tf_min)
    output_root = Path(args.output_dir)

    primary = replay_fixed_window(
        strategy_id=args.strategy_id,
        candles_file=candle_file,
        pair=args.pair,
        tf_min=args.tf_min,
        output_root=output_root,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        initial_equity=args.initial_equity,
        slip_bps=args.slip_bps,
    )

    print(f"[replay] strategy={primary.strategy_id} artifacts={primary.output_dir}")

    if args.compare_strategy_id:
        compare = replay_fixed_window(
            strategy_id=args.compare_strategy_id,
            candles_file=candle_file,
            pair=args.pair,
            tf_min=args.tf_min,
            output_root=output_root,
            start_ts=args.start_ts,
            end_ts=args.end_ts,
            initial_equity=args.initial_equity,
            slip_bps=args.slip_bps,
        )
        comparison_path = write_comparison(output_root, primary, compare)
        print(
            f"[replay] comparison baseline={primary.strategy_id} candidate={compare.strategy_id} file={comparison_path}"
        )


if __name__ == "__main__":
    main()
