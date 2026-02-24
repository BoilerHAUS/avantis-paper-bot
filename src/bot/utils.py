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


def json_dumps(obj: Any) -> str:
    if is_dataclass(obj):
        obj = asdict(obj)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


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
    if is_dataclass(obj):
        obj = asdict(obj)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
