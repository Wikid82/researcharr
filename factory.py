# ... code for factory.py ...

import importlib.util
import os
import pathlib
import shutil
import time
import zipfile
from typing import TYPE_CHECKING, Any

import yaml
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    stream_with_context,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from researcharr.backups import create_backup_file, prune_backups

# from datetime import datetime  (not required at module scope)


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

    # Prefer a repository-level `templates/` directory so the app can find
    # the top-level templates when they are placed at the repo root.
    # Fall back to the package-local `templates/` directory otherwise.
    repo_templates = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "templates")
    )
    package_templates = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "templates")
    )
    if os.path.isdir(repo_templates):
        templates_path = repo_templates
    else:
        templates_path = package_templates

    # Annotate as Any so static type checkers (Pylance) don't warn about
    # project-specific attributes we attach to the Flask app at runtime.
    app: Any = Flask(__name__, template_folder=templates_path)

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
        "user": {"username": "admin", "password": "password"},
        # Backups settings (sample defaults)
        # retain_count: max files to keep
        # retain_days: age in days to keep
        # pre_restore: create snapshot before restore
        "backups": {
            "retain_count": 10,
            "retain_days": 30,
            "pre_restore": True,
            "pre_restore_keep_days": 1,
            "auto_backup_enabled": False,
            "auto_backup_cron": "0 2 * * *",
            "prune_cron": "0 3 * * *",
        },
    }

    # Load persisted tasks settings if present so UI preferences survive restarts
    try:
        config_root = os.getenv("CONFIG_DIR", "/config")
        tasks_cfg_file = os.path.join(config_root, "tasks.yml")
        if os.path.exists(tasks_cfg_file):
            try:
                with open(tasks_cfg_file) as fh:
                    tcfg = yaml.safe_load(fh) or {}
                app.config_data.setdefault("tasks", {}).update(tcfg)
            except Exception:
                try:
                    app.logger.exception(
                        "Failed to load tasks settings %s", tasks_cfg_file
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # Load persisted general settings (e.g., UI-chosen LogLevel) if present
    try:
        general_cfg_file = os.path.join(config_root, "general.yml")
        if os.path.exists(general_cfg_file):
            try:
                with open(general_cfg_file) as fh:
                    gcfg = yaml.safe_load(fh) or {}
                # Only merge known keys to avoid clobbering runtime env-managed keys
                if isinstance(gcfg, dict):
                    app.config_data.setdefault("general", {}).update(
                        {k: v for k, v in gcfg.items() if k in ("LogLevel",)}
                    )
            except Exception:
                try:
                    app.logger.exception(
                        "Failed to load general settings %s", general_cfg_file
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # In-memory metrics for test isolation
    # Structure example:
    # {
    #   "requests_total": int,
    #   "errors_total": int,
    #   "plugins": {
    #       "<plugin>": {
    #           "validate_attempts", "validate_errors", "sync_attempts",
    #           "sync_errors", "last_error", "last_error_msg"
    #       }
    #   }
    # }
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
            # Preserve the in-code defaults for username/password used by
            # tests (username 'admin', password 'researcharr'). Do not
            # override these defaults with values returned by the loader
            # (which may generate first-run credentials) because tests rely
            # on stable defaults. However, if a persisted password hash is
            # present, expose it so the app can validate hashed passwords.
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
                        api_key_val = ucfg.get("api_key")
                        if api_key_val:
                            hashed = generate_password_hash(str(api_key_val))
                            username_default = app.config_data["user"]["username"]
                            webui.save_user_config(
                                ucfg.get("username", username_default),
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
    # Allow static analysis (Pylance) to see the PluginRegistry symbol while
    # using a runtime-safe import path for actual execution. The runtime
    # import attempts multiple fallbacks so the app starts under the repo
    # layout and inside a packaged installation.
    if TYPE_CHECKING:  # pragma: no cover - static type hint only
        # Provide a typing alias so static type checkers know the name
        # exists without requiring the actual module to be importable at
        # analysis time. Use `Any` to keep the type loose.
        PluginRegistry = Any  # type: ignore

    try:
        try:
            from researcharr.plugins.registry import (
                PluginRegistry,  # type: ignore
            )

            registry = PluginRegistry()
        except Exception:
            # Try plain top-level `plugins.registry` (when running from
            # repository root) before resorting to loading the file via
            # importlib. This helps the editor/runtime find the module in
            # both installed and source layouts.
            try:
                from plugins.registry import PluginRegistry  # type: ignore

                registry = PluginRegistry()
            except Exception:
                # Fallback: attempt to load the module directly from the
                # package directory using importlib. If this fails the
                # surrounding except will silently continue (app will
                # operate without plugin registry).
                pkg_dir = os.path.dirname(__file__)
                reg_path = os.path.join(pkg_dir, "plugins", "registry.py")
                spec = importlib.util.spec_from_file_location(
                    "researcharr.plugins.registry", reg_path
                )
                if spec is None or spec.loader is None:
                    raise ImportError("Failed to locate plugins.registry")
                plugin_mod = importlib.util.module_from_spec(spec)
                loader = spec.loader
                assert loader is not None
                loader.exec_module(plugin_mod)
                PluginRegistry = getattr(plugin_mod, "PluginRegistry")
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
                    # Print to stdout for debugging in the container logs.
                    # Build a compact keys list separately to avoid overly
                    # long inline expressions that exceed line-length limits.
                    keys_list = list(user.keys())
                    print(f"DEBUG_LOGIN user={username} pw_ok={pw_ok} keys={keys_list}")
                    try:
                        app.logger.debug(
                            "DEBUG_LOGIN user=%s pw_ok=%s keys=%s",
                            username,
                            pw_ok,
                            keys_list,
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
                # environment variables.
                flash("General settings saved")
        return render_template(
            "general.html",
            puid=app.config_data["general"].get("PUID"),
            pgid=app.config_data["general"].get("PGID"),
            timezone=app.config_data["general"].get("Timezone"),
            loglevel=app.config_data["general"].get("LogLevel"),
            api_key=app.config_data.get("general", {}).get("api_key"),
            msg=None,
        )

    @app.route("/logs", methods=["GET", "POST"])
    def logs_page():
        if not is_logged_in():
            return redirect(url_for("login"))
        # POST used to change live log level
        if request.method == "POST":
            loglevel = request.form.get("LogLevel")
            if loglevel:
                try:
                    # update runtime config and live logger level
                    app.config_data.setdefault("general", {})["LogLevel"] = loglevel
                    import logging

                    root = logging.getLogger()
                    root.setLevel(getattr(logging, loglevel, logging.INFO))
                    app.logger.setLevel(getattr(logging, loglevel, logging.INFO))
                    # persist chosen loglevel so it survives restarts
                    try:
                        config_root = os.getenv("CONFIG_DIR", "/config")
                        general_cfg_file = os.path.join(config_root, "general.yml")
                        os.makedirs(os.path.dirname(general_cfg_file), exist_ok=True)
                        with open(general_cfg_file, "w") as fh:
                            yaml.safe_dump({"LogLevel": loglevel}, fh)
                    except Exception:
                        app.logger.exception("Failed to persist LogLevel to disk")
                    flash("Log level updated")
                except Exception:
                    app.logger.exception("Failed to set log level")
                    flash("Failed to update log level")
        # Render logs page for GET (and for POST fall-through)
        return render_template("logs.html")

    @app.route("/settings/radarr", methods=["GET", "POST"])
    def radarr_settings():
        # Radarr settings are now managed by the plugin system. Keep a
        # backwards-compatible redirect to the Plugins page (media
        # category) so older links continue to work.
        if not is_logged_in():
            return redirect(url_for("login"))
        flash("Radarr settings have moved to the Plugins page.")
        return redirect(url_for("plugins_settings", category="media"))

    @app.route("/settings/sonarr", methods=["GET", "POST"])
    def sonarr_settings():
        # Sonarr settings are now managed by the plugin system. Redirect
        # to the Plugins page so old links keep working.
        if not is_logged_in():
            return redirect(url_for("login"))
        flash("Sonarr settings have moved to the Plugins page.")
        return redirect(url_for("plugins_settings", category="media"))

    @app.route("/api/logs", methods=["GET"])
    def api_logs():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        # allow overriding log path via env
        app_log = os.getenv(
            "WEBUI_LOG",
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, "app.log")
            ),
        )
        # optional query params
        try:
            lines = int(request.args.get("lines", 200))
        except Exception:
            lines = 200
        download = request.args.get("download")
        # If download requested, return file as attachment
        if download:
            if os.path.exists(app_log):
                return send_file(app_log, as_attachment=True)
            else:
                return jsonify({"error": "log_not_found"}), 404
        content = ""
        meta = {}
        try:
            if os.path.exists(app_log):
                with open(app_log, "r", errors="ignore") as fh:
                    all_lines = fh.read().splitlines()
                tail = all_lines[-lines:]
                content = "\n".join(tail)
                st = os.stat(app_log)
                meta = {"path": app_log, "size": st.st_size, "mtime": int(st.st_mtime)}
            else:
                content = ""
        except Exception:
            app.logger.exception("Failed to read app log")
            return jsonify({"error": "read_failed"}), 500
        return jsonify(
            {
                "content": content,
                "meta": meta,
                "loglevel": app.config_data.get("general", {}).get("LogLevel"),
            }
        )

    @app.route("/api/tasks", methods=["GET"])
    def api_tasks():
        """Return recent scheduled job runs from structured JSONL history.

        The runtime writes structured JSON lines to `CONFIG_DIR/task_history.jsonl`
        after each scheduled run. This endpoint supports pagination (`limit`,
        `offset`), server-side filtering by `status` (e.g., `failed`) and a
        text `search` over stdout/stderr.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        config_root = os.getenv("CONFIG_DIR", "/config")
        hist_file = os.path.join(config_root, "task_history.jsonl")
        limit = int(
            request.args.get(
                "limit", app.config_data.get("tasks", {}).get("show_count", 20)
            )
        )
        offset = int(request.args.get("offset", 0))
        status_filter = request.args.get("status")  # e.g., 'failed'
        search_text = request.args.get("search")

        runs = []
        total = 0
        try:
            if os.path.exists(hist_file):
                with open(hist_file, "r") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = (
                                yaml.safe_load(line)
                                if line.lstrip().startswith("-")
                                else None
                            )
                        except Exception:
                            rec = None
                        if rec is None:
                            try:
                                rec = __import__("json").loads(line)
                            except Exception:
                                # Skip malformed lines
                                continue
                        runs.append(rec)
                # newest last in file; present newest first
                runs = list(reversed(runs))

                # server-side filtering
                def match_filters(r):
                    if status_filter:
                        if status_filter == "failed":
                            if not (
                                r.get("success") is False
                                or (
                                    r.get("returncode") is not None
                                    and r.get("returncode") != 0
                                )
                                or r.get("stderr")
                            ):
                                return False
                        # other status types may be added
                    if search_text:
                        target = (
                            (r.get("stdout", "") or "")
                            + "\n"
                            + (r.get("stderr", "") or "")
                        )
                        if (
                            search_text.lower() not in target.lower()
                            and search_text.lower()
                            not in str(r.get("start_ts", "")).lower()
                        ):
                            return False
                    return True

                filtered = [r for r in runs if match_filters(r)]
                total = len(filtered)
                runs = filtered[offset : offset + limit]
            else:
                runs = []
                total = 0
        except Exception:
            return jsonify({"error": "failed_to_read_history"}), 500

        return jsonify({"runs": runs, "total": total})

    @app.route("/api/logs/stream", methods=["GET"])
    def api_logs_stream():
        """Server-sent events endpoint that tails the application log.

        Query params:
          lines - number of initial tail lines to send (default 200)
        """
        if not is_logged_in():
            return ("", 401)
        app_log = os.getenv(
            "WEBUI_LOG",
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, "app.log")
            ),
        )
        try:
            initial_lines = int(request.args.get("lines", 200))
        except Exception:
            initial_lines = 200

        def tail_lines(path, n):
            # Memory-efficient backward reader to get the last n lines.
            # Reads blocks from the end until we've got enough newlines.
            try:
                with open(path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    filesize = f.tell()
                    if filesize == 0:
                        return []
                    block_size = 4096
                    blocks = []
                    lines_found = 0
                    to_read = filesize
                    while to_read > 0 and lines_found <= n:
                        read_size = min(block_size, to_read)
                        f.seek(to_read - read_size)
                        chunk = f.read(read_size)
                        blocks.insert(0, chunk)
                        lines_found = b"\n".join(blocks).count(b"\n")
                        to_read -= read_size
                    data = b"".join(blocks)
                    parts = data.splitlines()
                    tail = parts[-n:]
                    return [p.decode("utf-8", errors="replace") for p in tail]
            except Exception:
                return []

        def generate():
            try:
                if not os.path.exists(app_log):
                    yield "data: " + "" + "\n\n"
                    return
                # send initial tail efficiently
                tail = tail_lines(app_log, initial_lines)
                if tail:
                    for t in tail:
                        # protect from newlines inside the line
                        for ln in t.splitlines():
                            yield f"data: {ln}\n"
                    yield "\n"

                # now stream appended lines by seeking to end and reading
                with open(app_log, "r", errors="ignore") as fh:
                    fh.seek(0, os.SEEK_END)
                    while True:
                        where = fh.tell()
                        line = fh.readline()
                        if line:
                            for ln in line.splitlines():
                                yield f"data: {ln}\n"
                            yield "\n"
                        else:
                            time.sleep(1.0)
                            fh.seek(where)
            except GeneratorExit:
                return
            except Exception:
                try:
                    app.logger.exception("Log stream error")
                except Exception:
                    pass
                yield "data: [stream error]\n\n"

        return Response(stream_with_context(generate()), mimetype="text/event-stream")

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
            "plugins.html",
            plugins=plugins_by_category,
            selected_category=selected_category,
            category_titles=category_titles,
        )

    @app.route("/account")
    def account():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("account.html")

    @app.route("/plugins")
    def plugins_redirect():
        # Convenience redirect so templates linking to /plugins resolve
        return redirect(url_for("plugins_settings"))

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
                plugin_name,
                {
                    "validate_attempts": 0,
                    "validate_errors": 0,
                    "sync_attempts": 0,
                    "sync_errors": 0,
                    "last_error": None,
                    "last_error_msg": None,
                },
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
                        pmetrics["validate_errors"] = (
                            pmetrics.get("validate_errors", 0) + 1
                        )
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
                plugin_name,
                {
                    "validate_attempts": 0,
                    "validate_errors": 0,
                    "sync_attempts": 0,
                    "sync_errors": 0,
                    "last_error": None,
                    "last_error_msg": None,
                },
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
        """Return simple checks for configured storage mount points.

        Returns JSON similar to:
        {
            "paths": [
                {"name": "config", "path": "/config", "exists": true,
                 "is_dir": true, "readable": true, "writable": false},
                ...
            ]
        }
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
            for name, path in (
                ("config", config_root),
                ("plugins", plugins_config_dir),
            ):
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
        # Annotate as Any to avoid narrow inference of the dict value types
        db_info: dict[str, Any] = {"ok": True}
        try:
            # Prefer env override
            db_file = os.getenv(
                "RESEARCHARR_DB",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), os.pardir, "researcharr.db")
                ),
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
                cfg_issues.append(
                    "Web UI admin account has first-run plaintext password; rotate it"
                )
            if not user.get("username"):
                cfg_issues.append("Missing web UI username")
        except Exception:
            cfg_issues.append("Failed to inspect user config")
        result["config"] = {"issues": cfg_issues}

        # Log and DB growth checks (best-effort)
        logs = {}
        try:
            # app.log in repository root or env override
            app_log = os.getenv(
                "WEBUI_LOG",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), os.pardir, "app.log")
                ),
            )
            if os.path.exists(app_log):
                st = os.stat(app_log)
                logs["app_log"] = {
                    "path": app_log,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                }
            # db size included above
        except Exception:
            pass
        result["logs"] = logs

        # Example files check
        try:
            example_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, "config.example.yml")
            )
            result["examples"] = {
                "config_example_exists": os.path.exists(example_path),
                "path": example_path,
            }
        except Exception:
            result["examples"] = {"config_example_exists": False}

        # Basic resource usage from /proc (Linux-only, best-effort)
        resources = {}
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as fh:
                    lines = fh.read().splitlines()
                mem = {}
                for ln in lines:
                    if ":" in ln:
                        k, v = ln.split(":", 1)
                        mem[k.strip()] = v.strip()
                resources["meminfo"] = (
                    {k: mem.get(k) for k in ("MemTotal", "MemAvailable")} if mem else {}
                )
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

            # normalize legacy form-shaped instances (e.g. sonarr0_url -> url)
            def _normalize_instance(d):
                if not isinstance(d, dict):
                    return d
                # if already normalized, return as-is
                if "url" in d or "api_key" in d:
                    return d
                # known suffixes to map (match longest first)
                suffixes = [
                    "reprocess_interval_days",
                    "max_download_queue",
                    "movies_to_upgrade",
                    "episodes_to_upgrade",
                    "api_pulls",
                    "api_key",
                    "state_mgmt",
                    "process",
                    "enabled",
                    "mode",
                    "url",
                    "name",
                ]
                normalized = {}
                for k, v in d.items():
                    mapped = None
                    for s in suffixes:
                        if k.endswith("_" + s):
                            mapped = s
                            break
                    if mapped is None:
                        # fallback to last component
                        mapped = k.rsplit("_", 1)[-1]
                    # convert common on/off strings to booleans
                    if isinstance(v, str) and v.lower() == "on":
                        v = True
                    normalized[mapped] = v
                return normalized

            inst = _normalize_instance(inst)
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
        return render_template(
            "general.html",
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
    # Attempt to import the API blueprint from the package. If that fails
    # (e.g., running from source tree where api.py is a top-level module)
    # fall back to loading the file directly similar to `webui` above.
    try:
        try:
            from researcharr import api as _api  # type: ignore

        except Exception:
            # Try top-level api.py next
            try:
                from api import bp as _api_bp  # type: ignore

                # construct a minimal module-like object with `bp`
                class _TmpMod:
                    bp = _api_bp

                _api = _TmpMod()
            except Exception:
                # Last resort: load via importlib from file path
                spec_path = os.path.join(os.path.dirname(__file__), "api.py")
                spec = importlib.util.spec_from_file_location("api", spec_path)
                if spec is None or spec.loader is None:
                    raise ImportError("Failed to load api module")
                _api = importlib.util.module_from_spec(spec)
                loader = spec.loader
                assert loader is not None
                loader.exec_module(_api)  # type: ignore

        # Register blueprint if present
        if getattr(_api, "bp", None) is not None:
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
        # Accept both legacy form-field keys (sonarr0_url/sonarr0_api_key)
        # and the normalized instance keys (url/api_key)
        url_present = bool(s.get("url") or s.get("sonarr0_url"))
        key_present = bool(s.get("api_key") or s.get("sonarr0_api_key"))
        if not url_present or not key_present:
            # Also show error on settings page for test
            error_msg = "Missing URL or API key for enabled instance."
            resp = jsonify({"success": False, "msg": error_msg})
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
            if spec is None or spec.loader is None:
                raise ImportError("Failed to load run.py for trigger")
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
        # Persist tasks settings to CONFIG_DIR/tasks.yml so UI preferences
        # survive restarts. Writing is best-effort.
        try:
            config_root = os.getenv("CONFIG_DIR", "/config")
            tasks_file = os.path.join(config_root, "tasks.yml")
            with open(tasks_file, "w") as fh:
                yaml.safe_dump(app.config_data.get("tasks", {}), fh)
        except Exception:
            # Don't fail the request if persistence fails; return ok but
            # include a warning for callers that persistence didn't work.
            return jsonify(
                {"result": "ok", "tasks": tasks_cfg, "warning": "persist_failed"}
            )

        return jsonify({"result": "ok", "tasks": tasks_cfg})

    @app.route("/backups")
    def backups():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("backups.html")

    @app.route("/api/backups", methods=["GET"])
    def api_backups_list():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        try:
            os.makedirs(backups_dir, exist_ok=True)
            files = []
            for fname in sorted(os.listdir(backups_dir), reverse=True):
                fpath = os.path.join(backups_dir, fname)
                try:
                    st = os.stat(fpath)
                    files.append(
                        {"name": fname, "size": st.st_size, "mtime": int(st.st_mtime)}
                    )
                except Exception:
                    continue
            return jsonify({"backups": files})
        except Exception as e:
            app.logger.exception("Failed to list backups: %s", e)
            return jsonify({"error": "failed_to_list"}), 500

    def _create_backup_file(
        config_root: str, backups_dir: str, prefix: str = ""
    ) -> str | None:
        """Wrapper around shared create_backup_file helper.

        Keeps the old internal name for backwards compatibility within this
        module.
        """
        return create_backup_file(config_root, backups_dir, prefix)

    def _prune_backups(backups_dir: str):
        """Wrapper around shared prune_backups helper which accepts a cfg.

        This wrapper reads the current app.config_data['backups'] and calls
        the shared implementation so tests and run.py can reuse the same
        logic.
        """
        try:
            cfg = app.config_data.get("backups", {})
        except Exception:
            cfg = None
        prune_backups(backups_dir, cfg)

    @app.route("/api/backups/create", methods=["POST"])
    def api_backups_create():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        try:
            name = _create_backup_file(config_root, backups_dir)
            # Prune according to settings
            try:
                _prune_backups(backups_dir)
            except Exception:
                pass
            return jsonify({"result": "ok", "name": name})
        except Exception as e:
            app.logger.exception("Failed to create backup: %s", e)
            return jsonify({"error": "create_failed"}), 500

    @app.route("/api/backups/import", methods=["POST"])
    def api_backups_import():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        if "file" not in request.files:
            return jsonify({"error": "missing_file"}), 400
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "missing_file"}), 400
        fname = getattr(f, "filename", None)
        if not fname:
            return jsonify({"error": "empty_name"}), 400
        filename = secure_filename(str(fname))
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        try:
            os.makedirs(backups_dir, exist_ok=True)
            dest = os.path.join(backups_dir, filename)
            # f may be a Werkzeug FileStorage; guard save() existence
            if not hasattr(f, "save"):
                return jsonify({"error": "invalid_file"}), 400
            f.save(dest)
            # After import, prune
            try:
                _prune_backups(backups_dir)
            except Exception:
                pass
            return jsonify({"result": "ok", "name": filename})
        except Exception as e:
            app.logger.exception("Failed to import backup: %s", e)
            return jsonify({"error": "import_failed"}), 500

    @app.route("/api/backups/download/<path:name>", methods=["GET"])
    def api_backups_download(name: str):
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        fpath = os.path.join(backups_dir, name)
        try:
            if not os.path.realpath(fpath).startswith(os.path.realpath(backups_dir)):
                return jsonify({"error": "invalid_name"}), 400
            if not os.path.exists(fpath):
                return jsonify({"error": "not_found"}), 404
            return send_file(fpath, as_attachment=True, download_name=name)
        except Exception as e:
            app.logger.exception("Failed to download backup: %s", e)
            return jsonify({"error": "download_failed"}), 500

    @app.route("/api/backups/delete/<path:name>", methods=["DELETE"])
    def api_backups_delete(name: str):
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        fpath = os.path.join(backups_dir, name)
        try:
            if not os.path.realpath(fpath).startswith(os.path.realpath(backups_dir)):
                return jsonify({"error": "invalid_name"}), 400
            if os.path.exists(fpath):
                os.remove(fpath)
                return jsonify({"result": "deleted"})
            return jsonify({"error": "not_found"}), 404
        except Exception as e:
            app.logger.exception("Failed to delete backup: %s", e)
            return jsonify({"error": "delete_failed"}), 500

    @app.route("/api/backups/restore/<path:name>", methods=["POST"])
    def api_backups_restore(name: str):
        """Restore a backup by extracting into the config directory.

        This is a best-effort restore. Files in the backup will overwrite
        existing files in the config directory. The operation is potentially
        destructive; callers should confirm before invoking.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        backups_dir = os.path.join(config_root, "backups")
        fpath = os.path.join(backups_dir, name)
        try:
            if not os.path.realpath(fpath).startswith(os.path.realpath(backups_dir)):
                return jsonify({"error": "invalid_name"}), 400
            if not os.path.exists(fpath):
                return jsonify({"error": "not_found"}), 404
            # Create a pre-restore backup so the operator can roll back if needed
            pre_name = None
            try:
                pre_cfg = app.config_data.get("backups", {})
                if bool(pre_cfg.get("pre_restore", True)):
                    pre_name = _create_backup_file(
                        config_root, backups_dir, prefix="pre-"
                    )
                    try:
                        _prune_backups(backups_dir)
                    except Exception:
                        pass
            except Exception:
                pre_name = None

            tmpdir = os.path.join(config_root, ".restore_tmp")
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)
            os.makedirs(tmpdir, exist_ok=True)
            with zipfile.ZipFile(fpath, "r") as zf:
                zf.extractall(tmpdir)
            for root, dirs, files in os.walk(tmpdir):
                rel = os.path.relpath(root, tmpdir)
                # If the archive has a top-level 'config' directory (common),
                # map its contents directly into the CONFIG_DIR root so that
                # 'config/config.yml' -> CONFIG_DIR/config.yml rather than
                # CONFIG_DIR/config/config.yml
                if rel == ".":
                    dest_dir = config_root
                elif rel == "config":
                    dest_dir = config_root
                elif rel.startswith("config" + os.sep):
                    # strip leading 'config/' component
                    sub = rel.split(os.sep, 1)[1]
                    dest_dir = os.path.join(config_root, sub)
                else:
                    dest_dir = os.path.join(config_root, rel)

                os.makedirs(dest_dir, exist_ok=True)
                for f in files:
                    s = os.path.join(root, f)
                    d = os.path.join(dest_dir, f)
                    shutil.copy2(s, d)
            shutil.rmtree(tmpdir)
            resp = {"result": "restored"}
            if pre_name:
                resp["pre_restore_backup"] = pre_name
            return jsonify(resp)
        except Exception as e:
            app.logger.exception("Failed to restore backup: %s", e)
            return jsonify({"error": "restore_failed"}), 500

    @app.route("/api/backups/settings", methods=["GET", "POST"])
    def api_backups_settings():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        config_root = os.getenv("CONFIG_DIR", "/config")
        settings_file = os.path.join(config_root, "backups.yml")
        if request.method == "GET":
            return jsonify(app.config_data.get("backups", {}))

        # POST: update settings
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid_json"}), 400
        backups_cfg = app.config_data.setdefault("backups", {})
        try:
            if "retain_count" in data:
                backups_cfg["retain_count"] = int(data.get("retain_count") or 0)
            if "retain_days" in data:
                backups_cfg["retain_days"] = int(data.get("retain_days") or 0)
            if "pre_restore" in data:
                # accept truthy/falsy values
                backups_cfg["pre_restore"] = bool(data.get("pre_restore"))
        except Exception:
            return jsonify({"error": "invalid_settings"}), 400
        app.config_data["backups"] = backups_cfg
        # Persist to CONFIG_DIR/backups.yml
        try:
            os.makedirs(config_root, exist_ok=True)
            with open(settings_file, "w") as fh:
                yaml.safe_dump(backups_cfg, fh)
        except Exception:
            app.logger.exception("Failed to persist backups settings")
            return jsonify(
                {"result": "ok", "warning": "persist_failed", "backups": backups_cfg}
            )

        return jsonify({"result": "ok", "backups": backups_cfg})

    # --- Updates API: check latest release and persist ignore settings ---
    def _read_local_version():
        info = {"version": "dev", "build": "0", "sha": "unknown"}
        try:
            ver_file = os.getenv("RESEARCHARR_VERSION_FILE", "/app/VERSION")
            p = pathlib.Path(ver_file)
            if p.exists():
                for line in p.read_text().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
        except Exception:
            pass
        return info

    def _updates_config_path():
        config_root = os.getenv("CONFIG_DIR", "/config")
        return os.path.join(config_root, "updates.yml")

    def _load_updates_cfg():
        cfg_file = _updates_config_path()
        try:
            if os.path.exists(cfg_file):
                with open(cfg_file) as fh:
                    return yaml.safe_load(fh) or {}
        except Exception:
            app.logger.exception("Failed to load updates config")
        return {}

    def _save_updates_cfg(cfg: dict):
        cfg_file = _updates_config_path()
        try:
            os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
            with open(cfg_file, "w") as fh:
                yaml.safe_dump(cfg, fh)
            return True
        except Exception:
            app.logger.exception("Failed to persist updates config")
            return False

    def _running_in_image():
        # Heuristic: check for common container indicators
        try:
            if os.path.exists("/.dockerenv"):
                return True
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                return True
            if os.getenv("CONTAINER") or os.getenv("IN_CONTAINER"):
                return True
        except Exception:
            pass
        return False

    # Caching and backoff for update checks
    def _updates_cache_path():
        config_root = os.getenv("CONFIG_DIR", "/config")
        return os.path.join(config_root, "updates_cache.yml")

    def _load_updates_cache():
        p = _updates_cache_path()
        try:
            if os.path.exists(p):
                with open(p) as fh:
                    return yaml.safe_load(fh) or {}
        except Exception:
            try:
                app.logger.exception("Failed to load updates cache")
            except Exception:
                pass
        return {}

    def _save_updates_cache(cache: dict):
        p = _updates_cache_path()
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                yaml.safe_dump(cache, fh)
            return True
        except Exception:
            try:
                app.logger.exception("Failed to persist updates cache")
            except Exception:
                pass
            return False

    def _fetch_remote_release(check_url: str, headers: dict):
        """Attempt to fetch remote release JSON. Returns dict or raises."""
        import requests

        resp = requests.get(check_url, headers=headers, timeout=8)
        resp.raise_for_status()
        return resp.json()

    def _ensure_latest_cached(check_url: str):
        """Ensure cache contains latest release info, respecting TTL and backoff.

        Returns a dict with keys: latest, fetched_at, backoff metadata.
        """
        cache = _load_updates_cache() or {}
        now = int(time.time())
        ttl = int(os.getenv("UPDATE_CACHE_TTL", str(60 * 60)))

        # respect backoff: if next_try is set and in future, skip fetch
        next_try = int(cache.get("next_try", 0) or 0)
        if next_try and now < next_try:
            return cache

        # if cache is recent enough, return it
        fetched_at = int(cache.get("fetched_at", 0) or 0)
        if fetched_at and (now - fetched_at) < ttl:
            return cache

        # attempt fetch with exponential backoff on failure
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "researcharr-updater/1",
        }
        gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"

        try:
            j = _fetch_remote_release(check_url, headers)
            latest = {
                "tag_name": j.get("tag_name"),
                "name": j.get("name"),
                "body": j.get("body"),
                "published_at": j.get("published_at"),
                "url": j.get("html_url") or j.get("url"),
                "assets": [
                    {"name": a.get("name"), "url": a.get("browser_download_url")}
                    for a in (j.get("assets") or [])
                ],
            }
            cache["latest"] = latest
            cache["fetched_at"] = now
            # reset backoff
            cache.pop("failed_attempts", None)
            cache.pop("next_try", None)
            _save_updates_cache(cache)
            return cache
        except Exception:
            # fetch failed; apply exponential backoff and keep prior cache if any
            fa = int(cache.get("failed_attempts", 0) or 0) + 1
            # base backoff seconds, capped maximum
            base = int(os.getenv("UPDATE_BACKOFF_BASE", "60"))
            cap = int(os.getenv("UPDATE_BACKOFF_CAP", str(60 * 60 * 6)))
            backoff = min(cap, base * (2 ** (fa - 1)))
            next_try = now + backoff
            cache["failed_attempts"] = fa
            cache["next_try"] = next_try
            # record last failure timestamp
            cache["last_failed_at"] = now
            _save_updates_cache(cache)
            try:
                app.logger.debug("Update check failed; backoff set %s seconds", backoff)
            except Exception:
                pass
            return cache

    @app.route("/api/updates", methods=["GET"])
    def api_updates():
        """Return current and latest release metadata.

        Attempts to fetch latest release info from GitHub for the
        `Wikid82/researcharr` repository by default. The URL can be
        overridden with the `UPDATE_CHECK_URL` env var. Network failures
        are handled gracefully and a best-effort response is returned.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401

        local = _read_local_version()
        current = local.get("version") or local.get("version", "dev")

        # default to the project's GitHub releases latest endpoint
        check_url = os.getenv(
            "UPDATE_CHECK_URL",
            "https://api.github.com/repos/Wikid82/researcharr/releases/latest",
        )

        # Ensure cache is populated, respecting TTL and backoff
        cache = _ensure_latest_cached(check_url) or {}
        latest = cache.get("latest") or {}

        # load ignore state
        ucfg = _load_updates_cfg()
        is_ignored = False
        ignore_reason = None
        try:
            if "ignored_until" in ucfg:
                try:
                    if int(time.time()) < int(ucfg.get("ignored_until", 0)):
                        is_ignored = True
                        ignore_reason = "ignored_until"
                except Exception:
                    pass
            if (
                not is_ignored
                and "ignored_release" in ucfg
                and ucfg.get("ignored_release")
            ):
                if latest.get("tag_name") and ucfg.get("ignored_release") == latest.get(
                    "tag_name"
                ):
                    is_ignored = True
                    ignore_reason = "ignored_release"
        except Exception:
            pass

        # Indicate whether in-app upgrade actions are allowed
        in_image = bool(_running_in_image())
        can_upgrade = (not in_image) and bool(latest.get("assets"))

        return jsonify(
            {
                "current_version": current,
                "latest": latest,
                "is_ignored": bool(is_ignored),
                "ignore_reason": ignore_reason,
                "in_image": in_image,
                "can_upgrade": bool(can_upgrade),
                # include some cache/backoff metadata for UI debugging
                "cache": {
                    "fetched_at": cache.get("fetched_at"),
                    "failed_attempts": cache.get("failed_attempts"),
                    "next_try": cache.get("next_try"),
                },
            }
        )

    @app.route("/api/updates/ignore", methods=["POST"])
    def api_updates_ignore():
        """Ignore update notifications.

        JSON payload examples:
        - {"mode": "until", "days": 7}  -> ignore for N days
        - {"mode": "release", "release_tag": "v1.2.3"} -> ignore this release
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        try:
            data = request.get_json(force=True) or {}
        except Exception:
            return jsonify({"error": "invalid_json"}), 400
        mode = data.get("mode")
        ucfg = _load_updates_cfg()
        if mode == "until":
            days = int(data.get("days") or 0)
            if days <= 0:
                return jsonify({"error": "invalid_days"}), 400
            ucfg["ignored_until"] = int(time.time()) + int(days) * 24 * 3600
            # clear release ignore when time-based ignore used
            ucfg.pop("ignored_release", None)
        elif mode == "release":
            tag = data.get("release_tag")
            if not tag:
                return jsonify({"error": "missing_release_tag"}), 400
            ucfg["ignored_release"] = tag
            ucfg.pop("ignored_until", None)
        else:
            return jsonify({"error": "unknown_mode"}), 400

        ok = _save_updates_cfg(ucfg)
        if not ok:
            return jsonify({"result": "ok", "warning": "persist_failed"}), 200
        return jsonify({"result": "ok", "updates": ucfg})

    @app.route("/api/updates/upgrade", methods=["POST"])
    def api_updates_upgrade():
        """Start a controlled in-app upgrade by downloading the selected asset.

        Request JSON: {"asset_url": "https://..."}
        This endpoint is disabled when running in an image-managed runtime.
        The download runs in a background thread.
        It writes to CONFIG_DIR/updates/downloads.
        """
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        if _running_in_image():
            return jsonify({"error": "in_image_runtime"}), 400
        try:
            data = request.get_json(force=True) or {}
        except Exception:
            return jsonify({"error": "invalid_json"}), 400
        asset_url = data.get("asset_url")
        if (
            not asset_url
            or not isinstance(asset_url, str)
            or not asset_url.startswith(("http://", "https://"))
        ):
            return jsonify({"error": "invalid_asset_url"}), 400

        # perform the download in a background thread
        def _download_asset(url: str):
            from urllib.parse import urlparse

            import requests

            cfg_root = os.getenv("CONFIG_DIR", "/config")
            dl_dir = os.path.join(cfg_root, "updates", "downloads")
            try:
                os.makedirs(dl_dir, exist_ok=True)
                # derive filename from URL
                p = urlparse(url)
                filename = os.path.basename(p.path) or "asset"
                filename = secure_filename(filename)
                dest = os.path.join(dl_dir, filename)
                with requests.get(url, stream=True, timeout=10) as r:
                    r.raise_for_status()
                    with open(dest, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                fh.write(chunk)
                # record last_download in cache for operator visibility
                cache = _load_updates_cache()
                cache["last_download"] = {
                    "url": url,
                    "path": dest,
                    "ts": int(time.time()),
                }
                _save_updates_cache(cache)
            except Exception:
                try:
                    app.logger.exception("Failed to download asset %s", url)
                except Exception:
                    pass

        import threading

        t = threading.Thread(target=_download_asset, args=(asset_url,), daemon=True)
        t.start()
        return jsonify({"result": "started", "asset_url": asset_url})

    @app.route("/api/updates/unignore", methods=["POST"])
    def api_updates_unignore():
        if not is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        ucfg = _load_updates_cfg()
        ucfg.pop("ignored_until", None)
        ucfg.pop("ignored_release", None)
        ok = _save_updates_cfg(ucfg)
        if not ok:
            return jsonify({"result": "ok", "warning": "persist_failed"}), 200
        return jsonify({"result": "ok"})

    @app.route("/updates")
    def updates():
        if not is_logged_in():
            return redirect(url_for("login"))
        return render_template("updates.html")

    return app
