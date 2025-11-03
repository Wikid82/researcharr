"""Package-level fallback implementation used by the import shim during tests.

This file provides a small, self-contained subset of the top-level
`researcharr.py` implementation so the package shim can load a module when
the repository's top-level `researcharr.py` is temporarily moved by tests.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

# Annotate fallback names up-front so mypy knows these may be None when
# the optional runtime dependencies aren't available in the environment.
requests: Any | None = None
yaml: Any | None = None

try:
    import requests  # type: ignore
except Exception:
    requests = None  # tests only need attribute access, not full runtime

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

DB_PATH = "researcharr.db"


def init_db(db_path: str | None = None) -> None:
    """Create minimal tables used by tests.

    The implementation is intentionally small and well-behaved so tests can
    call it whether the top-level module is present or not.
    """
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS radarr_queue ("
        "movie_id INTEGER PRIMARY KEY, "
        "last_processed TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS sonarr_queue ("
        "episode_id INTEGER PRIMARY KEY, "
        "last_processed TEXT)"
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
    logger.setLevel(level or logging.INFO)
    return logger


def has_valid_url_and_key(instances) -> bool:
    return all(
        not i.get("enabled") or (i.get("url", "").startswith("http") and i.get("api_key"))
        for i in instances
    )


def check_radarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Radarr URL or API key")
        return False
    if requests is None:
        logger.warning("requests not available in this environment")
        return False
    try:
        r = requests.get(url)
        if r.status_code == 200:
            logger.info("Radarr connection successful.")
            return True
        logger.error("Radarr connection failed with status %s", r.status_code)
        return False
    except Exception as e:
        logger.error("Radarr connection failed: %s", e)
        return False


def check_sonarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Sonarr URL or API key")
        return False
    if requests is None:
        logger.warning("requests not available in this environment")
        return False
    try:
        r = requests.get(url)
        if r.status_code == 200:
            logger.info("Sonarr connection successful.")
            return True
        logger.error("Sonarr connection failed with status %s", r.status_code)
        return False
    except Exception as e:
        logger.error("Sonarr connection failed: %s", e)
        return False


def load_config(path="config.yml"):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path) as f:
        config = yaml.safe_load(f) if yaml else {}
        return config or {}


def create_metrics_app():
    """Create a tiny Flask app with /health and /metrics used by tests."""
    try:
        from flask import Flask, jsonify
    except Exception:  # flask may not be available in some isolated checks

        class Dummy:
            def test_client(self):
                raise RuntimeError("flask not available")

        return Dummy()  # tests that require Flask will have it available

    app = Flask("metrics")
    app.metrics = {"requests_total": 0, "errors_total": 0}  # type: ignore[attr-defined]

    @app.before_request
    def _before():
        app.metrics["requests_total"] += 1  # type: ignore[attr-defined]

    @app.route("/health")
    def health():
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
            db_status = "ok"
        except Exception:
            db_status = "error"
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
        return jsonify(app.metrics)  # type: ignore[attr-defined]

    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(e):
        app.metrics["errors_total"] += 1  # type: ignore[attr-defined]
        return jsonify({"error": "internal error"}), 500

    return app


def serve() -> None:
    """Debug/Container entrypoint: create and run the metrics app.

    Starts the Flask metrics application on host 0.0.0.0 port 2929.
    This function provides the same entrypoint behavior as the top-level
    researcharr.py module for container and development use.
    """
    app = create_metrics_app()
    app.run(host="0.0.0.0", port=2929)
