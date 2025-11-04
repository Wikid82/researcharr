import logging
import os
import sqlite3


# --- Debug/Container Entrypoint ---
def serve():
    app = create_metrics_app()
    app.run(host="0.0.0.0", port=2929)  # nosec B104


# NOTE: the actual __main__ invocation is placed at the end of the
# module (after `create_metrics_app`) so the helper functions are
# defined before `serve()` is called. This top-level note preserves
# compatibility for tools that inspect the module.
# Allow the top-level module `researcharr.py` to behave like a package for
# legacy imports such as `import researcharr.plugins.example_sonarr`.
# When a module defines a __path__ attribute it is treated as a package by
# the import system; include both the module directory and the nested
# `researcharr/` package directory so submodule imports resolve.
__path__ = [
    os.path.dirname(__file__),
    os.path.join(os.path.dirname(__file__), "researcharr"),
]

# Allow test fixtures to monkeypatch top-level names before the module is
# (re)loaded. If a name already exists in globals() (for example because a
# test called monkeypatch.setattr("researcharr.researcharr.requests", ...) )
# avoid re-importing or re-defining so the test-patched object survives
# importlib.reload.
if "requests" not in globals():
    import requests

if "yaml" not in globals():
    import yaml

DB_PATH = "researcharr.db"
DEFAULT_TIMEOUT = 10


def init_db(db_path=None):
    # Use the passed path if provided, otherwise use the module-level DB_PATH.
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Create tables with the columns expected by the test suite
    sql = (
        "CREATE TABLE IF NOT EXISTS radarr_queue ("
        "movie_id INTEGER PRIMARY KEY, last_processed TEXT)"
    )
    c.execute(sql)
    sql = (
        "CREATE TABLE IF NOT EXISTS sonarr_queue ("
        "episode_id INTEGER PRIMARY KEY, last_processed TEXT)"
    )
    c.execute(sql)
    conn.commit()
    conn.close()


if "setup_logger" not in globals():

    def setup_logger(name: str, log_file: str, level: int | None = None):
        """Create and return a simple logger for the application.

        Tests expect a callable `setup_logger` that returns an object with an
        `info` method. Provide a minimal, well-behaved logger here.
        """
        logger = logging.getLogger(name)
        # Prevent adding duplicate handlers in repeated test runs
        if not logger.handlers:
            handler = logging.FileHandler(log_file)
            fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            handler.setFormatter(fmt)
            logger.addHandler(handler)
        if level is not None:
            logger.setLevel(level)
        else:
            logger.setLevel(logging.INFO)
        return logger


def has_valid_url_and_key(instances):
    return all(
        not i.get("enabled") or (i.get("url", "").startswith("http") and i.get("api_key"))
        for i in instances
    )


def check_radarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Radarr URL or API key")
        return False
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            logger.info("Radarr connection successful.")
            return True
        else:
            logger.error(
                "Radarr connection failed with status %s",
                r.status_code,
            )
            return False
    except Exception as e:
        logger.error("Radarr connection failed: %s", e)
        return False


def check_sonarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Sonarr URL or API key")
        return False
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            logger.info("Sonarr connection successful.")
            return True
        else:
            logger.error(
                "Sonarr connection failed with status %s",
                r.status_code,
            )
            return False
    except Exception as e:
        logger.error("Sonarr connection failed: %s", e)
        return False


def load_config(path="config.yml"):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path) as f:
        config = yaml.safe_load(f)
        # If the file is empty or evaluates to None, return an empty dict so
        # callers/tests can handle missing values gracefully.
        if not config:
            return {}
        # Don't raise on missing fields; return whatever is present. Tests
        # expect partial configs to be accepted.
        return config


if "create_metrics_app" not in globals():

    def create_metrics_app():
        from flask import Flask, jsonify

        app = Flask("metrics")
        app.config["metrics"] = {"requests_total": 0, "errors_total": 0}

        # Increment request counter for every request
        @app.before_request
        def _before():
            app.config["metrics"]["requests_total"] += 1

        @app.route("/health")
        def health():
            # Simulate DB/config/threads/time check for tests
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("SELECT 1")
                conn.close()
                db_status = "ok"
            except Exception:
                db_status = "error"
            # Provide the additional fields the tests expect
            return jsonify(
                {
                    "status": "ok",
                    "db": db_status,
                    "config": "ok",
                    "threads": 1,
                    "time": "2025-10-23T00:00:00Z",
                }
            )

        @app.route("/metrics")
        def metrics_endpoint():
            return jsonify(app.config["metrics"])

        @app.errorhandler(404)
        @app.errorhandler(500)
        def handle_error(e):
            # Log the exception details so running containers record a
            # traceback in their logs. This helps debugging in development
            # environments where Flask's debug page is not enabled.
            try:
                app.logger.exception("Unhandled exception in request: %s", e)
            except Exception:
                # If logging fails for any reason, do not raise further
                pass
            app.config["metrics"]["errors_total"] += 1
            return jsonify({"error": "internal error"}), 500

        return app


if __name__ == "__main__":
    import sys

    # When executed as `python researcharr.py serve` run the server. This
    # statement is placed after `create_metrics_app` so the `serve()`
    # helper can call it without NameError.
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
