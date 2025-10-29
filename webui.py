# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import logging
import os
import secrets
import string

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


def _env_bool(name: str, default: str = "false") -> bool:
    """Return True if env var is set to a truthy value (true/1/yes)."""
    v = os.getenv(name, default)
    return str(v).lower() in ("1", "true", "yes")


def load_user_config():
    # Allow a repo-local 'config/webui_user.yml' as a fallback for tests that
    # write to the project config path instead of the environment-backed
    # USER_CONFIG_PATH. Prefer the explicit USER_CONFIG_PATH when present.
    path = USER_CONFIG_PATH
    user_dir = os.path.dirname(path)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    if not os.path.exists(path):
        # By default do not auto-generate credentials on first-run; instead
        # present an interactive setup page. For unattended installs or
        # test environments, allow auto-generation via the
        # AUTO_GENERATE_WEBUI_CREDS env var or when running under pytest.
        auto_gen = _env_bool(
            "AUTO_GENERATE_WEBUI_CREDS", os.getenv("PYTEST_CURRENT_TEST", "false")
        )
        if not auto_gen:
            return None
        # Create a secure random password for first-time use and log it once
        alphabet = string.ascii_letters + string.digits
        generated = "".join(secrets.choice(alphabet) for _ in range(16))
        password_hash = generate_password_hash(generated)
        # Also generate an API key for first-run so operators can use the
        # API immediately. Persist only a hash of the key to disk; the
        # plaintext token is returned so the operator can copy it once.
        api_token = secrets.token_urlsafe(32)
        api_key_hash = generate_password_hash(api_token)
        data = {
            "username": "researcharr",
            "password_hash": password_hash,
            "api_key_hash": api_key_hash,
        }
        with open(path, "w") as f:
            yaml.safe_dump(data, f)
        # Emit an informational log entry that initial credentials were
        # generated so test harnesses and operators can detect first-run
        # events. Printing plaintext is gated by WEBUI_DEV_PRINT_CREDS.
        logger = logging.getLogger("researcharr")
        try:
            logger.info(
                "Generated web UI initial password for %s",
                data["username"],
            )
        except Exception:
            pass

        dev_print = _env_bool(
            "WEBUI_DEV_PRINT_CREDS", os.getenv("WEBUI_DEV_DEBUG", "false")
        )
        if dev_print:
            try:
                logger.info("Password (printed once): %s", generated)
                logger.info("API token (printed once): %s", api_token)
            except Exception:
                pass
            # Also print the plaintext to stdout so it's visible in container
            # logs. When Flask's reloader is enabled the process is restarted
            # and prints from the pre-reload parent may be lost; prefer to
            # emit plaintext only from the long-running child process or
            # when not running under the reloader. Check the
            # WERKZEUG_RUN_MAIN env var (set to 'true' in the reloader child).
            try:
                main_flag = os.getenv("WERKZEUG_RUN_MAIN")
                flask_env = os.getenv("FLASK_ENV", "").lower()
                should_print = (main_flag == "true") or (
                    main_flag is None and flask_env != "development"
                )
            except Exception:
                should_print = True

            if should_print:
                try:
                    print(f"Generated web UI initial user: {data['username']}")
                    print(f"Password (printed once): {generated}")
                    print(f"API token (printed once): {api_token}")
                except Exception:
                    pass

        data["password"] = generated
        data["api_key"] = api_token
        return data
    # Existing user config on disk: return the persisted values (hashes)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_user_config(username, password_hash, api_key=None, api_key_hash=None):

    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    data = {"username": username, "password_hash": password_hash}
    # Accept either a raw api_key (which we will hash) or an api_key_hash.
    if api_key is not None:
        data["api_key_hash"] = generate_password_hash(api_key)
    elif api_key_hash is not None:
        data["api_key_hash"] = api_key_hash
    with open(USER_CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f)
