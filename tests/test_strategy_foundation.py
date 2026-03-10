from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from bot.storage import journal_path, snapshot_path, state_path


def test_conservative_paths_remain_legacy() -> None:
    d = "2026-03-10"
    assert str(state_path()) == str(Path.cwd() / "data" / "state" / "current.json")
    assert str(snapshot_path()) == str(Path.cwd() / "data" / "state" / "snapshot.json")
    assert str(journal_path(d)) == str(Path.cwd() / "data" / "journal" / f"{d}.jsonl")


def test_non_default_strategy_paths_are_isolated() -> None:
    d = "2026-03-10"
    sid = "aggressive"
    assert str(state_path(sid)).endswith("data/strategies/aggressive/state/current.json")
    assert str(snapshot_path(sid)).endswith("data/strategies/aggressive/state/snapshot.json")
    assert str(journal_path(d, sid)).endswith(f"data/strategies/aggressive/journal/{d}.jsonl")


def test_dashboard_unknown_strategy_falls_back_to_default() -> None:
    repo = Path(__file__).resolve().parents[1]
    js = (
        "import { normalizeStrategyId } from './dashboard/strategy.mjs';"
        "const out = normalizeStrategyId('weird', ['conservative','aggressive'], 'conservative');"
        "console.log(JSON.stringify({out}));"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["out"] == "conservative"
