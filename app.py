# --- Health and Metrics Endpoints ---
from flask import Flask, jsonify, request

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

    """
    Loads and returns the YAML config as a dict.
    Accepts optional path for testability.
    """

    import sys
    import time

    for inst in instances:
def main():
