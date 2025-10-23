
import requests
import sqlite3
import yaml

def init_db():
    # Dummy implementation
    pass

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
        return r.status_code == 200
    except Exception:
        logger.error("Radarr connection failed")
        return False

def check_sonarr_connection(url, api_key, logger):
    if not url or not api_key:
        logger.warning("Missing Sonarr URL or API key")
        return False
    try:
        r = requests.get(url)
        return r.status_code == 200
    except Exception:
        logger.error("Sonarr connection failed")
        return False

def load_config(path="config.yml"):
    with open(path) as f:
        return yaml.safe_load(f)

def create_metrics_app():
    from flask import Flask, jsonify
    app = Flask("metrics")
    metrics = {"requests_total": 0, "errors_total": 0}

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/metrics")
    def metrics_endpoint():
        metrics["requests_total"] += 1
        return jsonify(metrics)

    return app