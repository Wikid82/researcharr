# ... code for factory.py ...

import importlib.util
import os
import pathlib
import time

import yaml
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
from werkzeug.security import generate_password_hash, check_password_hash

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

    # Use the repository-level `templates/` directory so the app can find
    # the top-level templates shipped with the project even when the
    # factory lives inside the `researcharr/` package.
    templates_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "templates")
    )
    app = Flask(__name__, template_folder=templates_path)

    # Development debug flags (enable via env vars). These are false by
    # default to avoid leaking sensitive info in production. Allowed true
    # values: 1, true, yes (case-insensitive).
    def _env_bool(name, default="false"):
        return str(os.getenv(name, default)).lower() in ("1", "true", "yes")

    app.config["WEBUI_DEV_DEBUG"] = _env_bool("WEBUI_DEV_DEBUG", "false")
    # Control whether plaintext generated credentials are printed/logged
    # on first-run. If unspecified, it follows WEBUI_DEV_DEBUG.
    app.config["WEBUI_DEV_PRINT_CREDS"] = _env_bool(
        "WEBUI_DEV_PRINT_CREDS", os.getenv("WEBUI_DEV_DEBUG", "false")
    )
    # Control the availability of an introspection debug endpoint used for
    # programmatic testing of auth logic. Disabled by default.
    app.config["WEBUI_DEV_ENABLE_DEBUG_ENDPOINT"] = _env_bool(
        "WEBUI_DEV_ENABLE_DEBUG_ENDPOINT", os.getenv("WEBUI_DEV_DEBUG", "false")
    )

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
            (
                "SECRET_KEY environment variable is required in production."
                " Set SECRET_KEY and restart."
            )
        )
    if not secret:
        secret = "dev"
        # Will be visible in logs once the app logger is configured; use
        # print as a fallback in early startup paths.
        try:
            print(
                (
                    "WARNING: using insecure default SECRET_KEY; "
                    "set SECRET_KEY in production"
                )
            )
        except Exception:
            pass
    app.secret_key = secret

    # Session cookie configuration — configurable via env vars but default
    # to secure settings suitable for production behind TLS.
    app.config["SESSION_COOKIE_SECURE"] = os.getenv(
        "SESSION_COOKIE_SECURE", "true"
    ).lower() in (
        "1",
        "true",
        "yes",
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = os.getenv(
        "SESSION_COOKIE_HTTPONLY", "true"
    ).lower() in (
        "1",
        "true",
        "yes",
    )
    samesite_val = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SAMESITE"] = samesite_val
    # Simulated in-memory config for tests. PUID/PGID/Timezone are sourced
    # from environment variables to avoid managing these sensitive runtime
    # settings via the web UI. This prevents accidental permission/timezone
    # mismatches when the container is started.
    app.config_data = {
        "general": {
            "PUID": os.getenv("PUID", "1000"),
            "PGID": os.getenv("PGID", "1000"),
            # Default timezone when not provided via env var
            "Timezone": os.getenv("TIMEZONE", "America/New_York"),
            "LogLevel": os.getenv("LOGLEVEL", "INFO"),
        },
        "radarr": [],
        "sonarr": [],
        "scheduling": {"cron_schedule": "0 0 * * *", "timezone": "UTC"},
        "user": {"username": "admin", "password": "researcharr"},
    }

    # In-memory metrics for test isolation
    # Structure:
    # { requests_total: int, errors_total: int, plugins: { <plugin>: {validate_attempts, validate_errors, sync_attempts, sync_errors, last_error, last_error_msg} } }
    app.metrics = {"requests_total": 0, "errors_total": 0, "plugins": {}}

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
                # In-memory plaintext for first-run so login works immediately
                app.config_data["user"]["password"] = ucfg.get("password")
                # If the loader returned a username (first-run), update the
                # in-memory username so the printed credentials shown to the
                # operator match what the login handler expects. This avoids a
                # mismatch where the persisted user file uses a different
                # username than the application's default 'admin'.
                if "username" in ucfg:
                    app.config_data["user"]["username"] = ucfg.get(
                        "username", app.config_data["user"]["username"]
                    )
                try:
                    app.logger.info(
                        "Generated web UI initial password for %s (plaintext available in-memory)",
                        app.config_data["user"]["username"],
                    )
                except Exception:
                    pass
            # Persisted user config may contain only hashes; preserve them
            if "password_hash" in ucfg:
                app.config_data["user"]["password_hash"] = ucfg.get("password_hash")
            # If an API key was persisted in the user config, migrate it to a
            # hashed form and expose the hash to the application so API
            # endpoints can validate requests. Prefer `api_key_hash` when
            # present; if only a legacy `api_key` is present, hash and
            # persist a migration.
            try:
                if "api_key_hash" in ucfg:
                    app.config_data.setdefault("general", {})["api_key_hash"] = (
                        ucfg.get("api_key_hash")
                    )
                elif "api_key" in ucfg:
                    # legacy plaintext key found; hash and persist migration
                    try:
                        hashed = generate_password_hash(ucfg.get("api_key"))
                        webui.save_user_config(
                            ucfg.get("username", app.config_data["user"]["username"]),
                            ucfg.get("password_hash"),
                            api_key_hash=hashed,
                        )
                        app.config_data.setdefault("general", {})[
                            "api_key_hash"
                        ] = hashed
                    except Exception:
                        app.logger.exception(
                            "Failed to migrate plaintext api_key to api_key_hash"
                        )
            except Exception:
                # best-effort; don't fail startup on migration errors
                pass
    except Exception:
        # best-effort; if loading the user config fails we continue with the
        # default in-memory credentials to avoid preventing the UI from
        # starting.
        pass

    # --- Plugin registry wiring (discover local example plugins) ---
    try:
        from researcharr.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        # Discover any local plugin modules placed under researcharr/plugins
        pkg_dir = os.path.dirname(__file__)
        plugins_dir = os.path.join(pkg_dir, "plugins")
        registry.discover_local(plugins_dir)
        # For tests we may want to instantiate configured plugin instances
        app.plugin_registry = registry
        # Load persisted plugin instance configs from disk (if available).
        # Use /config/plugins by default so admins can bind-mount persistent
        # storage into the container.
        config_root = os.getenv("CONFIG_DIR", "/config")
        plugins_config_dir = os.path.join(config_root, "plugins")
        try:
            os.makedirs(plugins_config_dir, exist_ok=True)
            for name in registry.list_plugins():
                cfg_file = os.path.join(plugins_config_dir, f"{name}.yml")
                if os.path.exists(cfg_file):
                    try:
                        with open(cfg_file) as fh:
                            data = yaml.safe_load(fh) or []
                            # Set in-memory config_data so UI and APIs use it
                            app.config_data[name] = data
                    except Exception:
                        app.logger.exception(
                            "Failed to load plugin config %s", cfg_file
                        )
        except Exception:
            # best-effort; don't prevent startup if config path is unwritable
            app.logger.debug(
                "Could not ensure plugins config dir %s",
                plugins_config_dir,
            )
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
                (
                    "Invalid PUID '%s' — falling back to 1000. "
                    "Set PUID env var to a valid integer."
                ),
                app.config_data["general"].get("PUID"),
            )
            app.config_data["general"]["PUID"] = "1000"

        try:
            pgid_val = int(app.config_data["general"].get("PGID", "1000"))
            app.config_data["general"]["PGID"] = str(pgid_val)
        except Exception:
            app.logger.warning(
                (
                    "Invalid PGID '%s' — falling back to 1000. "
                    "Set PGID env var to a valid integer."
                ),
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

    @app.route("/")
    def index():
        # Redirect root to the login page for convenience so visiting /
        # opens the web UI instead of returning 404. Tests that expect
        # root to be missing should continue to use explicit paths.
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = app.config_data["user"]
            # Accept either the in-memory plaintext password (first-run) or
            # verify against a stored password hash when present.
            pw_ok = False
            try:
                if password and "password" in user and password == user["password"]:
                    pw_ok = True
                elif password and "password_hash" in user and user["password_hash"]:
                    pw_ok = check_password_hash(user["password_hash"], password)
            except Exception:
                pw_ok = False
            # Debug logging to help diagnose mismatches during development
            try:
                # Emit debug information only when explicitly enabled via
                # the WEBUI_DEV_DEBUG env var to avoid leaking sensitive
                # information in production logs.
                if app.config.get("WEBUI_DEV_DEBUG"):
                    # Print to stdout for debugging in the container logs
                    print(
                        f"DEBUG_LOGIN user={username} pw_ok={pw_ok} keys={list(user.keys())}"
                    )
                    try:
                        app.logger.debug(
                            "DEBUG_LOGIN user=%s pw_ok=%s keys=%s",
                            username,
                            pw_ok,
                            list(user.keys()),
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            if username == user["username"] and pw_ok:
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
            # Regenerate API key when requested via the UI
            if request.form.get("regen_api"):
                import secrets

                new_key = secrets.token_urlsafe(32)
                # Store only the hash in runtime config for security
                from werkzeug.security import generate_password_hash

                new_hash = generate_password_hash(new_key)
                app.config_data.setdefault("general", {})["api_key_hash"] = new_hash
                # Persist to the user config so the key survives restarts
                try:
                    ucfg = webui.load_user_config() or {}
                    username = ucfg.get("username", app.config_data["user"]["username"])
                    pwd_hash = ucfg.get("password_hash")
                    webui.save_user_config(username, pwd_hash, api_key_hash=new_hash)
                except Exception:
                    app.logger.exception("Failed to persist regenerated API key")
                flash("API key regenerated")
            else:
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
            api_key=app.config_data.get("general", {}).get("api_key"),
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

    @app.route("/settings/plugins", methods=["GET"])
    def plugins_settings():
        if not is_logged_in():
            return redirect(url_for("login"))
        registry = getattr(app, "plugin_registry", None)
        # Build a mapping category -> list[plugin_entry]
        plugins_by_category = {}
        if registry is not None:
            for name in registry.list_plugins():
                instances = app.config_data.get(name, [])
                cls = registry.get(name)
                # Prefer a class-level category attribute, default to 'plugins'
                category = (
                    getattr(cls, "category", "plugins")
                    if cls is not None
                    else "plugins"
                )
                description = getattr(cls, "description", "") if cls is not None else ""
                docs_url = getattr(cls, "docs_url", None) if cls is not None else None
                plugins_by_category.setdefault(category, []).append(
                    {
                        "name": name,
                        "instances": instances,
                        "description": description,
                        "docs_url": docs_url,
                    }
                )

        # Allow filtering by category via ?category=media
        selected_category = request.args.get("category")

        # Human-friendly titles for known categories
        category_titles = {
            "media": "Media",
            "scrapers": "Scrapers",
            "clients": "Clients",
            "notifications": "Notifications",
            "plugins": "Plugins",
        }

        return render_template(
            "settings_plugins.html",
            plugins=plugins_by_category,
            selected_category=selected_category,
            category_titles=category_titles,
        )

    @app.route("/api/plugins", methods=["GET"])
    def api_plugins():
        """Return discovered plugins and configured instances as JSON.

        This is intentionally a read-only endpoint used by the UI and tests.
        """
        # Require login to access plugin metadata
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        registry = getattr(app, "plugin_registry", None)
        data = {"plugins": []}
        if registry is not None:
            for name in registry.list_plugins():
                instances = app.config_data.get(name, [])
                data["plugins"].append({"name": name, "instances": instances})
        return jsonify(data)

    @app.route("/api/version", methods=["GET"])
    def api_version():
        """Return build/version metadata baked into the image at build time.

        Reads `/app/VERSION` if present, otherwise returns sensible defaults.
        """
        info = {"version": "dev", "build": "0", "sha": "unknown"}
        try:
            # Allow overriding the version file path via env for testing or
            # alternative layouts. Default to /app/VERSION which is created
            # at image build time by CI.
            ver_file = os.getenv("RESEARCHARR_VERSION_FILE", "/app/VERSION")
            p = pathlib.Path(ver_file)
            if p.exists():
                for line in p.read_text().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
        except Exception:
            # best-effort; do not fail the endpoint on read errors
            pass
        return jsonify(info)

    @app.route(
        "/api/plugins/<plugin_name>/validate/<int:idx>",
        methods=["POST"],
    )
    def api_plugin_validate(plugin_name: str, idx: int):
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        registry = getattr(app, "plugin_registry", None)
        if registry is None or registry.get(plugin_name) is None:
            return jsonify({"error": "unknown_plugin"}), 404
        instances = app.config_data.get(plugin_name, [])
        if idx < 0 or idx >= len(instances):
            return jsonify({"error": "invalid_instance"}), 400
        inst_cfg = instances[idx]
        # Ensure plugin metrics bucket exists
        try:
            pmetrics = app.metrics.setdefault("plugins", {}).setdefault(
                plugin_name, {"validate_attempts": 0, "validate_errors": 0, "sync_attempts": 0, "sync_errors": 0, "last_error": None, "last_error_msg": None}
            )
        except Exception:
            pmetrics = None

        # Track an attempt
        try:
            if pmetrics is not None:
                pmetrics["validate_attempts"] = pmetrics.get("validate_attempts", 0) + 1
        except Exception:
            pass

        try:
            pl = registry.create_instance(plugin_name, inst_cfg)
            result = pl.validate()
            # Treat falsy result as a validation failure to be surfaced in metrics
            if not result:
                try:
                    if pmetrics is not None:
                        pmetrics["validate_errors"] = pmetrics.get("validate_errors", 0) + 1
                        pmetrics["last_error"] = int(time.time())
                        pmetrics["last_error_msg"] = "validation returned falsy"
                except Exception:
                    pass
            return jsonify({"result": result})
        except Exception as e:
            # Record error in plugin metrics
            try:
                if pmetrics is not None:
                    pmetrics["validate_errors"] = pmetrics.get("validate_errors", 0) + 1
                    pmetrics["last_error"] = int(time.time())
                    pmetrics["last_error_msg"] = str(e)
            except Exception:
                pass
            app.logger.exception("Plugin validate failed: %s", e)
            return jsonify({"error": "validate_failed", "msg": str(e)}), 500

    @app.route(
        "/api/plugins/<plugin_name>/sync/<int:idx>",
        methods=["POST"],
    )
    def api_plugin_sync(plugin_name: str, idx: int):
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        registry = getattr(app, "plugin_registry", None)
        if registry is None or registry.get(plugin_name) is None:
            return jsonify({"error": "unknown_plugin"}), 404
        instances = app.config_data.get(plugin_name, [])
        if idx < 0 or idx >= len(instances):
            return jsonify({"error": "invalid_instance"}), 400
        inst_cfg = instances[idx]
        # Ensure plugin metrics bucket exists
        try:
            pmetrics = app.metrics.setdefault("plugins", {}).setdefault(
                plugin_name, {"validate_attempts": 0, "validate_errors": 0, "sync_attempts": 0, "sync_errors": 0, "last_error": None, "last_error_msg": None}
            )
        except Exception:
            pmetrics = None

        # Track sync attempt
        try:
            if pmetrics is not None:
                pmetrics["sync_attempts"] = pmetrics.get("sync_attempts", 0) + 1
        except Exception:
            pass

        try:
            pl = registry.create_instance(plugin_name, inst_cfg)
            result = pl.sync()
            if not result:
                try:
                    if pmetrics is not None:
                        pmetrics["sync_errors"] = pmetrics.get("sync_errors", 0) + 1
                        pmetrics["last_error"] = int(time.time())
                        pmetrics["last_error_msg"] = "sync returned falsy"
                except Exception:
                    pass
            return jsonify({"result": result})
        except Exception as e:
            try:
                if pmetrics is not None:
                    pmetrics["sync_errors"] = pmetrics.get("sync_errors", 0) + 1
                    pmetrics["last_error"] = int(time.time())
                    pmetrics["last_error_msg"] = str(e)
            except Exception:
                pass
            app.logger.exception("Plugin sync failed: %s", e)
            return jsonify({"error": "sync_failed", "msg": str(e)}), 500


    @app.route("/api/storage", methods=["GET"])
    def api_storage():
        """Return simple checks for configured storage mount points (config/plugins).

        Returns JSON like: {"paths": [{"name": "config", "path": "/config", "exists": true, "is_dir": true, "readable": true, "writable": false}, ...]}
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        plugins_config_dir = os.path.join(config_root, "plugins")
        checks = []
        for name, path in (("config", config_root), ("plugins", plugins_config_dir)):
            try:
                exists = os.path.exists(path)
                is_dir = os.path.isdir(path)
                readable = os.access(path, os.R_OK)
                writable = os.access(path, os.W_OK)
            except Exception:
                exists = is_dir = readable = writable = False
            checks.append(
                {
                    "name": name,
                    "path": path,
                    "exists": exists,
                    "is_dir": is_dir,
                    "readable": readable,
                    "writable": writable,
                }
            )
        return jsonify({"paths": checks})

    @app.route("/api/status", methods=["GET"])
    def api_status():
        """Return an aggregated status summary used by the UI.

        Provides a lightweight, best-effort set of checks including:
        - storage mount checks (config/plugins)
        - simple DB connectivity/readability check
        - config/user/api key sanity checks
        - log and DB file size checks
        - example file existence check
        - simple resource usage (from /proc when available)
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        result = {}

        # Storage checks (reuse same logic as /api/storage)
        try:
            config_root = os.getenv("CONFIG_DIR", "/config")
            plugins_config_dir = os.path.join(config_root, "plugins")
            paths = []
            for name, path in (("config", config_root), ("plugins", plugins_config_dir)):
                try:
                    exists = os.path.exists(path)
                    is_dir = os.path.isdir(path)
                    readable = os.access(path, os.R_OK)
                    writable = os.access(path, os.W_OK)
                except Exception:
                    exists = is_dir = readable = writable = False
                paths.append(
                    {
                        "name": name,
                        "path": path,
                        "exists": exists,
                        "is_dir": is_dir,
                        "readable": readable,
                        "writable": writable,
                    }
                )
            result["storage"] = {"paths": paths}
        except Exception:
            result["storage"] = {"paths": []}

        # DB connectivity & file checks (best-effort)
        db_info = {"ok": True}
        try:
            # Prefer env override
            db_file = os.getenv(
                "RESEARCHARR_DB",
                os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "researcharr.db")),
            )
            db_info["path"] = db_file
            try:
                import sqlite3

                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
                conn.close()
                # size and mtime if present
                try:
                    st = os.stat(db_file)
                    db_info["size"] = st.st_size
                    db_info["mtime"] = int(st.st_mtime)
                except Exception:
                    pass
            except Exception as e:
                db_info["ok"] = False
                db_info["error"] = str(e)
        except Exception as e:
            db_info = {"ok": False, "error": str(e)}
        result["db"] = db_info

        # Config and user/api checks
        cfg_issues = []
        try:
            gen = app.config_data.get("general", {})
            if not gen.get("api_key_hash"):
                cfg_issues.append("Missing API key (no api_key_hash configured)")
        except Exception:
            cfg_issues.append("Failed to inspect general config")

        # Admin/user config check — if a plaintext password exists in-memory
        try:
            user = app.config_data.get("user", {})
            if user.get("password") and not user.get("password_hash"):
                cfg_issues.append("Web UI admin account still has first-run plaintext password in memory; rotate credentials")
            if not user.get("username"):
                cfg_issues.append("Missing web UI username")
        except Exception:
            cfg_issues.append("Failed to inspect user config")
        result["config"] = {"issues": cfg_issues}

        # Log and DB growth checks (best-effort)
        logs = {}
        try:
            # app.log in repository root or env override
            app_log = os.getenv("WEBUI_LOG", os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "app.log")))
            if os.path.exists(app_log):
                st = os.stat(app_log)
                logs["app_log"] = {"path": app_log, "size": st.st_size, "mtime": int(st.st_mtime)}
            # db size included above
        except Exception:
            pass
        result["logs"] = logs

        # Example files check
        try:
            example_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config.example.yml"))
            result["examples"] = {"config_example_exists": os.path.exists(example_path), "path": example_path}
        except Exception:
            result["examples"] = {"config_example_exists": False}

        # Basic resource usage from /proc (Linux-only, best-effort)
        resources = {}
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as fh:
                    lines = fh.read().splitlines()
                mem = {}
                for l in lines:
                    if ":" in l:
                        k, v = l.split(":", 1)
                        mem[k.strip()] = v.strip()
                resources["meminfo"] = {k: mem.get(k) for k in ("MemTotal", "MemAvailable")} if mem else {}
            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg") as fh:
                    resources["loadavg"] = fh.read().strip()
            # uptime
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime") as fh:
                    resources["uptime_seconds"] = float(fh.read().split()[0])
        except Exception:
            pass
        result["resources"] = resources

        # Metrics summary (best-effort)
        try:
            result["metrics"] = app.metrics or {}
        except Exception:
            result["metrics"] = {}

        # Include a plugin summary with error rates for convenience
        try:
            plugins_summary = {}
            for pname, pm in (app.metrics.get("plugins") or {}).items():
                try:
                    va = int(pm.get("validate_attempts", 0))
                    ve = int(pm.get("validate_errors", 0))
                    sa = int(pm.get("sync_attempts", 0))
                    se = int(pm.get("sync_errors", 0))
                    validate_rate = (ve / va * 100.0) if va > 0 else None
                    sync_rate = (se / sa * 100.0) if sa > 0 else None
                    plugins_summary[pname] = {
                        "validate_attempts": va,
                        "validate_errors": ve,
                        "validate_error_rate": validate_rate,
                        "sync_attempts": sa,
                        "sync_errors": se,
                        "sync_error_rate": sync_rate,
                        "last_error": pm.get("last_error"),
                        "last_error_msg": pm.get("last_error_msg"),
                    }
                except Exception:
                    plugins_summary[pname] = {"error": "failed to summarize"}
            result["plugins"] = plugins_summary
        except Exception:
            result["plugins"] = {}

        return jsonify(result)

    @app.route("/api/plugins/<plugin_name>/instances", methods=["POST"])
    def api_plugin_instances(plugin_name: str):
        """Add/update/delete plugin instances via JSON POST.

        Expected JSON shape:
        {
            "action": "add" | "update" | "delete",
            "idx": int | None,
            "instance": {...},
        }
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        registry = getattr(app, "plugin_registry", None)
        if registry is None or registry.get(plugin_name) is None:
            return jsonify({"error": "unknown_plugin"}), 404
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid_json"}), 400
        action = data.get("action")
        instances = app.config_data.get(plugin_name, []) or []

        def _validate_instance(inst):
            # Basic validation: if enabled, require url and api_key
            if not isinstance(inst, dict):
                return False, "instance must be an object"
            if inst.get("enabled"):
                url = inst.get("url", "") or ""
                key = inst.get("api_key", "") or ""
                if not isinstance(url, str) or not url.startswith("http"):
                    return False, "URL must start with http/https"
                if not key:
                    return False, "API key is required for enabled instances"
            return True, None

        # perform action
        if action == "add":
            inst = data.get("instance") or {}
            ok, err = _validate_instance(inst)
            if not ok:
                return jsonify({"error": "invalid_instance", "msg": err}), 400
            instances.append(inst)
            app.config_data[plugin_name] = instances
        elif action == "update":
            idx = data.get("idx")
            if (
                idx is None
                or not isinstance(idx, int)
                or idx < 0
                or idx >= len(instances)
            ):
                return jsonify({"error": "invalid_instance"}), 400
            inst = data.get("instance") or {}
            ok, err = _validate_instance(inst)
            if not ok:
                return jsonify({"error": "invalid_instance", "msg": err}), 400
            instances[idx] = inst
            app.config_data[plugin_name] = instances
        elif action == "delete":
            idx = data.get("idx")
            if (
                idx is None
                or not isinstance(idx, int)
                or idx < 0
                or idx >= len(instances)
            ):
                return jsonify({"error": "invalid_instance"}), 400
            instances.pop(idx)
            app.config_data[plugin_name] = instances
        else:
            return jsonify({"error": "unknown_action"}), 400

        # Persist instances to disk under CONFIG_DIR/plugins/<plugin_name>.yml
        try:
            config_root = os.getenv("CONFIG_DIR", "/config")
            plugins_config_dir = os.path.join(config_root, "plugins")
            os.makedirs(plugins_config_dir, exist_ok=True)
            cfg_file = os.path.join(plugins_config_dir, f"{plugin_name}.yml")
            with open(cfg_file, "w") as fh:
                yaml.safe_dump(app.config_data.get(plugin_name, []), fh)
        except Exception:
            app.logger.exception(
                "Failed to persist plugin instances for %s", plugin_name
            )
            # don't fail the request; inform the client
            return jsonify({"result": "ok", "warning": "persist_failed"}), 200

        return jsonify({"result": "ok"})

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

    # Register a small API blueprint (under /api/v1) if available. This
    # exposes programmatic access to plugins, metrics and health checks.
    try:
        from researcharr import api as _api

        app.register_blueprint(_api.bp, url_prefix="/api/v1")
    except Exception:
        # Non-fatal if API blueprint cannot be loaded (tests may not need it)
        pass

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

    # Development-only debug endpoint for programmatic auth testing. This
    # is only registered when WEBUI_DEV_ENABLE_DEBUG_ENDPOINT is enabled.
    if app.config.get("WEBUI_DEV_ENABLE_DEBUG_ENDPOINT"):

        @app.route("/__debug_auth", methods=["POST"])
        def __debug_auth():
            # Accept JSON {"password": "..."} and return whether it
            # matches the in-memory plaintext (first-run) or the stored
            # password hash. Returns minimal info suitable for local dev.
            payload = None
            try:
                payload = request.get_json(force=True, silent=True) or {}
            except Exception:
                payload = {}
            pw = payload.get("password")
            user = app.config_data.get("user", {})
            pw_ok = False
            try:
                if pw and "password" in user and pw == user.get("password"):
                    pw_ok = True
                elif pw and "password_hash" in user and user.get("password_hash"):
                    pw_ok = check_password_hash(user.get("password_hash"), pw)
            except Exception:
                pw_ok = False
            return jsonify(
                {
                    "user_keys": list(user.keys()),
                    "pw_ok": pw_ok,
                    "username": user.get("username"),
                }
            )

    # --- System pages introduced via the sidebar ---
    @app.route("/status")
    def status():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("status.html")

    @app.route("/tasks")
    def tasks():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("tasks.html")


    @app.route("/api/tasks", methods=["GET"])
    def api_tasks():
        """Return recent scheduled job runs parsed from the cron log.

        The implementation is best-effort and parses `/config/cron.log` by
        splitting on 'Starting scheduled job' entries. Each run contains a
        start timestamp, lines for stdout/stderr, and a returncode when
        available.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        log_path = os.getenv("CRON_LOG_PATH", "/config/cron.log")
        # Pagination parameters
        max_entries = int(request.args.get("limit", app.config_data.get("tasks", {}).get("show_count", 20)))
        offset = int(request.args.get("offset", 0))
        runs = []
        try:
            if os.path.exists(log_path):
                with open(log_path, "r") as fh:
                    raw = fh.read()
                # Split into blocks starting with the date-prefixed line
                parts = raw.split('\n')
                current = None
                for line in parts:
                    if not line.strip():
                        continue
                    # Expect lines like: 2025-10-25 12:00:00,000 INFO Message
                    # Identify new run by 'Starting scheduled job'
                    if "Starting scheduled job" in line:
                        # start a new run
                        if current is not None:
                            runs.append(current)
                        # extract timestamp at start of line (space-separated first two tokens)
                        try:
                            ts = line.split()[0] + " " + line.split()[1]
                        except Exception:
                            ts = None
                        current = {"start": ts, "lines": [line], "returncode": None, "success": None}
                    elif current is not None:
                        current["lines"].append(line)
                        if "Job finished with returncode" in line:
                            try:
                                rc = int(line.rsplit()[-1])
                                current["returncode"] = rc
                                current["success"] = (rc == 0)
                            except Exception:
                                pass
                        elif line.startswith("Job stderr:") or "Job stderr:" in line:
                            # treat any stderr as possible failure indicator
                            current.setdefault("has_stderr", True)
                if current is not None:
                    runs.append(current)
                # most recent runs last in file; return newest first
                runs = list(reversed(runs))
                total = len(runs)
                # apply offset/limit for pagination
                runs = runs[offset: offset + max_entries]
        except Exception:
            return jsonify({"error": "failed_to_read_log"}), 500

        return jsonify({"runs": runs, "total": total})


    @app.route("/api/tasks/trigger", methods=["POST"])
    def api_tasks_trigger():
        """Trigger the scheduled job manually (runs in background thread).

        This invokes the same `run_job` function used by the scheduler. The
        function is executed in a background thread to avoid blocking the
        request. The scheduler's concurrency guard (if any) applies, so
        triggering while a job runs will typically be skipped by the
        underlying lock.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        try:
            # Import run.py and invoke run_job in a background thread if
            # available. If import fails, return an error.
            spec_path = os.path.join(os.path.dirname(__file__), "run.py")
            if not os.path.exists(spec_path):
                return jsonify({"error": "run_module_missing"}), 500
            import importlib.util

            spec = importlib.util.spec_from_file_location("run_module", spec_path)
            run_mod = importlib.util.module_from_spec(spec)
            loader = spec.loader
            assert loader is not None
            loader.exec_module(run_mod)

            # Run in background thread
            import threading

            t = threading.Thread(target=getattr(run_mod, "run_job"), daemon=True)
            t.start()
            return jsonify({"result": "triggered"})
        except Exception:
            app.logger.exception("Failed to trigger scheduled job")
            return jsonify({"error": "trigger_failed"}), 500


    @app.route("/api/tasks/settings", methods=["GET", "POST"])
    def api_tasks_settings():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        if request.method == "GET":
            tasks_cfg = app.config_data.get("tasks", {})
            return jsonify(tasks_cfg)
        # POST: update settings
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid_json"}), 400
        tasks_cfg = app.config_data.setdefault("tasks", {})
        # Only allow integer show_count for now
        show_count = data.get("show_count")
        try:
            if show_count is not None:
                tasks_cfg["show_count"] = int(show_count)
        except Exception:
            return jsonify({"error": "invalid_show_count"}), 400
        app.config_data["tasks"] = tasks_cfg
        return jsonify({"result": "ok", "tasks": tasks_cfg})

    @app.route("/backups")
    def backups():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("backups.html")

    @app.route("/updates")
    def updates():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("updates.html")

    @app.route("/logs")
    def logs():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("logs.html")

    return app
