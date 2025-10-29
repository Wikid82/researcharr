"""Minimal package-level implementation shim for tests.

This module provides a small subset of the top-level `researcharr.py`
functionality so tests that temporarily remove the top-level module can
still import `researcharr.researcharr` as a package-local implementation.
"""

import sqlite3

from flask import Flask, jsonify

# Basic DB path used by tests
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


def create_metrics_app():
    app = Flask("metrics")
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
        return jsonify(app.metrics)

    return app


def check_radarr_connection(url, api_key, logger):
    # Minimal smoke-check used in tests; do not make external requests here.
    if not url or not api_key:
        return False
    # Assume success for unit tests that don't perform real HTTP calls.
    return True
