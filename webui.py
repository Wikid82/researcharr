# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import os

from werkzeug.security import generate_password_hash

# The application now uses DB-backed storage for web UI users exclusively.
# Import the DB helper from the package. If import fails, set `rdb` to None
# so callers can handle the absence (tests/CI should supply a DB via
# `researcharr.researcharr.DB_PATH` or `DATABASE_URL`).
try:
    from researcharr import db as rdb
except Exception:
    rdb = None


def _env_bool(name: str, default: str = "false") -> bool:
    """Return True if env var is set to a truthy value (true/1/yes)."""
    v = os.getenv(name, default)
    return str(v).lower() in ("1", "true", "yes")


def load_user_config():
    """Return the persisted web UI user dict from the DB or None.

    This function no longer reads from any YAML file. Tests and CI should
    ensure a DB is available (conftest sets `researcharr.researcharr.DB_PATH`).
    """
    if rdb is None:
        return None
    try:
        return rdb.load_user()
    except Exception:
        return None


def save_user_config(username, password_hash, api_key=None, api_key_hash=None):
    """Persist username and password/api hashes to the DB.

    Accept either a raw api_key (which will be hashed) or an api_key_hash.
    Raises RuntimeError when no DB backend is available.
    """
    api_hash = None
    if api_key is not None:
        api_hash = generate_password_hash(api_key)
    elif api_key_hash is not None:
        api_hash = api_key_hash

    if rdb is None:
        raise RuntimeError("DB backend not available for saving webui user")
    rdb.save_user(username, password_hash, api_hash)
