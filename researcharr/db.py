"""Minimal SQLite-backed helper for web UI credentials.

This module stores a single webui user (username, password_hash,
api_key_hash) using sqlite3. It prefers DATABASE_URL when set
"""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Dict, Optional


def _get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite://", "")
    try:
        # Lazy import to avoid cycles during package import
        from researcharr import researcharr as rra

        return getattr(rra, "DB_PATH", "researcharr.db")
    except Exception:
        return os.getenv("RESEARCHARR_DB", "researcharr.db")


def _conn():
    path = _get_db_path()
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        try:
            os.makedirs(dirname, exist_ok=True)
        except Exception:
            pass
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS webui_users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                api_key_hash TEXT,
                created_at INTEGER
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def load_user() -> Optional[Dict[str, Optional[str]]]:
    """Return the first user row as a dict or None if no user exists."""
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT username, password_hash, api_key_hash" " FROM webui_users ORDER BY id LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "username": row["username"],
            "password_hash": row["password_hash"],
            "api_key_hash": row["api_key_hash"],
        }
    finally:
        conn.close()


def save_user(
    username: str,
    password_hash: str,
    api_key_hash: Optional[str] = None,
) -> None:
    """Insert or update the single webui user (id=1 semantics).

    This uses an UPSERT-style pattern to keep the implementation tiny and
    deterministic for single-user usage.
    """
    init_db()
    conn = get_connection()
    try:
        now = int(time.time())
        cur = conn.cursor()
        # Try update first; if no rows updated, insert.
        cur.execute(
            "UPDATE webui_users SET username = ?, password_hash = ?,"
            " api_key_hash = ? WHERE id = 1",
            (username, password_hash, api_key_hash),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO webui_users (id, username, password_hash,"
                " api_key_hash, created_at) VALUES (1, ?, ?, ?, ?)",
                (username, password_hash, api_key_hash, now),
            )
        conn.commit()
    finally:
        conn.close()


# Backward-compatible wrappers / aliases for test compatibility
def get_user_by_username(username: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
    """Return the first user row.

    Historically tests call `get_user_by_username(username)` even though the
    implementation stores a single user. Accept an optional username argument
    for compatibility and delegate to the single-user loader.
    """
    return load_user()


create_tables = init_db
get_connection = _conn
create_user = save_user
