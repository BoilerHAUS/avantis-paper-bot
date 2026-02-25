PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  domain TEXT,
  title TEXT,
  content TEXT NOT NULL,
  mtime_ns INTEGER,
  bytes INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS docs_domain ON docs(domain);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  title,
  content,
  domain,
  path,
  content='docs',
  content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(rowid, title, content, domain, path)
  VALUES (new.id, new.title, new.content, new.domain, new.path);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, title, content, domain, path)
  VALUES('delete', old.id, old.title, old.content, old.domain, old.path);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, title, content, domain, path)
  VALUES('delete', old.id, old.title, old.content, old.domain, old.path);
  INSERT INTO docs_fts(rowid, title, content, domain, path)
  VALUES (new.id, new.title, new.content, new.domain, new.path);
END;
