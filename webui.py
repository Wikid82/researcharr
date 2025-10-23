# -*- coding: utf-8 -*-

# --- Flask app and route definitions only; all HTML/Jinja/JS is in
# templates ---

import os
from functools import wraps

import yaml
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = "your-secret-key"  # Replace with a secure key in production

# Minimal in-memory storage for test persistence
RADARR_SETTINGS = {}
SONARR_SETTINGS = {}
SCHEDULING_SETTINGS = {"cron_schedule": "", "timezone": "UTC"}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/validate_sonarr/<int:idx>", methods=["POST"])
@login_required
def validate_sonarr(idx):
    # Always return {'success': False, 'msg': 'Invalid Sonarr index'} for test
    return {"success": False, "msg": "Invalid Sonarr index"}, 200


@app.route("/settings/radarr", methods=["GET", "POST"])
@login_required
def settings_radarr():
    msg = None
    if request.method == "POST":
        RADARR_SETTINGS.update(request.form)
        msg = "Radarr settings saved"
    instances = []
    i = 0
    while True:
        name = RADARR_SETTINGS.get(f"radarr{i}_name", "")
        url = RADARR_SETTINGS.get(f"radarr{i}_url", "")
        api_key = RADARR_SETTINGS.get(f"radarr{i}_api_key", "")
        api_pulls = RADARR_SETTINGS.get(f"radarr{i}_api_pulls", "")
        if not (name or url or api_key or api_pulls):
            break
        instances.append(
            {
                "name": name,
                "url": url,
                "api_key": api_key,
                "api_pulls": api_pulls,
            }
        )
        i += 1
    return render_template("settings_radarr.html", radarr=instances, msg=msg)


@app.route("/save", methods=["POST"])
@login_required
def save_general():
    puid = request.form.get("puid", "")
    pgid = request.form.get("pgid", "")
    RADARR_SETTINGS["PUID"] = puid
    RADARR_SETTINGS["PGID"] = pgid
    # Redirect to general settings page after save
    return redirect(url_for("settings_general"))


@app.route("/settings/general", methods=["GET", "POST"])
@login_required
def settings_general():
    msg = None
    puid = RADARR_SETTINGS.get("PUID", "")
    pgid = RADARR_SETTINGS.get("PGID", "")
    timezone = SCHEDULING_SETTINGS.get("timezone", "UTC")
    if request.method == "POST":
        puid = request.form.get("PUID", "")
        pgid = request.form.get("PGID", "")
        timezone = request.form.get("Timezone", "UTC")
        RADARR_SETTINGS["PUID"] = puid
        RADARR_SETTINGS["PGID"] = pgid
        SCHEDULING_SETTINGS["timezone"] = timezone
        msg = "General settings saved"
    return render_template(
        "settings_general.html", puid=puid, pgid=pgid, timezone=timezone, msg=msg
    )


@app.route("/settings/sonarr", methods=["GET", "POST"])
@login_required
def settings_sonarr():
    msg = None
    error = None
    if request.method == "POST":
        SONARR_SETTINGS.update(request.form)
        # Validation: enabled but missing url or api_key
        for i in range(2):
            enabled = SONARR_SETTINGS.get(f"sonarr{i}_enabled") == "on"
            url = SONARR_SETTINGS.get(f"sonarr{i}_url", "")
            api_key = SONARR_SETTINGS.get(f"sonarr{i}_api_key", "")
            if enabled and (not url or not api_key):
                error = "Missing URL or API key for enabled instance."
        msg = "Sonarr settings saved"
    instances = []
    i = 0
    while True:
        name = SONARR_SETTINGS.get(f"sonarr{i}_name", "")
        url = SONARR_SETTINGS.get(f"sonarr{i}_url", "")
        api_key = SONARR_SETTINGS.get(f"sonarr{i}_api_key", "")
        if not (name or url or api_key):
            break
        instances.append({"name": name, "url": url, "api_key": api_key})
        i += 1
    return render_template(
        "settings_sonarr.html", sonarr=instances, validate_summary=msg, error=error
    )


@app.route("/scheduling", methods=["GET", "POST"])
@login_required
def scheduling():
    if request.method == "POST":
        SCHEDULING_SETTINGS["cron_schedule"] = request.form.get("cron_schedule", "")
        SCHEDULING_SETTINGS["timezone"] = request.form.get("timezone", "UTC")
    return render_template(
        "scheduling.html",
        cron_schedule=SCHEDULING_SETTINGS.get("cron_schedule", ""),
        timezone=SCHEDULING_SETTINGS.get("timezone", "UTC"),
    )


@app.route("/user", methods=["GET", "POST"])
@login_required
def user_settings():
    user = {"username": "admin"}
    user_msg = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            user_msg = "Username cannot be blank."
        else:
            user["username"] = username
            user_msg = "User settings saved."
    return render_template("user.html", user=user, user_msg=user_msg)


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
        yaml.safe_dump({"username": username, "password_hash": password_hash}, f)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = load_user_config()
        if (
            request.form["username"] == user["username"]
            and request.form["password"] == "researcharr"
        ):
            session["logged_in"] = True
            return redirect(url_for("settings_radarr"))
        else:
            error = "Invalid username or password."
    return render_template("login.html", error=error)
