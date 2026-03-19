from __future__ import annotations

import json
from pathlib import Path

from bot.replay import replay_fixed_window, write_comparison


def _write_fixture_files(tmp_path: Path) -> tuple[Path, Path]:
    config = {
        "pair": "ETH/USD",
        "tf_min": 15,
        "risk": {"min_confidence_to_trade": 0.60},
        "strategy": {
            "default_id": "conservative",
            "allowed_ids": ["conservative", "aggressive"],
            "profiles": {
                "aggressive": {"regime_confidence_floor": 0.70},
            },
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    price = 100.0
    candles = []
    for i in range(80):
        if i < 30:
            price += 0.05
        elif i < 55:
            price += 0.9
        else:
            price -= 1.1
        candles.append(
            {
                "start_ts": 1_700_000_000 + i * 900,
                "tf_sec": 900,
                "o": price - 0.2,
                "h": price + 0.4,
                "l": price - 0.5,
                "c": price,
            }
        )

    candles_path = tmp_path / "candles.jsonl"
    candles_path.write_text(
        "".join(json.dumps(candle, separators=(",", ":")) + "\n" for candle in candles),
        encoding="utf-8",
    )
    return config_path, candles_path


def test_replay_outputs_are_deterministic(monkeypatch, tmp_path: Path) -> None:
    config_path, candles_path = _write_fixture_files(tmp_path)
    monkeypatch.setenv("APB_CONFIG", str(config_path))

    start_ts = 1_700_000_000 + 49 * 900
    end_ts = 1_700_000_000 + 79 * 900

    first = replay_fixed_window(
        strategy_id="aggressive",
        candles_file=candles_path,
        pair="ETH/USD",
        tf_min=15,
        output_root=tmp_path / "out-a",
        start_ts=start_ts,
        end_ts=end_ts,
    )
    second = replay_fixed_window(
        strategy_id="aggressive",
        candles_file=candles_path,
        pair="ETH/USD",
        tf_min=15,
        output_root=tmp_path / "out-b",
        start_ts=start_ts,
        end_ts=end_ts,
    )

    assert first.summary == second.summary
    assert first.manifest == second.manifest
    assert first.cycles == second.cycles
    assert first.trades == second.trades
    assert first.equity_curve == second.equity_curve

    for name in ("manifest.json", "summary.json", "cycles.jsonl", "trades.jsonl", "equity.jsonl"):
        assert (first.output_dir / name).read_text(encoding="utf-8") == (
            second.output_dir / name
        ).read_text(encoding="utf-8")

    assert first.summary["trade_count"] == 3
    assert first.summary["decision_counts"] == {"skip": 14, "trade": 3, "veto": 14}
    assert any(row["decision"]["status"] == "veto" for row in first.cycles)
    assert any(row["analysis"]["regime_label"] == "trend_up" for row in first.cycles)
    assert all("regime_classifier" in row["analysis"] for row in first.cycles)
    assert first.manifest["schemas"]["regime_classifier"] == "regime_classifier.v1"
    assert any(trade["kind"] == "take_profit_partial" for trade in first.trades)


def test_replay_comparison_uses_same_window(monkeypatch, tmp_path: Path) -> None:
    config_path, candles_path = _write_fixture_files(tmp_path)
    monkeypatch.setenv("APB_CONFIG", str(config_path))

    start_ts = 1_700_000_000 + 49 * 900
    end_ts = 1_700_000_000 + 79 * 900
    output_root = tmp_path / "out"

    baseline = replay_fixed_window(
        strategy_id="conservative",
        candles_file=candles_path,
        pair="ETH/USD",
        tf_min=15,
        output_root=output_root,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    candidate = replay_fixed_window(
        strategy_id="aggressive",
        candles_file=candles_path,
        pair="ETH/USD",
        tf_min=15,
        output_root=output_root,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    comparison_path = write_comparison(output_root, baseline, candidate)
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))

    assert baseline.summary["window"] == candidate.summary["window"] == comparison["window"]
    assert comparison["baseline"]["strategy_id"] == "conservative"
    assert comparison["candidate"]["strategy_id"] == "aggressive"
    assert comparison["delta"]["trade_count"] == 3
    assert comparison["baseline"]["summary"]["trade_count"] == 0
    assert comparison["candidate"]["summary"]["trade_count"] == 3
