#!/usr/bin/env python3
"""Query the GOAT KB SQLite+FTS5 index.

Usage:
  python3 scripts/goat_kb_query.py --q "overfitting PBO" --limit 5

Output:
- prints short results with path + domain + title + snippet
"""

import argparse
import sqlite3

DEFAULT_DB = "/home/boilerrat/clawd/state/goat_kb.db"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--q", required=True)
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    try:
        con.row_factory = sqlite3.Row
        cur = con.execute(
            """
            SELECT d.path, d.domain, d.title,
                   snippet(docs_fts, 1, '[', ']', ' … ', 12) AS snip
            FROM docs_fts
            JOIN docs d ON d.id = docs_fts.rowid
            WHERE docs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (args.q, args.limit),
        )
        rows = cur.fetchall()
        if not rows:
            print("No results")
            return
        for i, r in enumerate(rows, 1):
            print(f"{i}. [{r['domain']}] {r['title']}\n   {r['path']}\n   {r['snip']}\n")
    finally:
        con.close()


if __name__ == "__main__":
    main()
