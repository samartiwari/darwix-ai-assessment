"""Record storage and indexes.

SQLite holds the records and their metadata; it is the source of truth and is
queryable by hand, which matters when a reviewer wants to see why a particular
answer was given. Two indexes sit beside it:

* an FTS5 full-text index, giving BM25 lexical scoring inside the same database
  file, so it cannot drift out of sync with the records table;
* a FAISS flat index over the embeddings, rebuilt deterministically from the
  stored vectors.

A flat index is exact rather than approximate. At a few thousand records the
search is sub-millisecond, and approximate indexes trade recall for a speed gain
that is not needed here.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from core.kb.fetch import ROOT

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id       TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    category        TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    section_path    TEXT NOT NULL,
    version         TEXT NOT NULL,
    effective_date  TEXT,
    checksum        TEXT NOT NULL,
    superseded_by   TEXT,
    pii             INTEGER NOT NULL DEFAULT 0,
    pii_types       TEXT NOT NULL DEFAULT '',
    lang            TEXT NOT NULL DEFAULT 'en',
    kind            TEXT NOT NULL DEFAULT 'prose',
    doc_id          TEXT NOT NULL,
    ordinal         INTEGER NOT NULL DEFAULT 0,
    word_count      INTEGER NOT NULL DEFAULT 0,
    ingested_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_records_category ON records(category);
CREATE INDEX IF NOT EXISTS idx_records_doc ON records(doc_id);
CREATE INDEX IF NOT EXISTS idx_records_checksum ON records(checksum);

-- Lexical index. Kept external to the records table so the row content is not
-- duplicated, and rebuilt alongside it.
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
    record_id UNINDEXED,
    title,
    section_path,
    content,
    tokenize = 'porter unicode61'
);

-- Vector order is recorded so the FAISS row number maps back to a record.
CREATE TABLE IF NOT EXISTS vector_order (
    position   INTEGER PRIMARY KEY,
    record_id  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS build_info (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""


@dataclass
class Record:
    record_id: str
    title: str
    content: str
    category: str
    source_url: str
    source_type: str
    section_path: str
    version: str = "1.0"
    effective_date: str | None = None
    checksum: str = ""
    superseded_by: str | None = None
    pii: bool = False
    pii_types: list[str] = field(default_factory=list)
    lang: str = "en"
    kind: str = "prose"
    doc_id: str = ""
    ordinal: int = 0
    word_count: int = 0
    ingested_at: str = ""

    def as_row(self) -> tuple:
        data = asdict(self)
        data["pii"] = int(self.pii)
        data["pii_types"] = ",".join(self.pii_types)
        data["ingested_at"] = self.ingested_at or datetime.now(UTC).isoformat(timespec="seconds")
        return tuple(data[column] for column in COLUMNS)


COLUMNS = (
    "record_id", "title", "content", "category", "source_url", "source_type",
    "section_path", "version", "effective_date", "checksum", "superseded_by",
    "pii", "pii_types", "lang", "kind", "doc_id", "ordinal", "word_count",
    "ingested_at",
)


def db_path() -> Path:
    import os

    return ROOT / os.getenv("KB_PATH", "kb.sqlite")


def faiss_path() -> Path:
    return db_path().with_suffix(".faiss")


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def row_to_record(row: sqlite3.Row) -> Record:
    data = dict(row)
    data["pii"] = bool(data["pii"])
    data["pii_types"] = [t for t in (data["pii_types"] or "").split(",") if t]
    return Record(**{k: data[k] for k in COLUMNS})


class KnowledgeBase:
    """Read and write access to the records and their indexes."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or db_path()
        self.conn = connect(self.path)
        self._faiss = None

    # --- writing ---------------------------------------------------------

    def replace_all(self, records: list[Record]) -> None:
        """Rebuild the record set in one transaction.

        A full rebuild rather than an incremental update: the corpus is small,
        and a rebuild cannot leave the lexical index and the records table
        describing different content.
        """
        with self.conn:
            self.conn.execute("DELETE FROM records")
            self.conn.execute("DELETE FROM records_fts")
            self.conn.execute("DELETE FROM vector_order")
            placeholders = ",".join("?" for _ in COLUMNS)
            self.conn.executemany(
                f"INSERT INTO records ({','.join(COLUMNS)}) VALUES ({placeholders})",
                [r.as_row() for r in records],
            )
            self.conn.executemany(
                "INSERT INTO records_fts (record_id, title, section_path, content) "
                "VALUES (?,?,?,?)",
                [(r.record_id, r.title, r.section_path, r.content) for r in records],
            )
            self.conn.executemany(
                "INSERT INTO vector_order (position, record_id) VALUES (?,?)",
                [(i, r.record_id) for i, r in enumerate(records)],
            )

    def build_vector_index(self, vectors: np.ndarray) -> None:
        import faiss

        if vectors.ndim != 2:
            raise ValueError(f"expected a 2-D array of vectors, got shape {vectors.shape}")
        stored = self.conn.execute("SELECT COUNT(*) AS n FROM vector_order").fetchone()["n"]
        if stored != vectors.shape[0]:
            raise ValueError(
                f"{vectors.shape[0]} vectors for {stored} records — the index would "
                "not map back to the right rows"
            )
        # Inner product on normalized vectors is cosine similarity.
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(faiss_path()))
        self._faiss = index

    def set_build_info(self, info: dict[str, str]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO build_info (key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                list(info.items()),
            )

    # --- reading ---------------------------------------------------------

    @property
    def faiss_index(self):
        if self._faiss is None:
            import faiss

            path = faiss_path()
            if not path.exists():
                raise FileNotFoundError(
                    f"no vector index at {path} — run scripts/build_kb.py first"
                )
            self._faiss = faiss.read_index(str(path))
        return self._faiss

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()["n"]

    def build_info(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM build_info").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def record_ids_in_vector_order(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT record_id FROM vector_order ORDER BY position"
        ).fetchall()
        return [r["record_id"] for r in rows]

    def get(self, record_ids: list[str]) -> dict[str, Record]:
        if not record_ids:
            return {}
        marks = ",".join("?" for _ in record_ids)
        rows = self.conn.execute(
            f"SELECT * FROM records WHERE record_id IN ({marks})", record_ids
        ).fetchall()
        return {row["record_id"]: row_to_record(row) for row in rows}

    def all_records(self) -> list[Record]:
        rows = self.conn.execute("SELECT * FROM records ORDER BY record_id").fetchall()
        return [row_to_record(r) for r in rows]

    def category_counts(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT category, COUNT(*) AS n FROM records GROUP BY category ORDER BY n DESC"
        ).fetchall()
        return {r["category"]: r["n"] for r in rows}

    def close(self) -> None:
        self.conn.close()


def load_metadata() -> dict:
    """Read the build manifest written alongside the database."""
    path = db_path().with_suffix(".manifest.json")
    return json.loads(path.read_text()) if path.exists() else {}


def write_metadata(data: dict) -> None:
    db_path().with_suffix(".manifest.json").write_text(json.dumps(data, indent=2))
