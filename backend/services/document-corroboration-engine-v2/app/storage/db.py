import os
import json
import sqlite3
from typing import Any, Dict, List, Optional

DB_DIR = os.environ.get("DCEV2_DATA_DIR", "/app/data")
DB_PATH = os.environ.get("DCEV2_DB_PATH", os.path.join(DB_DIR, "dcev2.db"))


def _conn() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS corroborations (
              id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              primary_name TEXT,
              ref_count INTEGER,
              score REAL,
              summary TEXT,
              details TEXT
            )
            """
        )


def save_record(data: Dict[str, Any]) -> None:
    ensure_db()
    details_json = json.dumps(data.get("details_full", {}), ensure_ascii=False)
    with _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO corroborations
            (id, created_at, primary_name, ref_count, score, summary, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["created_at"],
                data.get("primary_name"),
                int(data.get("ref_count", 0)),
                float(data.get("score", 0.0)),
                data.get("summary"),
                details_json,
            ),
        )


def list_records(limit: int = 50) -> List[Dict[str, Any]]:
    ensure_db()
    with _conn() as c:
        cur = c.execute(
            "SELECT id, created_at, primary_name, ref_count, score, summary FROM corroborations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_record(rec_id: str) -> Optional[Dict[str, Any]]:
    ensure_db()
    with _conn() as c:
        cur = c.execute("SELECT * FROM corroborations WHERE id = ?", (rec_id,))
        row = cur.fetchone()
        if not row:
            return None
        out = dict(row)
        try:
            out["details"] = json.loads(out.get("details") or "{}")
        except Exception:
            pass
        return out

