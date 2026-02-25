#!/usr/bin/env python3
"""Index the GOAT Crypto Trading Agent Pack into a local SQLite+FTS5 database.

Design goals:
- local-first, no dependencies beyond Python stdlib + sqlite3
- idempotent: re-running updates changed files only
- safe: only reads files under the knowledge root

DB:
- /home/boilerrat/clawd/state/goat_kb.db

Usage:
  python3 scripts/goat_kb_index.py \
    --root /home/boilerrat/clawd/knowledge/GOAT_Crypto_Trading_Agent_Pack \
    --db /home/boilerrat/clawd/state/goat_kb.db
"""

import argparse
import datetime as dt
import os
import sqlite3
from pathlib import Path

TEXT_EXTS = {".md", ".txt"}


def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def guess_domain(rel: Path) -> str:
    parts = rel.parts
    if not parts:
        return ""
    # First folder name is the domain bucket (01_quant_foundations, etc.)
    return parts[0]


def guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:200]
    return fallback[:200]


def read_text(path: Path) -> str:
    # UTF-8 first; fall back to latin-1 to avoid hard failures on odd docs.
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def init_db(db_path: Path, init_sql_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(init_sql_path.read_text(encoding="utf-8"))
        con.commit()
    finally:
        con.close()


def get_existing(con: sqlite3.Connection):
    cur = con.execute("SELECT path, mtime_ns, bytes FROM docs")
    return {row[0]: {"mtime_ns": row[1], "bytes": row[2]} for row in cur.fetchall()}


def upsert_doc(con: sqlite3.Connection, *, path: str, domain: str, title: str, content: str, mtime_ns: int, bytes_: int):
    now = utc_now()
    con.execute(
        """
        INSERT INTO docs(path, domain, title, content, mtime_ns, bytes, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(path) DO UPDATE SET
          domain=excluded.domain,
          title=excluded.title,
          content=excluded.content,
          mtime_ns=excluded.mtime_ns,
          bytes=excluded.bytes,
          updated_at=excluded.updated_at
        """,
        (path, domain, title, content, mtime_ns, bytes_, now, now),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--init-sql", default="/home/boilerrat/clawd/scripts/goat_kb_init.sql")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    db = Path(args.db).expanduser().resolve()
    init_sql = Path(args.init_sql).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a dir: {root}")
    if not init_sql.exists():
        raise SystemExit(f"Init SQL not found: {init_sql}")

    init_db(db, init_sql)

    con = sqlite3.connect(str(db))
    try:
        con.row_factory = sqlite3.Row
        existing = get_existing(con)

        scanned = 0
        updated = 0
        skipped = 0

        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in TEXT_EXTS:
                continue

            # safety: ensure within root
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue

            st = p.stat()
            scanned += 1
            key = str(p)
            prev = existing.get(key)
            if prev and int(prev["mtime_ns"] or 0) == int(st.st_mtime_ns) and int(prev["bytes"] or 0) == int(st.st_size):
                skipped += 1
                continue

            text = read_text(p).strip()
            domain = guess_domain(rel)
            title = guess_title(text, fallback=p.stem)
            upsert_doc(
                con,
                path=key,
                domain=domain,
                title=title,
                content=text,
                mtime_ns=int(st.st_mtime_ns),
                bytes_=int(st.st_size),
            )
            updated += 1

        con.commit()
        print(f"Indexed GOAT KB: scanned={scanned} updated={updated} skipped={skipped} db={db}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
