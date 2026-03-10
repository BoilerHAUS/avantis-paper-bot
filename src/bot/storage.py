from __future__ import annotations

import re
from pathlib import Path

from .config import DEFAULT_STRATEGY_ID
from .utils import data_dir


def candles_path(pair: str, tf_min: int) -> Path:
    sym = pair.replace("/", "-").replace(" ", "")
    return data_dir() / "candles" / f"{sym}-{tf_min}m.jsonl"


_STRATEGY_ID_RE = re.compile(r"^[a-z0-9_-]+$")


def _sanitize_strategy_id(strategy_id: str) -> str:
    sid = (strategy_id or DEFAULT_STRATEGY_ID).strip()
    if sid == DEFAULT_STRATEGY_ID:
        return sid
    if not _STRATEGY_ID_RE.match(sid):
        raise ValueError(f"invalid strategy_id '{strategy_id}'")
    return sid


def _strategy_root(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    sid = _sanitize_strategy_id(strategy_id)
    if sid == DEFAULT_STRATEGY_ID:
        return data_dir()
    return data_dir() / "strategies" / sid


def journal_path(date_yyyy_mm_dd: str, strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "journal" / f"{date_yyyy_mm_dd}.jsonl"


def state_path(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "state" / "current.json"


def snapshot_path(strategy_id: str = DEFAULT_STRATEGY_ID) -> Path:
    return _strategy_root(strategy_id) / "state" / "snapshot.json"
