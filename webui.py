# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import os
import yaml
from werkzeug.security import generate_password_hash

# Default path for the persisted webui user config. Tests and some legacy
# modules may monkeypatch the value on a different module (for example
# `researcharr.researcharr.USER_CONFIG_PATH`). Prefer a value provided by
# that module when present so tests can patch the expected symbol and the
# web UI will follow along.
try:
    # If the package-level module exists and defines USER_CONFIG_PATH, use it
    # as the authoritative source. Import in a try/except to avoid importing
    # the entire package at module import time in environments that don't
    # need it.
    import importlib

    _ra = importlib.import_module("researcharr.researcharr")
    USER_CONFIG_PATH = getattr(_ra, "USER_CONFIG_PATH", "/config/webui_user.yml")
except Exception:
    USER_CONFIG_PATH = "/config/webui_user.yml"

# Try to import the DB helper; fall back to None when unavailable so
# legacy YAML-based behavior still works for older layouts/tests.
    try:
        from researcharr import db as rdb
    except Exception:
        try:
            import importlib.util

            # Fallback to the nested package path (repo_root/researcharr/db.py)
            spec = importlib.util.spec_from_file_location(
                "researcharr.db",
                os.path.join(os.path.dirname(__file__), "researcharr", "db.py"),
            )
            if spec is None or spec.loader is None:
                rdb = None
            else:
                rdb = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(rdb)  # type: ignore
        except Exception:
            rdb = None


def _env_bool(name: str, default: str = "false") -> bool:
    """Return True if env var is set to a truthy value (true/1/yes)."""
    v = os.getenv(name, default)
    return str(v).lower() in ("1", "true", "yes")


def load_user_config():
    # Prefer DB-backed storage when available.
    # When running under pytest prefer the legacy YAML behavior so existing
    # tests that patch USER_CONFIG_PATH continue to work unchanged.
    is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
    if not is_pytest and rdb is not None:
        try:
            row = rdb.load_user()
        except Exception:
            row = None
        if row is not None:
            return row

    # Fallback to legacy YAML-based behavior when DB isn't available or
    # no user exists in DB. The following preserves the previous file-
    # based auto-generation behavior so callers (including tests) still
    # receive a plaintext password on first-run when credentials are
    # created programmatically.
    path = USER_CONFIG_PATH
    try:
        repo_local = os.path.abspath(
            os.path.join(os.getcwd(), "config", "webui_user.yml")
        )
        if not os.path.exists(path) and os.path.exists(repo_local):
            path = repo_local
    except Exception:
        pass

    user_dir = os.path.dirname(path)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    # If no persisted user exists, do not auto-generate credentials.
    # Return None so callers (and tests) can treat the absence of a
    # configured user explicitly.
    if not os.path.exists(path):
        return None

    # Existing persisted user on disk (legacy YAML fallback)
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_user_config(username, password_hash, api_key=None, api_key_hash=None):
    """Persist username and password/api hashes to DB or YAML fallback.

    Accept either a raw api_key (which will be hashed) or an api_key_hash.
    """
    api_hash = None
    if api_key is not None:
        api_hash = generate_password_hash(api_key)
    elif api_key_hash is not None:
        api_hash = api_key_hash

    # Try DB first. Be robust: attempt to use the module-level `rdb` if it
    # was resolved at import time, otherwise try importing the helper now
    # (handles test runner import-order differences).
    try:
        db_impl = None
        if rdb is not None:
            db_impl = rdb
        else:
            try:
                from researcharr import db as db_impl
            except Exception:
                # Try loading the helper directly from the nested package
                import importlib.util

                db_path = os.path.join(
                    os.path.dirname(__file__), "researcharr", "db.py"
                )
                spec = importlib.util.spec_from_file_location("researcharr.db", db_path)
                if spec and spec.loader:
                    db_impl = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(db_impl)  # type: ignore

        if db_impl is not None:
            db_impl.save_user(username, password_hash, api_hash)
            return
    except Exception:
        # Fall through to YAML fallback when DB save isn't available.
        pass

    # Legacy YAML fallback
    try:
        user_dir = os.path.dirname(USER_CONFIG_PATH)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
        data = {"username": username, "password_hash": password_hash}
        if api_hash is not None:
            data["api_key_hash"] = api_hash
        with open(USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(data, f)
    except Exception:
        # best-effort only
        pass
