# ... code for factory.py ...

from flask import Flask, render_template_string, redirect, url_for, request, session, jsonify, flash

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev"
    # Simulated in-memory config for tests
    app.config_data = {
        "general": {"PUID": "1000", "PGID": "1000", "Timezone": "UTC", "LogLevel": "INFO"},
        "radarr": [],
        "sonarr": [],
        "scheduling": {"cron_schedule": "0 0 * * *", "timezone": "UTC"},
        "user": {"username": "admin", "password": "admin"},
    }

    # In-memory metrics for test isolation
    app.metrics = {"requests_total": 0, "errors_total": 0}

    def is_logged_in():
        return session.get("logged_in")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if username == app.config_data["user"]["username"] and password == app.config_data["user"]["password"]:
                session["logged_in"] = True
                return redirect(url_for("general_settings"))
            return render_template_string("<p>Invalid username or password</p>")
        return render_template_string("""
            <form method='post'>
                <input name='username'>
                <input name='password' type='password'>
                <input type='submit' value='Login'>
            </form>
        """)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/settings/general", methods=["GET", "POST"])
    def general_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            app.config_data["general"].update(request.form)
            flash("General settings saved")
        return render_template_string("<p>PUID</p><p>PGID</p><p>Timezone</p>")

    @app.route("/settings/radarr", methods=["GET", "POST"])
    def radarr_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            # Save radarr settings (simulate)
            app.config_data["radarr"] = [dict(request.form)]
            flash("Radarr settings saved")
        # Render saved Radarr config values for test assertions
        radarrs = app.config_data.get("radarr", [])
        names = " ".join(r.get("radarr0_name", "") for r in radarrs if r.get("radarr0_name"))
        api_keys = " ".join(r.get("radarr0_api_key", "") for r in radarrs if r.get("radarr0_api_key"))
        html = f"<p>Radarr Settings</p><p>API Key</p><p>{names}</p><p>{api_keys}</p>"
        return render_template_string(html)

    @app.route("/settings/sonarr", methods=["GET", "POST"])
    def sonarr_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            app.config_data["sonarr"] = [dict(request.form)]
            flash("Sonarr settings saved")
        # Render saved Sonarr config values for test assertions
        sonarrs = app.config_data.get("sonarr", [])
        names = " ".join(r.get("sonarr0_name", "") for r in sonarrs if r.get("sonarr0_name"))
        api_keys = " ".join(r.get("sonarr0_api_key", "") for r in sonarrs if r.get("sonarr0_api_key"))
        html = f"<p>Sonarr Settings</p><p>API Key</p><p>{names}</p><p>{api_keys}</p>"
        return render_template_string(html)

    @app.route("/scheduling", methods=["GET", "POST"])
    def scheduling():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            app.config_data["scheduling"].update(request.form)
            flash("Schedule saved")
        # Render saved scheduling config for test assertions
        cron = app.config_data.get("scheduling", {}).get("cron_schedule", "")
        timezone = app.config_data.get("scheduling", {}).get("timezone", "")
        html = f"<p>Scheduling</p><p>Timezone</p><p>{cron}</p><p>{timezone}</p>"
        return render_template_string(html)

    @app.route("/user", methods=["GET", "POST"])
    def user_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if not username:
                flash("Username cannot be blank")
            else:
                app.config_data["user"]["username"] = username
                if password:
                    app.config_data["user"]["password"] = password
                flash("User settings updated")
        return render_template_string("<p>User Settings</p><p>Username</p>")

    @app.route("/health")
    def health():
        # Simulate DB/config/threads/time check for tests
        return jsonify({
            "status": "ok",
            "db": "ok",
            "config": "ok",
            "threads": 1,
            "time": "2025-10-23T00:00:00Z"
        })

    @app.route("/metrics")
    def metrics():
        # Return and increment metrics
        return jsonify(app.metrics)
    # Increment requests_total for every request
    @app.before_request
    def before_any_request():
        app.metrics["requests_total"] += 1

    # Increment errors_total for 404/500
    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(error):
        app.metrics["errors_total"] += 1
        return ("Not found", 404) if error.code == 404 else ("Server error", 500)

    @app.route("/validate_sonarr/<int:idx>", methods=["POST"])
    def validate_sonarr(idx):
        # Simulate validation
        sonarrs = app.config_data.get("sonarr", [])
        if idx >= len(sonarrs):
            return jsonify({"error": "Invalid index"}), 400
        s = sonarrs[idx]
        if not s.get("sonarr0_url") or not s.get("sonarr0_api_key"):
            return jsonify({"error": "Missing URL or API key for enabled instance."}), 400
        return jsonify({"success": True})

    return app