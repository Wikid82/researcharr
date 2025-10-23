# ... code for researcharr.py ...
# ... code for app.py ...

import requests
import sqlite3
import yaml
import os

DB_PATH = "researcharr.db"

def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS radarr_queue (id INTEGER PRIMARY KEY, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sonarr_queue (id INTEGER PRIMARY KEY, data TEXT)")
    conn.commit()
    conn.close()

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
        r = requests.get(url)
        if r.status_code == 200:
            logger.info("Radarr connection successful")
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
            logger.info("Sonarr connection successful")
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
            raise yaml.YAMLError("Empty config")
        if "radarr" not in config or "sonarr" not in config:
            raise KeyError("Missing required fields")
        return config

def create_metrics_app():
    from flask import Flask, jsonify
    app = Flask("metrics")
    app.metrics = {"requests_total": 0, "errors_total": 0}

    @app.route("/health")
    def health():
        # Simulate DB check
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
            db_status = "ok"
        except Exception:
            db_status = "error"
        return jsonify({"status": "ok", "db": db_status})

    @app.route("/metrics")
    def metrics_endpoint():
        app.metrics["requests_total"] += 1
        return jsonify(app.metrics)

    @app.errorhandler(500)
    def handle_error(e):
        app.metrics["errors_total"] += 1
        return jsonify({"error": "internal error"}), 500

    return app