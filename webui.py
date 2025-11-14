# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import os
from types import ModuleType

from werkzeug.security import generate_password_hash

USER_CONFIG_PATH = os.getenv("USER_CONFIG_PATH", "/config/webui_user.yml")

# DB helper import: tests may monkeypatch `webui.rdb` to a fake object with
# load_user/save_user; leave None when import fails.
rdb: ModuleType | None
try:
    from researcharr import db as rdb  # type: ignore
except Exception:
    rdb = None


def _env_bool(name: str, default: str = "false") -> bool:
    """Return True if env var is set to a truthy value (true/1/yes)."""
    v = os.getenv(name, default)
    return str(v).lower() in ("1", "true", "yes")


def load_user_config():
    """Return persisted web UI user dict or None.

    When `rdb` is None, return None so tests expecting absence pass; when
    present delegate to `rdb.load_user()` catching errors.
    """
    if rdb is None:
        return None
    try:
        user = rdb.load_user()
    except Exception:
        return None
    return user


def save_user_config(username, password_hash, api_key=None, api_key_hash=None):
    """Persist user credentials; raise when DB unavailable.

    Hash `api_key` if provided; otherwise use `api_key_hash` verbatim. If
    `rdb` is None raise RuntimeError (tests assert this). Returns the stored
    mapping for convenience when available.
    """
    if rdb is None:
        raise RuntimeError("DB backend not available for saving webui user")
    if api_key is not None:
        api_hash = generate_password_hash(api_key)
    else:
        api_hash = api_key_hash
    rdb.save_user(username, password_hash, api_hash)
    return {"username": username, "password_hash": password_hash, "api_key_hash": api_hash}


__all__ = ["USER_CONFIG_PATH", "_env_bool", "load_user_config", "save_user_config"]
