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
    local_fallback = os.path.abspath(
        os.path.join(os.getcwd(), "config", "webui_user.yml")
    )
    # Only use the repo-local fallback when the configured USER_CONFIG_PATH
    # is the default '/config/webui_user.yml'. If USER_CONFIG_PATH was set by
    # tests or explicitly by the operator, respect that path.
    if path == "/config/webui_user.yml" and os.path.exists(local_fallback):
        path = local_fallback

    user_dir = os.path.dirname(path)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    if not os.path.exists(path):
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
        # Decide whether to print/log plaintext credentials. By default
        # this is disabled; set WEBUI_DEV_DEBUG=true or
        # WEBUI_DEV_PRINT_CREDS=true to enable in development.
        # Always emit an informational log entry that initial credentials
        # were generated so test harnesses and operators can detect first-run
        # events. Printing the plaintext credentials to stdout is optional
        # and controlled by WEBUI_DEV_PRINT_CREDS / WEBUI_DEV_DEBUG.
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
            # Also print the plaintext to stdout so it's visible in container logs.
            try:
                print(
                    "Generated web UI initial credentials -> "
                    f"username: {data['username']} password: {generated} "
                    f"api_token: {api_token}"
                )
            except Exception:
                # If printing fails, ignore; the hash was persisted.
                pass
        # Return the generated plaintext to the caller so the running app can
        # set its in-memory password for immediate login. Also include the
        # plaintext API token so the operator can copy it once (we persist
        # only the hash to disk).
        data["password"] = generated
        data["api_key"] = api_token
        # Return the generated plaintext values to the caller so the
        # application can set in-memory credentials for immediate login.
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
