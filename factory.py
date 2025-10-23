from flask import Flask, render_template_string, redirect, url_for, request, session, jsonify

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev"

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if request.form.get("username") == "admin" and request.form.get("password") == "admin":
                session["logged_in"] = True
                return redirect(url_for("general_settings"))
            return render_template_string("<p>Invalid username or password</p>")
        return render_template_string("<form method='post'>Login</form>")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/settings/general")
    def general_settings():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return render_template_string("<p>General Settings</p>")

    @app.route("/settings/radarr", methods=["GET", "POST"])
    def radarr_settings():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return render_template_string("<p>Radarr Settings</p>")

    @app.route("/settings/sonarr", methods=["GET", "POST"])
    def sonarr_settings():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return render_template_string("<p>Sonarr Settings</p>")

    @app.route("/scheduling", methods=["GET", "POST"])
    def scheduling():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return render_template_string("<p>Scheduling</p>")

    @app.route("/user", methods=["GET", "POST"])
    def user_settings():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return render_template_string("<p>User Settings</p>")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/metrics")
    def metrics():
        return jsonify({"requests_total": 1, "errors_total": 0})

    return app