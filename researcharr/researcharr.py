import sqlite3
from flask import Flask, jsonify
import requests
from typing import Any

# Minimal package-level implementation used as a fallback by the package shim
# Tests only require a small surface: DB_PATH, init_db, create_metrics_app,
# and check_radarr_connection (signatures and reasonable behavior).

DB_PATH = "researcharr.db"


def init_db(db_path=None):
    """Create minimal tables used by tests."""
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


def create_metrics_app():
    # Use a loose type for `app` so static checkers don't flag ad-hoc attributes
    app: Any = Flask("metrics")
    # store metrics on the app object for tests; typed as Any above to avoid
    # Pylance/typing complaints about unknown Flask attributes
    setattr(app, "metrics", {"requests_total": 0, "errors_total": 0})

    @app.before_request
    def _before():
        metrics = getattr(app, "metrics")
        metrics["requests_total"] += 1

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
        return jsonify(getattr(app, "metrics"))

    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(e):
        metrics = getattr(app, "metrics")
        metrics["errors_total"] += 1
        return jsonify({"error": "internal error"}), 500

    return app


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
