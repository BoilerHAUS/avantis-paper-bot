from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    return Path(os.environ.get("APB_DATA_DIR", "data")).resolve()


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _json_default(value: Any):
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def json_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        default=_json_default,
    )


def jsonl_append(path: Path, obj: Any) -> None:
    ensure_parent(path)
    path.open("a", encoding="utf-8").write(json_dumps(obj) + "\n")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json(path: Path, obj: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
