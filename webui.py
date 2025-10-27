# ... code for webui.py ...

# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import logging
import os
import secrets
import string

import yaml
from werkzeug.security import generate_password_hash

USER_CONFIG_PATH = "/config/webui_user.yml"


def load_user_config():
    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    if not os.path.exists(USER_CONFIG_PATH):
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
        with open(USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(data, f)
        # Log and print the generated plaintext once for operators to copy from logs.
        # Printing ensures the plaintext appears in container stdout/stderr even when
        # logging configuration may default to higher levels or write elsewhere.
        logger = logging.getLogger("researcharr")
        try:
            logger.info(
                "Generated web UI initial password for %s",
                data["username"],
            )
            logger.info("Password (printed once): %s", generated)
            logger.info("API token (printed once): %s", api_token)
        except Exception:
            # Best-effort logging; continue to print directly.
            pass
        # Also print the plaintext to stdout so it's visible in container logs.
        try:
            print(f"Generated web UI initial credentials -> username: {data['username']} password: {generated} api_token: {api_token}")
        except Exception:
            # If printing fails for any reason, ignore — we still persisted the hash.
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
    with open(USER_CONFIG_PATH, "r") as f:
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
