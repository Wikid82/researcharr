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
        # API immediately. The key is stored alongside the user config.
        api_key = secrets.token_urlsafe(32)
        data = {
            "username": "researcharr",
            "password_hash": password_hash,
            "api_key": api_key,
        }
        with open(USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(data, f)
        # Log the generated plaintext once for operators to copy from logs.
        logger = logging.getLogger("researcharr")
        logger.info(
            "Generated web UI initial password for %s: %s",
            data["username"],
            generated,
        )
        # Return the generated plaintext to the caller so the running app can
        # set its in-memory password for immediate login.
        data["password"] = generated
    with open(USER_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_user_config(username, password_hash, api_key=None):

    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    data = {"username": username, "password_hash": password_hash}
    # Persist the API key if provided (keep existing behaviour when not
    # supplied for backwards compatibility with older callers/tests).
    if api_key is not None:
        data["api_key"] = api_key
    with open(USER_CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f)
