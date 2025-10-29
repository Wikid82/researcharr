"""Entry point module (renamed from top-level `researcharr.py`).

This module preserves the previous top-level script behavior but avoids
shadowing the package name `researcharr` used by the library code. Tests
and templates were updated to reference `entrypoint.py` where necessary.
"""

import logging
import os
import sqlite3
from typing import Any, cast

# Allow the top-level module `entrypoint.py` to behave like a package for
# legacy imports such as `import researcharr.plugins.example_sonarr` when
# executed from the repository root. When a module defines a __path__
# attribute it is treated as a package by the import system; include both
# the module directory and the nested `researcharr/` package directory so
# submodule imports resolve.
__path__ = [
    os.path.dirname(__file__),
    os.path.join(os.path.dirname(__file__), "researcharr"),
]

if "requests" not in globals():
    import requests

if "yaml" not in globals():
    import yaml

DB_PATH = "researcharr.db"


def init_db(db_path=None):
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS radarr_queue ("
        "movie_id INTEGER PRIMARY KEY, last_processed TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS sonarr_queue ("
        "episode_id INTEGER PRIMARY KEY, last_processed TEXT)"
    )
    conn.commit()
    conn.close()


def setup_logger(name: str, log_file: str, level: int | None = None):
    logger = logging.getLogger(name)
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
        not i.get("enabled")
        or (i.get("url", "").startswith("http") and i.get("api_key"))
        for i in instances
    )


def check_radarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Radarr URL or API key")
        return False
    try:
        r = requests.get(url)
        if r.status_code == 200:
            logger.info("Radarr connection successful.")
            return True
        else:
            logger.error("Radarr connection failed with status %s", r.status_code)
            return False
    except Exception as e:
        logger.error("Radarr connection failed: %s", e)
        return False


def check_sonarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Sonarr URL or API key")
        return False
    try:
        r = requests.get(url)
        if r.status_code == 200:
            logger.info("Sonarr connection successful.")
            return True
        else:
            logger.error("Sonarr connection failed with status %s", r.status_code)
            return False
    except Exception as e:
        logger.error("Sonarr connection failed: %s", e)
        return False


def load_config(path="config.yml"):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path) as f:
        config = yaml.safe_load(f)
        if not config:
            return {}
        return config


def create_metrics_app():
    from flask import Flask, jsonify

    app = Flask("metrics")
    # Cast to Any so static type checkers (Pylance/mypy) allow assigning
    # arbitrary attributes used by the tests (e.g. `metrics`).
    app = cast(Any, app)
    app.metrics = {"requests_total": 0, "errors_total": 0}

    @app.before_request
    def _before():
        app.metrics["requests_total"] += 1

    @app.route("/health")
    def health():
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
            db_status = "ok"
        except Exception:
            db_status = "error"
        return jsonify({
            "status": "ok",
            "db": db_status,
            "config": "ok",
            "threads": 1,
            "time": "2025-10-23T00:00:00Z",
        })

    @app.route("/metrics")
    def metrics_endpoint():
        return jsonify(app.metrics)

    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(e):
        app.metrics["errors_total"] += 1
        return jsonify({"error": "internal error"}), 500

    return app
