from __future__ import annotations

from pathlib import Path

from .utils import data_dir


def candles_path(pair: str, tf_min: int) -> Path:
    sym = pair.replace("/", "-").replace(" ", "")
    return data_dir() / "candles" / f"{sym}-{tf_min}m.jsonl"


def journal_path(date_yyyy_mm_dd: str) -> Path:
    return data_dir() / "journal" / f"{date_yyyy_mm_dd}.jsonl"


def state_path() -> Path:
    return data_dir() / "state" / "current.json"


def snapshot_path() -> Path:
    return data_dir() / "state" / "snapshot.json"
