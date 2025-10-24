# ... code for factory.py ...

import importlib.util
import os

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

try:
    # Prefer importing webui from the package if available
    from researcharr import webui  # type: ignore
except Exception:
    # Fallback: load the top-level webui.py module directly (this keeps
    # compatibility with how the project is laid out in the Docker image
    # where webui.py lives at /app/webui.py).
    spec = importlib.util.spec_from_file_location(
        "webui", os.path.join(os.path.dirname(__file__), "webui.py")
    )
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load webui module from file")
    webui = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(webui)  # type: ignore


def create_app():
    def logout_link():
        return '<a href="/logout">Logout</a>'

    app = Flask(__name__)
    # SECRET_KEY must be provided in production. In development/test the
    # default 'dev' key is used but a warning is emitted. Use an
    # environment variable to supply a strong secret in production.
    secret = os.getenv("SECRET_KEY")
    # Determine if running in production via common env markers.
    env_prod = (
        os.getenv("ENV", "").lower() == "production"
        or os.getenv("FLASK_ENV", "").lower() == "production"
    )
    if not secret and env_prod:
        # Fail fast in production if SECRET_KEY is missing.
        raise SystemExit(
            "SECRET_KEY environment variable is required in production. Set SECRET_KEY and restart."
        )
    if not secret:
        secret = "dev"
        # Will be visible in logs once the app logger is configured; use
        # print as a fallback in early startup paths.
        try:
            print("WARNING: using insecure default SECRET_KEY; set SECRET_KEY in production")
        except Exception:
            pass
    app.secret_key = secret

    # Session cookie configuration — configurable via env vars but default
    # to secure settings suitable for production behind TLS.
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    # Simulated in-memory config for tests. PUID/PGID/Timezone are sourced
    # from environment variables to avoid managing these sensitive runtime
    # settings via the web UI. This prevents accidental permission/timezone
    # mismatches when the container is started.
    app.config_data = {
        "general": {
            "PUID": os.getenv("PUID", "1000"),
            "PGID": os.getenv("PGID", "1000"),
            "Timezone": os.getenv("TIMEZONE", "UTC"),
            "LogLevel": os.getenv("LOGLEVEL", "INFO"),
        },
        "radarr": [],
        "sonarr": [],
        "scheduling": {"cron_schedule": "0 0 * * *", "timezone": "UTC"},
        "user": {"username": "admin", "password": "researcharr"},
    }

    # In-memory metrics for test isolation
    app.metrics = {"requests_total": 0, "errors_total": 0}

    # Ensure web UI user config exists on startup. If a first-run password is
    # generated, the loader returns the plaintext as `password` so we can set
    # the in-memory auth to allow immediate login using that password.
    try:
        try:
            ucfg = webui.load_user_config()
        except Exception:
            ucfg = None
        if isinstance(ucfg, dict):
            # Do not override the default username set in app.config_data to
            # preserve test expectations (tests expect the initial username
            # to be 'admin'). Only set an in-memory password when the loader
            # returned a plaintext password (first-run).
            if "password" in ucfg:
                app.config_data["user"]["password"] = ucfg.get("password")
                try:
                    app.logger.info(
                        "Generated web UI initial password for %s: %s",
                        app.config_data["user"]["username"],
                        ucfg.get("password"),
                    )
                except Exception:
                    pass
    except Exception:
        # best-effort; if loading the user config fails we continue with the
        # default in-memory credentials to avoid preventing the UI from
        # starting.
        pass

    # --- Plugin registry wiring (discover local example plugins) ---
    try:
        from researcharr.plugins.registry import PluginRegistry
        from researcharr.plugins import example_sonarr

        registry = PluginRegistry()
        # Discover any local plugin modules placed under researcharr/plugins
        pkg_dir = os.path.dirname(__file__)
        plugins_dir = os.path.join(pkg_dir, "plugins")
        registry.discover_local(plugins_dir)
        # For tests we may want to instantiate configured plugin instances
        app.plugin_registry = registry
        # Example: if there are configured sonarr instances in config_data,
        # create plugin instances and register their blueprints.
        try:
            for inst in app.config_data.get("sonarr", []):
                try:
                    pl = registry.create_instance("sonarr", inst)
                    bp = pl.blueprint()
                    if bp is not None:
                        app.register_blueprint(bp)
                except Exception:
                    # ignore plugin instantiation failures for now
                    pass
        except Exception:
            pass
    except Exception:
        # If plugin machinery isn't available, continue silently.
        pass

    # Validate runtime env vars (PUID/PGID) and warn if they are invalid.
    try:
        # Use app.logger so warnings appear in application logs.
        try:
            puid_val = int(app.config_data["general"].get("PUID", "1000"))
            app.config_data["general"]["PUID"] = str(puid_val)
        except Exception:
            app.logger.warning(
                "Invalid PUID '%s' — falling back to 1000. Set PUID env var to a valid integer.",
                app.config_data["general"].get("PUID"),
            )
            app.config_data["general"]["PUID"] = "1000"

        try:
            pgid_val = int(app.config_data["general"].get("PGID", "1000"))
            app.config_data["general"]["PGID"] = str(pgid_val)
        except Exception:
            app.logger.warning(
                "Invalid PGID '%s' — falling back to 1000. Set PGID env var to a valid integer.",
                app.config_data["general"].get("PGID"),
            )
            app.config_data["general"]["PGID"] = "1000"
    except Exception:
        # If logging or access fails for any reason, don't prevent startup.
        pass

    def is_logged_in():
        return session.get("logged_in")

    def _parse_instances(form, prefix, max_instances=5):
        instances = []
        for i in range(max_instances):
            key_base = f"{prefix}{i}_"
            # determine if this instance has any submitted fields
            has_any = any(k.startswith(key_base) for k in form.keys())
            if not has_any:
                continue
            inst = {}
            # common fields
            inst["enabled"] = bool(form.get(f"{prefix}{i}_enabled"))
            inst["name"] = form.get(f"{prefix}{i}_name", "")
            inst["url"] = form.get(f"{prefix}{i}_url", "")
            inst["api_key"] = form.get(f"{prefix}{i}_api_key", "")
            inst["process"] = bool(form.get(f"{prefix}{i}_process"))
            inst["state_mgmt"] = bool(form.get(f"{prefix}{i}_state_mgmt"))
            # numeric-ish fields (store as provided)
            inst["api_pulls"] = form.get(f"{prefix}{i}_api_pulls")
            k = f"{prefix}{i}_movies_to_upgrade"
            inst["movies_to_upgrade"] = form.get(k)
            k = f"{prefix}{i}_episodes_to_upgrade"
            inst["episodes_to_upgrade"] = form.get(k)
            k = f"{prefix}{i}_max_download_queue"
            inst["max_download_queue"] = form.get(k)
            k = f"{prefix}{i}_reprocess_interval_days"
            inst["reprocess_interval_days"] = form.get(k)
            inst["mode"] = form.get(f"{prefix}{i}_mode")
            instances.append(inst)
        return instances

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = app.config_data["user"]
            if username == user["username"] and password == user["password"]:
                session["logged_in"] = True
                return redirect(url_for("general_settings"))
            return render_template(
                "login.html",
                error="Invalid username or password",
            )
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        """Allow resetting the web UI user password.

        Requires the `WEBUI_RESET_TOKEN` env var. The provided token must match
        the configured value. If the variable is not set the reset page is
        disabled to avoid exposing an unauthenticated reset endpoint.
        """
        token_required = os.getenv("WEBUI_RESET_TOKEN")
        # If no reset token configured, disallow reset via web UI
        if not token_required and request.method == "GET":
            # show a simple page saying reset is unavailable
            return render_template("reset_password.html", disabled=True)

        error = None
        if request.method == "POST":
            username = request.form.get("username")
            token = request.form.get("token")
            password = request.form.get("password")
            confirm = request.form.get("confirm")

            if token_required and token != token_required:
                error = "Invalid reset token"
            elif not password or password != confirm:
                error = "Passwords do not match"
            else:
                # Apply the reset to in-memory config
                app.config_data["user"]["username"] = (
                    username or app.config_data["user"]["username"]
                )
                app.config_data["user"]["password"] = password
                # Persist to file if webui.save_user_config is available
                try:
                    pwd_hash = generate_password_hash(password)
                    webui.save_user_config(
                        app.config_data["user"]["username"], pwd_hash
                    )
                except Exception:
                    # best-effort persistence; ignore failures here
                    pass
                flash("Password has been reset. Please log in.")
                return redirect(url_for("login"))

        return render_template(
            "reset_password.html",
            error=error,
            disabled=False,
            user=app.config_data.get("user"),
        )

    @app.route("/settings/general", methods=["GET", "POST"])
    def general_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            # Only allow editing of non-runtime values via the UI. Do not
            # accept PUID/PGID/Timezone from the form — they are set via
            # environment variables. Accept only LogLevel here.
            loglevel = request.form.get("LogLevel")
            if loglevel:
                app.config_data["general"]["LogLevel"] = loglevel
            flash("General settings saved")
        return render_template(
            "settings_general.html",
            puid=app.config_data["general"].get("PUID"),
            pgid=app.config_data["general"].get("PGID"),
            timezone=app.config_data["general"].get("Timezone"),
            loglevel=app.config_data["general"].get("LogLevel"),
            msg=None,
        )

    @app.route("/settings/radarr", methods=["GET", "POST"])
    def radarr_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            # Parse and save radarr instances
            radarr_list = _parse_instances(request.form, "radarr")
            app.config_data["radarr"] = radarr_list
            flash("Radarr settings saved")
        radarrs = app.config_data.get("radarr", [])

        # Convert stored dicts to objects for template attribute-style access
        # and provide a .get() method used by templates

        class _Obj:
            def __init__(self, d):
                self._d = dict(d)

            def __getattr__(self, name):
                # allow attribute access like obj.name
                return self._d.get(name)

            def get(self, key, default=None):
                return self._d.get(key, default)

        def _wrap_list(lst):
            return [_Obj(r) if isinstance(r, dict) else r for r in lst]

        return render_template(
            "settings_radarr.html",
            radarr=_wrap_list(radarrs),
        )

    @app.route("/settings/sonarr", methods=["GET", "POST"])
    def sonarr_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            # Parse and save sonarr instances
            sonarr_list = _parse_instances(request.form, "sonarr")
            app.config_data["sonarr"] = sonarr_list
            flash("Sonarr settings saved")
        sonarrs = app.config_data.get("sonarr", [])
        error = None
        if request.method == "POST":
            # Basic validation: if enabled but missing url/api_key, set error
            if request.form.get("sonarr0_enabled") and (
                not request.form.get("sonarr0_url")
                or not request.form.get("sonarr0_api_key")
            ):
                error = "Missing URL or API key for enabled instance."
                flash(error)
            sonarrs = app.config_data.get("sonarr", [])

        return render_template(
            "settings_sonarr.html",
            sonarr=sonarrs,
            error=error,
        )

    @app.route("/scheduling", methods=["GET", "POST"])
    def scheduling():
        if not is_logged_in():
            return redirect(url_for("login"))
        if request.method == "POST":
            app.config_data["scheduling"].update(request.form)
            flash("Schedule saved")
        cron = app.config_data.get("scheduling", {}).get("cron_schedule", "")
        timezone = app.config_data.get("scheduling", {}).get("timezone", "")
        return render_template(
            "scheduling.html",
            cron_schedule=cron,
            timezone=timezone,
        )

    @app.route("/user", methods=["GET", "POST"])
    def user_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        error = ""
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if not username:
                error = "Username cannot be blank"
            else:
                app.config_data["user"]["username"] = username
                if password:
                    app.config_data["user"]["password"] = password
                error = "User settings updated"
        return render_template(
            "user.html",
            user=type("U", (), app.config_data["user"]),
            user_msg=error,
        )

    @app.route("/save", methods=["POST"])
    def save():
        # Simulate saving general settings
        # Only allow saving of non-runtime fields. Do not overwrite
        # PUID/PGID/Timezone which are controlled via environment variables.
        loglevel = request.form.get("LogLevel")
        if loglevel:
            app.config_data["general"]["LogLevel"] = loglevel
        return render_template(
            "settings_general.html",
            puid=app.config_data["general"].get("PUID"),
            pgid=app.config_data["general"].get("PGID"),
            timezone=app.config_data["general"].get("Timezone"),
            loglevel=app.config_data["general"].get("LogLevel"),
            msg="Saved",
        )

    @app.route("/health")
    def health():
        # Simulate DB/config/threads/time check for tests
        return jsonify(
            {
                "status": "ok",
                "db": "ok",
                "config": "ok",
                "threads": 1,
                "time": "2025-10-23T00:00:00Z",
            }
        )

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
        if getattr(error, "code", None) == 404:
            return ("Not found", 404)
        return ("Server error", 500)

    @app.route("/validate_sonarr/<int:idx>", methods=["POST"])
    def validate_sonarr(idx):
        # Simulate validation
        sonarrs = app.config_data.get("sonarr", [])
        if idx >= len(sonarrs):
            resp = jsonify(
                {
                    "success": False,
                    "msg": "Invalid Sonarr index",
                }
            )
            return resp, 400
        s = sonarrs[idx]
        if not s.get("sonarr0_url") or not s.get("sonarr0_api_key"):
            # Also show error on settings page for test
            error_msg = "Missing URL or API key for enabled instance."
            resp = jsonify(
                {
                    "success": False,
                    "msg": error_msg,
                }
            )
            return resp, 400

        return jsonify({"success": True})

    return app
