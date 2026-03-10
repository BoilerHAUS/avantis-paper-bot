from __future__ import annotations

from pathlib import Path

from .config import DEFAULT_STRATEGY_ID
from .utils import data_dir


def candles_path(pair: str, tf_min: int) -> Path:
    sym = pair.replace("/", "-").replace(" ", "")
    return data_dir() / "candles" / f"{sym}-{tf_min}m.jsonl"


def _strategy_root(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    if strategy_id == DEFAULT_STRATEGY_ID:
        return data_dir()
    return data_dir() / "strategies" / strategy_id


def journal_path(date_yyyy_mm_dd: str, strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "journal" / f"{date_yyyy_mm_dd}.jsonl"


def state_path(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "state" / "current.json"


def snapshot_path(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "state" / "snapshot.json"
