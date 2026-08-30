"""
SQLite persistence for analysis history + the similarity reference corpus.

Deliberately stdlib-only (sqlite3, no ORM) — this project has no database
today and rule 6 ("don't introduce unnecessary complexity") argues against
pulling in SQLAlchemy for what is fundamentally a handful of small tables.

Two tables:
  - analysis_history: one row per completed text or image analysis (Feature 3).
  - reference_chunks: the similarity/plagiarism comparison corpus (Feature 1).
    Every analyzed text document contributes its chunks here, so future
    analyses can be compared against real prior submissions — never a
    fabricated external source (see app/similarity.py).

DB file lives at backend/data/history.db, created on first use.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Literal

import numpy as np

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(_DATA_DIR, "history.db")

MAX_REFERENCE_CHUNKS = 20_000  # soft cap so the comparison corpus can't grow unbounded

SortOrder = Literal["newest", "oldest"]
HistoryFilter = Literal["all", "text", "image"]


def _ensure_dirs() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name       TEXT NOT NULL,
                file_type       TEXT NOT NULL,
                analysis_type   TEXT NOT NULL CHECK (analysis_type IN ('text', 'image')),
                ai_probability  REAL,
                similarity_score REAL,
                confidence      TEXT,
                status          TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                report_path     TEXT,
                result_json     TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reference_chunks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id   INTEGER NOT NULL REFERENCES analysis_history(id) ON DELETE CASCADE,
                file_name    TEXT NOT NULL,
                chunk_index  INTEGER NOT NULL,
                chunk_text   TEXT NOT NULL,
                embedding    BLOB NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON analysis_history(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_type ON analysis_history(analysis_type)")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_history(
    *,
    file_name: str,
    file_type: str,
    analysis_type: Literal["text", "image"],
    ai_probability: float | None,
    similarity_score: float | None,
    confidence: str | None,
    status: str,
    result_json: dict[str, Any],
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_history
                (file_name, file_type, analysis_type, ai_probability, similarity_score,
                 confidence, status, created_at, report_path, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                file_name, file_type, analysis_type, ai_probability, similarity_score,
                confidence, status, _now_iso(), json.dumps(result_json, default=str),
            ),
        )
        return int(cur.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["result_json"] = json.loads(d["result_json"])
    except (TypeError, json.JSONDecodeError):
        d["result_json"] = {}
    return d


def list_history(filter_type: HistoryFilter = "all", sort: SortOrder = "newest") -> list[dict[str, Any]]:
    where = "" if filter_type == "all" else "WHERE analysis_type = ?"
    order = "DESC" if sort == "newest" else "ASC"
    params = () if filter_type == "all" else (filter_type,)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM analysis_history {where} ORDER BY created_at {order}", params
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_history(history_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM analysis_history WHERE id = ?", (history_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_history(history_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM analysis_history WHERE id = ?", (history_id,))
        return cur.rowcount > 0


def get_dashboard_stats() -> dict[str, Any]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
        text_count = conn.execute(
            "SELECT COUNT(*) FROM analysis_history WHERE analysis_type = 'text'"
        ).fetchone()[0]
        image_count = conn.execute(
            "SELECT COUNT(*) FROM analysis_history WHERE analysis_type = 'image'"
        ).fetchone()[0]
        ai_flagged = conn.execute(
            "SELECT COUNT(*) FROM analysis_history WHERE ai_probability >= 60"
        ).fetchone()[0]
        avg_similarity = conn.execute(
            "SELECT AVG(similarity_score) FROM analysis_history WHERE similarity_score IS NOT NULL"
        ).fetchone()[0]
    return {
        "total_analyses": total,
        "text_analyses": text_count,
        "image_analyses": image_count,
        "ai_flagged": ai_flagged,
        "average_similarity": round(avg_similarity, 1) if avg_similarity is not None else 0.0,
    }


# ══════════════════════════════════════════════════════════════════════════
# Similarity reference corpus (Feature 1)
# ══════════════════════════════════════════════════════════════════════════

def insert_reference_chunks(history_id: int, file_name: str, chunks: list[str], embeddings: np.ndarray) -> None:
    if not chunks:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO reference_chunks (history_id, file_name, chunk_index, chunk_text, embedding) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (history_id, file_name, i, chunk, embeddings[i].astype(np.float32).tobytes())
                for i, chunk in enumerate(chunks)
            ],
        )
        # Soft cap: trim oldest chunks once the corpus grows past the limit.
        count = conn.execute("SELECT COUNT(*) FROM reference_chunks").fetchone()[0]
        if count > MAX_REFERENCE_CHUNKS:
            excess = count - MAX_REFERENCE_CHUNKS
            conn.execute(
                "DELETE FROM reference_chunks WHERE id IN "
                "(SELECT id FROM reference_chunks ORDER BY id ASC LIMIT ?)",
                (excess,),
            )


def get_all_reference_chunks() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT history_id, file_name, chunk_index, chunk_text, embedding FROM reference_chunks"
        ).fetchall()
    return [
        {
            "history_id": r["history_id"],
            "file_name": r["file_name"],
            "chunk_index": r["chunk_index"],
            "chunk_text": r["chunk_text"],
            "embedding": np.frombuffer(r["embedding"], dtype=np.float32),
        }
        for r in rows
    ]
