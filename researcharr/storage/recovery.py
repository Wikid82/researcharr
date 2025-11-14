"""Recovery and compatibility helpers for database backups."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory


def get_alembic_head_revision() -> str | None:
    """Return the repository head revision string, if available."""
    try:
        repo_root = Path(__file__).parent.parent.parent
        alembic_ini = repo_root / "alembic.ini"
        if not alembic_ini.exists():
            return None
        cfg = Config(str(alembic_ini))
        script = ScriptDirectory.from_config(cfg)
        return script.get_current_head()
    except Exception:
        return None


def suggest_image_tag_from_meta(meta: dict[str, Any] | None) -> str | None:
    """Given backup metadata, suggest a container image tag to use.

    Prefers an explicit app_version field if present, otherwise returns None.
    """
    try:
        if not meta:
            return None
        ver = meta.get("app_version")
        return f"ghcr.io/wikid82/researcharr:{ver}" if ver else None
    except Exception:
        return None


def read_backup_meta(backup_zip_path: str | Path) -> dict[str, Any] | None:
    """Read backup_meta.json from a backup zip if present."""
    try:
        import zipfile

        with zipfile.ZipFile(str(backup_zip_path), "r") as zf:
            try:
                raw = zf.read("backup_meta.json")
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return None
    except Exception:
        return None


def check_db_integrity(db_path: str | Path) -> bool:
    """Run PRAGMA integrity_check on a SQLite file."""
    try:
        import sqlite3

        con = sqlite3.connect(str(db_path))
        try:
            cur = con.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            return bool(row and row[0] == "ok")
        finally:
            con.close()
    except Exception:
        return False


def snapshot_sqlite(db_path: str | Path, out_path: str | Path) -> bool:
    """Create a hot copy snapshot of a SQLite DB file to out_path."""
    try:
        import sqlite3

        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(out_path))
        try:
            src.backup(dst)
            return True
        finally:
            dst.close()
            src.close()
    except Exception:
        return False
