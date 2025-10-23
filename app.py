# Standard library imports
import logging
import os
import sqlite3
import requests
import yaml


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


# Create loggers
def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = logging.FileHandler(log_file, encoding="utf-8")
    # Add timezone info to log messages
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(message)s [%(levelname)s] [%(name)s] "
            "[%(process)d] [%(thread)d] [%(timezone)s]",
            datefmt="%m/%d/%Y %I:%M:%S %p",
        )
    )
    # Patch LogRecord to add timezone
    old_factory = logging.getLogRecordFactory()
    import time

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        try:
            record.timezone = time.tzname[0]
        except Exception:
            record.timezone = "Unknown"
        return record

    logging.setLogRecordFactory(record_factory)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


main_logger = None
radarr_logger = None
sonarr_logger = None


# --- Connection Status Checks ---


# --- New: Download queue check and main logic for each instance ---
def get_radarr_queue_length(url, key):
    try:
        resp = requests.get(
            url + "/api/v3/queue", headers={"Authorization": key}, timeout=10
        )
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            radarr_logger.warning(
                f"Failed to get Radarr queue: HTTP {resp.status_code}"
            )
    except Exception as e:
        radarr_logger.warning(f"Error getting Radarr queue: {e}")
    return 0


def get_sonarr_queue_length(url, key):
    try:
        resp = requests.get(
            url + "/api/v3/queue", headers={"Authorization": key}, timeout=10
        )
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            sonarr_logger.warning(
                f"Failed to get Sonarr queue: HTTP {resp.status_code}"
            )
    except Exception as e:
        sonarr_logger.warning(f"Error getting Sonarr queue: {e}")
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
    global main_logger, radarr_logger, sonarr_logger

    # --- Force TZ environment variable and tzset at startup ---
    try:
        config = load_config()
        _tz = config.get("researcharr", {}).get("timezone", "America/New_York")
        os.environ["TZ"] = _tz
        import time as _time

        _time.tzset()
    except Exception as e:
        print(f"[WARNING] Could not set TZ at startup: {e}")

    # Setup loggers
    main_logger = setup_logger("main_logger", "/config/logs/researcharr.log")
    radarr_logger = setup_logger("radarr_logger", "/config/logs/radarr.log")
    sonarr_logger = setup_logger("sonarr_logger", "/config/logs/sonarr.log")

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
    main()
