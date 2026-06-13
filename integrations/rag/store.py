"""SQLite FTS5 — локальный RAG без внешних зависимостей."""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Optional

_lock = threading.Lock()
_store: Optional["RagStore"] = None

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rag", "knowledge.db")


class RagStore:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS rag_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                    CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
                        agent_id UNINDEXED,
                        title,
                        content,
                        keywords,
                        source UNINDEXED,
                        pack_id UNINDEXED,
                        tokenize='unicode61'
                    );
                    CREATE TABLE IF NOT EXISTS rag_vec (
                        chunk_id INTEGER PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        title TEXT,
                        content TEXT,
                        embedding BLOB NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_rag_vec_agent ON rag_vec(agent_id);
                """)
                conn.commit()
            finally:
                conn.close()

    def clear_agent(self, agent_id: str) -> int:
        with _lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM rag_vec WHERE agent_id = ?", (agent_id,))
                cur = conn.execute(
                    "DELETE FROM rag_fts WHERE agent_id = ?", (agent_id,)
                )
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()

    def clear_all(self) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM rag_fts")
                conn.execute("DELETE FROM rag_vec")
                conn.commit()
            finally:
                conn.close()

    def clear_vectors(self) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM rag_vec")
                conn.commit()
            finally:
                conn.close()

    def add_entry(
        self,
        agent_id: str,
        title: str,
        content: str,
        keywords: str = "",
        source: str = "pack",
        pack_id: str = "v1",
    ) -> int:
        title = (title or "").strip()
        content = (content or "").strip()
        if not title and not content:
            return 0
        with _lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """INSERT INTO rag_fts(agent_id, title, content, keywords, source, pack_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (agent_id, title, content, keywords, source, pack_id),
                )
                chunk_id = cur.lastrowid
                conn.commit()
                return chunk_id
            finally:
                conn.close()

    def set_embedding(self, chunk_id: int, agent_id: str, title: str, content: str, embedding: bytes) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO rag_vec(chunk_id, agent_id, title, content, embedding)
                       VALUES (?, ?, ?, ?, ?)""",
                    (chunk_id, agent_id, title, content, embedding),
                )
                conn.commit()
            finally:
                conn.close()

    def vector_search(self, agent_id: str, query_embedding: list[float], limit: int = 8) -> list[dict]:
        from integrations.rag.embeddings import blob_to_embedding, cosine_similarity, embedding_to_blob
        qblob = embedding_to_blob(query_embedding)
        with _lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT chunk_id, agent_id, title, content, embedding FROM rag_vec WHERE agent_id = ?",
                    (agent_id,),
                ).fetchall()
            finally:
                conn.close()
        scored = []
        for r in rows:
            vec = blob_to_embedding(r["embedding"])
            sim = cosine_similarity(query_embedding, vec)
            scored.append({
                "title": r["title"],
                "content": r["content"],
                "score": sim,
                "vector_score": sim,
                "chunk_id": r["chunk_id"],
            })
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    def list_fts_chunks(self, agent_id: str = None, limit: int = 5000) -> list[dict]:
        with _lock:
            conn = self._connect()
            try:
                if agent_id:
                    rows = conn.execute(
                        """SELECT rowid AS chunk_id, agent_id, title, content, keywords, source, pack_id
                           FROM rag_fts WHERE agent_id = ? LIMIT ?""",
                        (agent_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT rowid AS chunk_id, agent_id, title, content, keywords, source, pack_id
                           FROM rag_fts LIMIT ?""",
                        (limit,),
                    ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def count_vectors(self) -> int:
        with _lock:
            conn = self._connect()
            try:
                return conn.execute("SELECT COUNT(*) FROM rag_vec").fetchone()[0]
            finally:
                conn.close()

    def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 8,
    ) -> list[dict]:
        q = (query or "").strip()
        if not q:
            return []
        # FTS5: escape quotes, build OR query from words
        words = [w for w in q.replace('"', " ").split() if len(w) >= 2][:12]
        if not words:
            words = [q[:40]]
        fts_q = " OR ".join(f'"{w}"' for w in words)

        with _lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT title, content, keywords, source, pack_id,
                           bm25(rag_fts) AS score
                    FROM rag_fts
                    WHERE agent_id = ? AND rag_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (agent_id, fts_q, limit),
                ).fetchall()
                if rows:
                    return [dict(r) for r in rows]
                # Fallback: LIKE search
                like = f"%{words[0]}%"
                rows = conn.execute(
                    """
                    SELECT title, content, keywords, source, pack_id, 0 AS score
                    FROM rag_fts
                    WHERE agent_id = ? AND (content LIKE ? OR title LIKE ? OR keywords LIKE ?)
                    LIMIT ?
                    """,
                    (agent_id, like, like, like, limit),
                ).fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                return []
            finally:
                conn.close()

    def stats(self) -> dict:
        with _lock:
            conn = self._connect()
            try:
                total = conn.execute("SELECT COUNT(*) FROM rag_fts").fetchone()[0]
                by_agent = conn.execute(
                    "SELECT agent_id, COUNT(*) AS n FROM rag_fts GROUP BY agent_id ORDER BY n DESC"
                ).fetchall()
                meta = {}
                for row in conn.execute("SELECT key, value FROM rag_meta"):
                    meta[row[0]] = row[1]
                vec_count = conn.execute("SELECT COUNT(*) FROM rag_vec").fetchone()[0]
                return {
                    "total_chunks": total,
                    "vector_chunks": vec_count,
                    "by_agent": {r["agent_id"]: r["n"] for r in by_agent},
                    "db_path": self.db_path,
                    "meta": meta,
                }
            finally:
                conn.close()

    def set_meta(self, key: str, value: str) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO rag_meta(key, value) VALUES (?, ?)",
                    (key, value),
                )
                conn.commit()
            finally:
                conn.close()


def get_store() -> RagStore:
    global _store
    if _store is None:
        import config as cfg
        path = cfg.config.get("rag_db_path") or DEFAULT_DB
        _store = RagStore(path)
    return _store
