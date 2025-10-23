# ... code for webui.py ...

# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates
# Keep route helpers and config management small and testable

import os
import yaml
from werkzeug.security import generate_password_hash

USER_CONFIG_PATH = "config/webui_user.yml"


def load_user_config():
    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    if not os.path.exists(USER_CONFIG_PATH):
        with open(USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(
                {
                    "username": "admin",
                    "password_hash": generate_password_hash("researcharr"),
                },
                f,
            )
    with open(USER_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_user_config(username, password_hash):

    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    with open(USER_CONFIG_PATH, "w") as f:
        yaml.safe_dump(
            {"username": username, "password_hash": password_hash},
            f,
        )
