# --- Health and Metrics Endpoints ---
from flask import Flask, jsonify, request

APP_METRICS = {
    "requests_total": 0,
    "errors_total": 0,
    "last_health_check": None,
    "radarr_queue_length": 0,
    "sonarr_queue_length": 0,
}

def increment_metric(name):
    if name in APP_METRICS:
        APP_METRICS[name] += 1

def create_metrics_app():
    app = Flask("metrics")

    @app.before_request
    def before_any_request():
        APP_METRICS["requests_total"] += 1

    @app.errorhandler(Exception)
    def handle_error(e):
        APP_METRICS["errors_total"] += 1
        return str(e), 500

    @app.route("/health", methods=["GET"])
    def health():
        APP_METRICS["last_health_check"] = time.time()
        status = {
            "status": "ok",
            "db": True,
            "config": True,
            "threads": True,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }
        return jsonify(status)

    @app.route("/metrics", methods=["GET"])
    def metrics():
        return jsonify(APP_METRICS)

    return app

# Standard library imports

import logging
import sys
import os
import sqlite3
import threading
import time

import requests
import yaml
from logging.handlers import RotatingFileHandler

try:
    from pythonjsonlogger import jsonlogger
    _HAS_JSON_LOGGER = True
except ImportError:
    _HAS_JSON_LOGGER = False
# --- Database Setup ---

def setup_logging(loglevel=None):
    logger = logging.getLogger()
    # Set log level from config or default to DEBUG
    if loglevel is None:
        # Try to read from config file
        try:
            import yaml
            config_path = os.environ.get("USER_CONFIG_PATH") or globals().get("USER_CONFIG_PATH") or "/config/config.yml"
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            loglevel = config.get("researcharr", {}).get("loglevel", "DEBUG")
        except Exception:
            loglevel = "DEBUG"
    logger.setLevel(getattr(logging, loglevel, logging.DEBUG))

    # Remove all handlers associated with the root logger object (avoid duplicate logs)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    if _HAS_JSON_LOGGER:
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    else:
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler
    file_handler = RotatingFileHandler('app.log', maxBytes=2*1024*1024, backupCount=2)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def watch_loglevel_config(interval=10):
    """Background thread to watch for loglevel changes in config and update live."""
    config_path = os.environ.get("USER_CONFIG_PATH") or globals().get("USER_CONFIG_PATH") or "/config/config.yml"
    last_loglevel = None
    while True:
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            loglevel = config.get("researcharr", {}).get("loglevel", "DEBUG")
            logger = logging.getLogger()
            if loglevel != last_loglevel:
                logger.setLevel(getattr(logging, loglevel, logging.DEBUG))
                last_loglevel = loglevel
        except Exception:
            pass
        time.sleep(interval)

setup_logging()

# Start background watcher for live loglevel changes
threading.Thread(target=watch_loglevel_config, args=(5,), daemon=True).start()

# --- Database Setup ---


def init_db():
    """
    Initializes the SQLite database and creates tables if they don't exist.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Radarr queue table with last_processed
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS radarr_queue (
            movie_id INTEGER PRIMARY KEY,
            last_processed TIMESTAMP
        )
        """
    )
    # Sonarr queue table with last_processed
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sonarr_queue (
            episode_id INTEGER PRIMARY KEY,
            last_processed TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


# --- Connection Status Checks ---
def check_radarr_connection(url, key, logger):
    try:
        if url and key:
            resp = requests.get(
                url + "/api/v3/system/status",
                headers={"Authorization": key},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("Radarr connection successful.")
            else:
                logger.error(
                    f"Radarr connection failed: HTTP {resp.status_code} - "
                    f"{resp.text}"
                )
        else:
            logger.warning("Radarr URL or API key not set; skipping connection test.")
    except Exception as e:
        logger.error(f"Radarr connection error: {e}")


def check_sonarr_connection(url, key, logger):
    try:
        if url and key:
            resp = requests.get(
                url + "/api/v3/system/status",
                headers={"Authorization": key},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("Sonarr connection successful.")
            else:
                logger.error(
                    f"Sonarr connection failed: HTTP {resp.status_code} - "
                    f"{resp.text}"
                )
        else:
            logger.warning("Sonarr URL or API key not set; skipping connection test.")
    except Exception as e:
        logger.error(f"Sonarr connection error: {e}")


# --- Database Setup ---
DB_PATH = "/config/researcharr.db"





# --- Connection Status Checks ---


# --- New: Download queue check and main logic for each instance ---

def get_radarr_queue_length(url, key, logger):
    try:
        resp = requests.get(
            url + "/api/v3/queue", headers={"Authorization": key}, timeout=10
        )
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            logger.warning(
                f"Failed to get Radarr queue: HTTP {resp.status_code}"
            )
    except Exception as e:
        logger.warning(f"Error getting Radarr queue: {e}")
    return 0



def get_sonarr_queue_length(url, key, logger):
    try:
        resp = requests.get(
            url + "/api/v3/queue", headers={"Authorization": key}, timeout=10
        )
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            logger.warning(
                f"Failed to get Sonarr queue: HTTP {resp.status_code}"
            )
    except Exception as e:
        logger.warning(f"Error getting Sonarr queue: {e}")
    return 0


# --- Radarr instance processing ---


# --- Config Loader ---
def load_config(path=None):
    """
    Loads and returns the YAML config as a dict.
    Accepts optional path for testability.
    """

    # Allow override by argument, then env var, then default
    if path is not None:
        config_path = path
    else:
        config_path = (
            os.environ.get("USER_CONFIG_PATH")
            or globals().get("USER_CONFIG_PATH")
            or "/config/config.yml"
        )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def countdown(minutes, logger=None):
    import sys
    import time

    if logger:
        logger.info(
            f"Countdown: {minutes} minutes until next scheduled run " f"(test mode)"
        )
    for i in range(minutes, 0, -1):
        sys.stdout.write(f"\rNext run in {i} minute(s)... ")
        sys.stdout.flush()
        time.sleep(60)
    sys.stdout.write("\n")
    if logger:
        logger.info(
            (
                "Countdown complete. If this is a test, the next cron run "
                "should now occur."
            )
        )


def has_valid_url_and_key(instances):
    for inst in instances:
        if (
            inst.get("enabled", False)
            and inst.get("url", "").startswith(("http://", "https://"))
            and inst.get("api_key", "")
        ):
            return True
    return False



def main():
    # --- Force TZ environment variable and tzset at startup ---
    try:
        config = load_config()
        _tz = config.get("researcharr", {}).get("timezone", "America/New_York")
        os.environ["TZ"] = _tz
        import time as _time
        _time.tzset()
    except Exception as e:
        print(f"[WARNING] Could not set TZ at startup: {e}")

    main_logger = logging.getLogger("main_logger")
    radarr_logger = logging.getLogger("radarr_logger")
    sonarr_logger = logging.getLogger("sonarr_logger")

    # Initialize the database
    init_db()

    # Load configuration from YAML
    config = load_config()

    # Set researcharr (general) variables (if needed elsewhere, assign here)

    # --- Multi-instance support ---
    radarr_instances = config.get("radarr", [])
    sonarr_instances = config.get("sonarr", [])

    # Log connection status for all enabled Radarr/Sonarr instances
    for idx, radarr_cfg in enumerate(
        [r for r in radarr_instances if r.get("enabled", False)]
    ):
        url = radarr_cfg.get("url", "")
        key = radarr_cfg.get("api_key", "")
        check_radarr_connection(url, key, radarr_logger)

    for idx, sonarr_cfg in enumerate(
        [s for s in sonarr_instances if s.get("enabled", False)]
    ):
        url = sonarr_cfg.get("url", "")
        key = sonarr_cfg.get("api_key", "")
        check_sonarr_connection(url, key, sonarr_logger)

    # --- Startup validation for Radarr/Sonarr config ---
    if not has_valid_url_and_key(radarr_instances) and not has_valid_url_and_key(
        sonarr_instances
    ):
        main_logger.warning(
            "No enabled Radarr or Sonarr instance has a valid URL "
            "(must start with http:// or https://) and API key. "
            "Please update your config.yml using the web UI. "
            "The app will not run jobs until this is fixed."
        )
        print(
            "WARNING: No enabled Radarr or Sonarr instance has a valid URL "
            "(must start with http:// or https://) and API key. "
            "Please update your config.yml using the web UI. "
            "The app will not run jobs until this is fixed."
        )

    # Only run countdown if started with a special env var
    # (to avoid running in cron jobs)
    if os.environ.get("RESEARCHARR_STARTUP_COUNTDOWN", "0") == "1":
        countdown(5, main_logger)  # 5 minute countdown for test/demo



if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Run Flask metrics/health endpoints
        metrics_app = create_metrics_app()
        metrics_app.run(host="0.0.0.0", port=5001)
    else:
        main()
