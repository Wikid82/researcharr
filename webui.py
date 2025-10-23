
# -*- coding: utf-8 -*-
# --- Flask app and route definitions only; all HTML/Jinja/JS is in templates ---

import time
import os

USER_CONFIG_PATH = "config/webui_user.yml"

        yaml.safe_dump({"username": username, "password_hash": password_hash}, f)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        url = RADARR_SETTINGS.get(f"radarr{i}_url", "")
        api_key = RADARR_SETTINGS.get(f"radarr{i}_api_key", "")
        api_pulls = RADARR_SETTINGS.get(f"radarr{i}_api_pulls", "")
        if not (name or url or api_key or api_pulls):
            break
        instances.append(
            {
                "name": name,

        USER_CONFIG_PATH = "config/webui_user.yml"

    puid = request.form.get("puid", "")
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

    pgid = request.form.get("pgid", "")
            user_dir = os.path.dirname(USER_CONFIG_PATH)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
            with open(USER_CONFIG_PATH, "w") as f:
                yaml.safe_dump({"username": username, "password_hash": password_hash}, f)

    RADARR_SETTINGS["PUID"] = puid
    RADARR_SETTINGS["PGID"] = pgid
    # Redirect to general settings page after save
    return redirect(url_for("settings_general"))





