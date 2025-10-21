from datetime import date

# Version based on build date
__version__ = date.today().strftime('%Y.%m.%d')
from requests.auth import HTTPBasicAuth
import os
import requests as requests
import random
import logging
import sqlite3
import yaml

# --- Database Setup ---
DB_PATH = "/config/researcharr.db"

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Radarr queue table with last_processed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS radarr_queue (
            movie_id INTEGER PRIMARY KEY,
            last_processed TIMESTAMP
        )
    ''')
    # Sonarr queue table with last_processed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sonarr_queue (
            episode_id INTEGER PRIMARY KEY,
            last_processed TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Create loggers
def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


# Setup loggers
main_logger = setup_logger('main_logger', '/config/logs/researcharr.log')
radarr_logger = setup_logger('radarr_logger', '/config/logs/radarr.log')
sonarr_logger = setup_logger('sonarr_logger', '/config/logs/sonarr.log')

# --- Connection Status Checks ---
def check_radarr_connection():
    try:
        if RADARR_URL and RADARR_API_KEY:
            resp = requests.get(RADARR_URL + '/api/v3/system/status', headers={'Authorization': RADARR_API_KEY}, timeout=10)
            if resp.status_code == 200:
                radarr_logger.info("Radarr connection successful.")
            else:
                radarr_logger.error(f"Radarr connection failed: HTTP {resp.status_code} - {resp.text}")
        else:
            radarr_logger.warning("Radarr URL or API key not set; skipping connection test.")
    except Exception as e:
        radarr_logger.error(f"Radarr connection error: {e}")

def check_sonarr_connection():
    try:
        if SONARR_URL and SONARR_API_KEY:
            resp = requests.get(SONARR_URL + '/api/v3/system/status', headers={'Authorization': SONARR_API_KEY}, timeout=10)
            if resp.status_code == 200:
                sonarr_logger.info("Sonarr connection successful.")
            else:
                sonarr_logger.error(f"Sonarr connection failed: HTTP {resp.status_code} - {resp.text}")
        else:
            sonarr_logger.warning("Sonarr URL or API key not set; skipping connection test.")
    except Exception as e:
        sonarr_logger.error(f"Sonarr connection error: {e}")


# Initialize the database
init_db()


# Load configuration from YAML
with open('/config/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Set researcharr (general) variables
researcharr_cfg = config.get('researcharr', {})
PUID = int(researcharr_cfg.get('puid', 1000))
PGID = int(researcharr_cfg.get('pgid', 1000))
TIMEZONE = researcharr_cfg.get('timezone', "America/New_York")
CRON_SCHEDULE = researcharr_cfg.get('cron_schedule', "0 */1 * * *")


# --- Multi-instance support ---
radarr_instances = config.get('radarr', [])
sonarr_instances = config.get('sonarr', [])

# Log connection status for all enabled Radarr/Sonarr instances
for idx, radarr_cfg in enumerate(r for r in radarr_instances if r.get('enabled', False)):
    url = radarr_cfg.get('url', '')
    key = radarr_cfg.get('api_key', '')
    try:
        if url and key:
            resp = requests.get(url + '/api/v3/system/status', headers={'Authorization': key}, timeout=10)
            if resp.status_code == 200:
                radarr_logger.info(f"Radarr {idx+1} connection successful.")
            else:
                radarr_logger.error(f"Radarr {idx+1} connection failed: HTTP {resp.status_code} - {resp.text}")
        else:
            radarr_logger.warning(f"Radarr {idx+1} URL or API key not set; skipping connection test.")
    except Exception as e:
        radarr_logger.error(f"Radarr {idx+1} connection error: {e}")

for idx, sonarr_cfg in enumerate(s for s in sonarr_instances if s.get('enabled', False)):
    url = sonarr_cfg.get('url', '')
    key = sonarr_cfg.get('api_key', '')
    try:
        if url and key:
            resp = requests.get(url + '/api/v3/system/status', headers={'Authorization': key}, timeout=10)
            if resp.status_code == 200:
                sonarr_logger.info(f"Sonarr {idx+1} connection successful.")
            else:
                sonarr_logger.error(f"Sonarr {idx+1} connection failed: HTTP {resp.status_code} - {resp.text}")
        else:
            sonarr_logger.warning(f"Sonarr {idx+1} URL or API key not set; skipping connection test.")
    except Exception as e:
        sonarr_logger.error(f"Sonarr {idx+1} connection error: {e}")

# --- New: Download queue check and main logic for each instance ---
def get_radarr_queue_length(url, key):
    try:
        resp = requests.get(url + '/api/v3/queue', headers={'Authorization': key}, timeout=10)
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            radarr_logger.warning(f"Failed to get Radarr queue: HTTP {resp.status_code}")
    except Exception as e:
        radarr_logger.warning(f"Error getting Radarr queue: {e}")
    return 0

def get_sonarr_queue_length(url, key):
    try:
        resp = requests.get(url + '/api/v3/queue', headers={'Authorization': key}, timeout=10)
        if resp.status_code == 200:
            queue = resp.json()
            return len(queue)
        else:
            sonarr_logger.warning(f"Failed to get Sonarr queue: HTTP {resp.status_code}")
    except Exception as e:
        sonarr_logger.warning(f"Error getting Sonarr queue: {e}")
    return 0

# --- Radarr instance processing ---
import datetime
for idx, radarr_cfg in enumerate(r for r in radarr_instances if r.get('enabled', False)):
    url = radarr_cfg.get('url', '')
    key = radarr_cfg.get('api_key', '')
    process = str(radarr_cfg.get('process', False)).lower() == 'true'
    num_to_upgrade = int(radarr_cfg.get('movies_to_upgrade', 5))
    max_queue = int(radarr_cfg.get('max_download_queue', 15))
    reprocess_days = int(radarr_cfg.get('reprocess_interval_days', 7))
    if not (url and key and process):
        continue
    if not url.startswith(('http://', 'https://')):
        radarr_logger.warning(f"Radarr {idx+1} URL is invalid or missing scheme, skipping this instance.")
        continue
    API_PATH = "/api/v3/"
    COMMAND_ENDPOINT = "command"
    QUALITY_PROFILE_ENDPOINT = "qualityprofile"
    MOVIE_ENDPOINT = "movie"
    MOVIEFILE_ENDPOINT = "moviefile/"
    radarr_headers = {'Authorization': key}

    def get_radarr_quality_cutoff_scores():
        QUALITY_PROFILES_GET_API_CALL = url + API_PATH + QUALITY_PROFILE_ENDPOINT
        quality_profiles = requests.get(QUALITY_PROFILES_GET_API_CALL, headers=radarr_headers).json()
        quality_to_formats = {}
        for quality in quality_profiles:
            quality_to_formats.update({quality["id"]: quality["cutoffFormatScore"]})
        return quality_to_formats

    def get_movies():
        MOVIES_GET_API_CALL = url + API_PATH + MOVIE_ENDPOINT
        movies = requests.get(MOVIES_GET_API_CALL, headers=radarr_headers).json()
        return movies

    def get_movie_files(movies, quality_to_formats):
        candidate_ids = []
        for movie in movies:
            monitored_str = str(movie.get("monitored", ""))
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            if movie.get("movieFileId", 0) > 0 and is_monitored:
                MOVIE_FILE_GET_API_CALL = url + API_PATH + MOVIEFILE_ENDPOINT + str(movie["movieFileId"])
                movie_file = requests.get(MOVIE_FILE_GET_API_CALL, headers=radarr_headers).json()
                movie_quality_profile_id = movie["qualityProfileId"]
                if movie_file.get("customFormatScore", 99999) < quality_to_formats.get(movie_quality_profile_id, 99999):
                    candidate_ids.append(movie["id"])
        return candidate_ids

    queue_len = get_radarr_queue_length(url, key)
    if queue_len >= max_queue:
        radarr_logger.info(f"Radarr {idx+1}: Download queue has {queue_len} items (limit {max_queue}), skipping this run.")
        continue
    radarr_logger.info(f"Radarr {idx+1}: Download queue has {queue_len} items (limit {max_queue}), proceeding.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM radarr_queue")
    queue_count = cursor.fetchone()[0]
    radarr_logger.info(f"Found {queue_count} movies in the Radarr queue.")

    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=reprocess_days)).isoformat()
    cursor.execute("SELECT movie_id FROM radarr_queue WHERE last_processed IS NULL OR last_processed < ?", (cutoff,))
    reprocess_ids = [row[0] for row in cursor.fetchall()]

    if queue_count == 0 or reprocess_ids:
        radarr_logger.info("Radarr queue is empty or items need reprocessing. Repopulating from all eligible movies...")
        quality_to_formats = get_radarr_quality_cutoff_scores()
        all_movies = get_movies()
        candidate_ids = get_movie_files(all_movies, quality_to_formats)
        for movie_id in candidate_ids:
            cursor.execute("INSERT OR IGNORE INTO radarr_queue (movie_id, last_processed) VALUES (?, NULL)", (movie_id,))
        conn.commit()
    else:
        radarr_logger.info("No eligible movies found to populate the queue.")

    cursor.execute("SELECT movie_id FROM radarr_queue ORDER BY COALESCE(last_processed, '1970-01-01') ASC LIMIT ?", (num_to_upgrade,))
    movie_ids_to_process = [row[0] for row in cursor.fetchall()]

    if movie_ids_to_process:
        radarr_logger.info(f"Processing {len(movie_ids_to_process)} movies from the queue.")
        data = {
            "name": "MoviesSearch",
            "movieIds": movie_ids_to_process
        }
        MOVIE_COMMAND_API_CALL = url + API_PATH + COMMAND_ENDPOINT
        requests.post(MOVIE_COMMAND_API_CALL, headers=radarr_headers, json=data)
        radarr_logger.info(f"Movie search command sent for IDs: {movie_ids_to_process}")
        now = datetime.datetime.utcnow().isoformat()
        for movie_id in movie_ids_to_process:
            cursor.execute("UPDATE radarr_queue SET last_processed = ? WHERE movie_id = ?", (now, movie_id))
        conn.commit()
        radarr_logger.info(f"Updated last_processed for {len(movie_ids_to_process)} movies.")
    else:
        radarr_logger.info("No movies in the queue to process.")
    conn.close()

# --- Sonarr instance processing ---
for idx, sonarr_cfg in enumerate(s for s in sonarr_instances if s.get('enabled', False)):
    url = sonarr_cfg.get('url', '')
    key = sonarr_cfg.get('api_key', '')
    process = str(sonarr_cfg.get('process', False)).lower() == 'true'
    num_to_upgrade = int(sonarr_cfg.get('episodes_to_upgrade', 5))
    max_queue = int(sonarr_cfg.get('max_download_queue', 15))
    reprocess_days = int(sonarr_cfg.get('reprocess_interval_days', 7))
    if not (url and key and process):
        continue
    if not url.startswith(('http://', 'https://')):
        sonarr_logger.warning(f"Sonarr {idx+1} URL is invalid or missing scheme, skipping this instance.")
        continue
    API_PATH = "/api/v3/"
    COMMAND_ENDPOINT = "command"
    QUALITY_PROFILE_ENDPOINT = "qualityprofile"
    SERIES_ENDPOINT = "series"
    EPISODEFILE_ENDPOINT = "episodefile"
    EPISODE_ENDPOINT = "episode"
    sonarr_headers = {'Authorization': key}

    def get_sonarr_quality_cutoff_scores():
        QUALITY_PROFILES_GET_API_CALL = url + API_PATH + QUALITY_PROFILE_ENDPOINT
        quality_profiles = requests.get(QUALITY_PROFILES_GET_API_CALL, headers=sonarr_headers).json()
        quality_to_formats = {}
        for quality in quality_profiles:
            quality_to_formats.update({quality["id"]: quality["cutoffFormatScore"]})
        return quality_to_formats

    def get_series():
        SERIES_GET_API_CALL = url + API_PATH + SERIES_ENDPOINT
        series = requests.get(SERIES_GET_API_CALL, headers=sonarr_headers).json()
        return series

    def get_episode_files(series, quality_to_formats):
        candidate_ids = []
        for show in series:
            monitored_str = str(show.get("monitored", ""))
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            if show.get("monitored") and show.get("statistics", {}).get("episodeFileCount", 0) > 0:
                EPISODE_FILE_GET_API_CALL = url + API_PATH + EPISODEFILE_ENDPOINT + "?seriesId=" + str(show["id"])
                episode_files = requests.get(EPISODE_FILE_GET_API_CALL, headers=sonarr_headers).json()
                for episode_file in episode_files:
                    episode_quality_profile_id = show["qualityProfileId"]
                    if episode_file.get("customFormatScore", 99999) < quality_to_formats.get(episode_quality_profile_id, 99999):
                        candidate_ids.append(episode_file["id"])
        return candidate_ids

    queue_len = get_sonarr_queue_length(url, key)
    if queue_len >= max_queue:
        sonarr_logger.info(f"Sonarr {idx+1}: Download queue has {queue_len} items (limit {max_queue}), skipping this run.")
        continue
    sonarr_logger.info(f"Sonarr {idx+1}: Download queue has {queue_len} items (limit {max_queue}), proceeding.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sonarr_queue")
    queue_count = cursor.fetchone()[0]
    sonarr_logger.info(f"Found {queue_count} episodes in the Sonarr queue.")

    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=reprocess_days)).isoformat()
    cursor.execute("SELECT episode_id FROM sonarr_queue WHERE last_processed IS NULL OR last_processed < ?", (cutoff,))
    reprocess_ids = [row[0] for row in cursor.fetchall()]

    if queue_count == 0 or reprocess_ids:
        sonarr_logger.info("Sonarr queue is empty or items need reprocessing. Repopulating from all eligible episodes...")
        quality_to_formats = get_sonarr_quality_cutoff_scores()
        all_series = get_series()
        candidate_ids = get_episode_files(all_series, quality_to_formats)
        for episode_id in candidate_ids:
            cursor.execute("INSERT OR IGNORE INTO sonarr_queue (episode_id, last_processed) VALUES (?, NULL)", (episode_id,))
        conn.commit()
    else:
        sonarr_logger.info("No eligible episodes found to populate the queue.")

    cursor.execute("SELECT episode_id FROM sonarr_queue ORDER BY COALESCE(last_processed, '1970-01-01') ASC LIMIT ?", (num_to_upgrade,))
    episode_ids_to_process = [row[0] for row in cursor.fetchall()]

    if episode_ids_to_process:
        sonarr_logger.info(f"Processing {len(episode_ids_to_process)} episodes from the queue.")
        data = {
            "name": "EpisodeSearch",
            "episodeIds": episode_ids_to_process
        }
        EPISODE_COMMAND_API_CALL = url + API_PATH + COMMAND_ENDPOINT
        requests.post(EPISODE_COMMAND_API_CALL, headers=sonarr_headers, json=data)
        sonarr_logger.info(f"Episode search command sent for IDs: {episode_ids_to_process}")
        now = datetime.datetime.utcnow().isoformat()
        for episode_id in episode_ids_to_process:
            cursor.execute("UPDATE sonarr_queue SET last_processed = ? WHERE episode_id = ?", (now, episode_id))
        conn.commit()
        sonarr_logger.info(f"Updated last_processed for {len(episode_ids_to_process)} episodes.")
    else:
        sonarr_logger.info("No episodes in the queue to process.")
    conn.close()

# Load configuration from YAML
with open('/config/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Set researcharr (general) variables
researcharr_cfg = config.get('researcharr', {})
PUID = int(researcharr_cfg.get('puid', 1000))
PGID = int(researcharr_cfg.get('pgid', 1000))
TIMEZONE = researcharr_cfg.get('timezone', "America/New_York")
CRON_SCHEDULE = researcharr_cfg.get('cron_schedule', "0 */1 * * *")


# Multi-instance Radarr
radarr_list = config.get('radarr', [])
for idx, radarr_cfg in enumerate(radarr_list):
    if not radarr_cfg.get('enabled', False):
        continue
    process_radarr_str = str(radarr_cfg.get('process', True))
    PROCESS_RADARR = process_radarr_str.lower() == "true"
    RADARR_API_KEY = radarr_cfg.get('api_key', "")
    RADARR_URL = radarr_cfg.get('url', "")
    NUM_MOVIES_TO_UPGRADE = int(radarr_cfg.get('movies_to_upgrade', 5))
    MOVIE_ENDPOINT = "movie"
    MOVIEFILE_ENDPOINT = "moviefile/"
    # ...existing Radarr processing logic here, using these variables per instance...

# Multi-instance Sonarr
sonarr_list = config.get('sonarr', [])
for idx, sonarr_cfg in enumerate(sonarr_list):
    if not sonarr_cfg.get('enabled', False):
        continue
    process_sonarr_str = str(sonarr_cfg.get('process', True))
    PROCESS_SONARR = process_sonarr_str.lower() == "true"
    SONARR_API_KEY = sonarr_cfg.get('api_key', "")
    SONARR_URL = sonarr_cfg.get('url', "")
    NUM_EPISODES_TO_UPGRADE = int(sonarr_cfg.get('episodes_to_upgrade', 5))
    SERIES_ENDPOINT = "series"
    EPISODEFILE_ENDPOINT = "episodefile"
    EPISODE_ENDPOINT = "episode"
    # ...existing Sonarr processing logic here, using these variables per instance...

# Set shared variables
API_PATH = "/api/v3/"
QUALITY_PROFILE_ENDPOINT = "qualityprofile"
COMMAND_ENDPOINT = "command"

main_logger.info("Starting researcharr process...")

if PROCESS_RADARR:
    radarr_logger.info("Processing Radarr...")
    # Set Authorization radarr headers for API calls
    radarr_headers = {
        'Authorization': RADARR_API_KEY,
    }

    quality_to_formats = {}
    movies = {}
    movie_files = {}

    def get_radarr_quality_cutoff_scores():
        QUALITY_PROFILES_GET_API_CALL = RADARR_URL + API_PATH + QUALITY_PROFILE_ENDPOINT
        quality_profiles = requests.get(QUALITY_PROFILES_GET_API_CALL, headers=radarr_headers).json()
        for quality in quality_profiles:
            quality_to_formats.update({quality["id"]: quality["cutoffFormatScore"]})

    # Get all movies and return a dictionary of movies
    def get_movies():
        radarr_logger.info("Querying Movies API")
        MOVIES_GET_API_CALL = RADARR_URL + API_PATH + MOVIE_ENDPOINT
        movies = requests.get(MOVIES_GET_API_CALL, headers=radarr_headers).json()
        return movies

    # Get all moviefiles for all movies and if moviefile exists and the customFormatScore is less than the wanted score, add it to dictionary and return dictionary
    def get_movie_files(movies):
        radarr_logger.info("Querying all movie files to find candidates for upgrade...")
        candidate_ids = []
        for movie in movies:
            monitored_str = str(movie["monitored"])
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            if movie["movieFileId"] > 0 and is_monitored:
                MOVIE_FILE_GET_API_CALL = RADARR_URL + API_PATH + MOVIEFILE_ENDPOINT + str(movie["movieFileId"])
                movie_file = requests.get(MOVIE_FILE_GET_API_CALL, headers=radarr_headers).json()
                movie_quality_profile_id = movie["qualityProfileId"]
                # If score is lower than wanted, add to candidates
                if movie_file["customFormatScore"] < quality_to_formats.get(movie_quality_profile_id, 99999):
                    candidate_ids.append(movie["id"])
        return candidate_ids

    # --- Radarr Main Logic ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if queue is empty
    cursor.execute("SELECT COUNT(*) FROM radarr_queue")
    queue_count = cursor.fetchone()[0]
    radarr_logger.info(f"Found {queue_count} movies in the Radarr queue.")

    if queue_count == 0:
        radarr_logger.info("Radarr queue is empty. Repopulating from all eligible movies...")
        get_radarr_quality_cutoff_scores()
        all_movies = get_movies()
        candidate_ids = get_movie_files(all_movies)
        if candidate_ids:
            radarr_logger.info(f"Found {len(candidate_ids)} movies to add to the queue.")
            cursor.executemany("INSERT OR IGNORE INTO radarr_queue (movie_id) VALUES (?)", [(id,) for id in candidate_ids])
            conn.commit()
        else:
            radarr_logger.info("No eligible movies found to populate the queue.")

    # Get movies to process from the queue
    cursor.execute("SELECT movie_id FROM radarr_queue LIMIT ?", (NUM_MOVIES_TO_UPGRADE,))
    movie_ids_to_process = [row[0] for row in cursor.fetchall()]

    if movie_ids_to_process:
        radarr_logger.info(f"Processing {len(movie_ids_to_process)} movies from the queue.")
        # Set data payload for the movies to search
        data = {
            "name": "MoviesSearch",
            "movieIds": movie_ids_to_process
        }
        # Send search command to Radarr
        MOVIE_COMMAND_API_CALL = RADARR_URL + API_PATH + COMMAND_ENDPOINT
        requests.post(MOVIE_COMMAND_API_CALL, headers=radarr_headers, json=data)
        radarr_logger.info(f"Movie search command sent for IDs: {movie_ids_to_process}")

        # Remove processed movies from the queue
        cursor.executemany("DELETE FROM radarr_queue WHERE movie_id = ?", [(id,) for id in movie_ids_to_process])
        conn.commit()
        radarr_logger.info(f"Removed {len(movie_ids_to_process)} movies from the queue.")
    else:
        radarr_logger.info("No movies in the queue to process.")

    conn.close()


if PROCESS_SONARR:
    sonarr_logger.info("Processing Sonarr...")
    # Set Authorization sonarr headers for API calls
    sonarr_headers = {
        'Authorization': SONARR_API_KEY,
    }

    quality_to_formats = {}
    series = {}
    episode_files = {}

    def get_sonarr_quality_cutoff_scores():
        QUALITY_PROFILES_GET_API_CALL = SONARR_URL + API_PATH + QUALITY_PROFILE_ENDPOINT
        quality_profiles = requests.get(QUALITY_PROFILES_GET_API_CALL, headers=sonarr_headers).json()
        for quality in quality_profiles:
            quality_to_formats.update({quality["id"]: quality["cutoffFormatScore"]})

    # Get all series and return a dictionary of series
    def get_series():
        sonarr_logger.info("Querying Series API")
        SERIES_GET_API_CALL = SONARR_URL + API_PATH + SERIES_ENDPOINT
        series = requests.get(SERIES_GET_API_CALL, headers=sonarr_headers).json()
        return series

    # Get all episodefiles for all series and if episodefile exists and the customFormatScore is less than the wanted score, add it to dictionary and return dictionary
    def get_episode_files(series):
        sonarr_logger.info("Querying all episode files to find candidates for upgrade...")
        candidate_ids = []
        for show in series:
            monitored_str = str(show["monitored"])
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            if show["monitored"] and show.get("statistics", {}).get("episodeFileCount", 0) > 0:
                EPISODE_FILE_GET_API_CALL = SONARR_URL + API_PATH + EPISODEFILE_ENDPOINT + "?seriesId=" + str(show["id"])
                episode_files = requests.get(EPISODE_FILE_GET_API_CALL, headers=sonarr_headers).json()
                for episode_file in episode_files:
                    episode_quality_profile_id = show["qualityProfileId"]
                    if episode_file["customFormatScore"] < quality_to_formats.get(episode_quality_profile_id, 99999):
                        candidate_ids.append(episode_file["id"])
        return candidate_ids

    # --- Sonarr Main Logic ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if queue is empty
    cursor.execute("SELECT COUNT(*) FROM sonarr_queue")
    queue_count = cursor.fetchone()[0]
    sonarr_logger.info(f"Found {queue_count} episodes in the Sonarr queue.")

    if queue_count == 0:
        sonarr_logger.info("Sonarr queue is empty. Repopulating from all eligible episodes...")
        get_sonarr_quality_cutoff_scores()
        all_series = get_series()
        candidate_ids = get_episode_files(all_series)
        if candidate_ids:
            sonarr_logger.info(f"Found {len(candidate_ids)} episodes to add to the queue.")
            cursor.executemany("INSERT OR IGNORE INTO sonarr_queue (episode_id) VALUES (?)", [(id,) for id in candidate_ids])
            conn.commit()
        else:
            sonarr_logger.info("No eligible episodes found to populate the queue.")

    # Get episodes to process from the queue
    cursor.execute("SELECT episode_id FROM sonarr_queue LIMIT ?", (NUM_EPISODES_TO_UPGRADE,))
    episode_ids_to_process = [row[0] for row in cursor.fetchall()]

    if episode_ids_to_process:
        sonarr_logger.info(f"Processing {len(episode_ids_to_process)} episodes from the queue.")
        # Set data payload for the episodes to search
        data = {
            "name": "EpisodeSearch",
            "episodeIds": episode_ids_to_process
        }
        # Send search command to Sonarr
        EPISODE_COMMAND_API_CALL = SONARR_URL + API_PATH + COMMAND_ENDPOINT
        requests.post(EPISODE_COMMAND_API_CALL, headers=sonarr_headers, json=data)
        sonarr_logger.info(f"Episode search command sent for IDs: {episode_ids_to_process}")

        # Remove processed episodes from the queue
        cursor.executemany("DELETE FROM sonarr_queue WHERE episode_id = ?", [(id,) for id in episode_ids_to_process])
        conn.commit()
        sonarr_logger.info(f"Removed {len(episode_ids_to_process)} episodes from the queue.")
    else:
        sonarr_logger.info("No episodes in the queue to process.")

    conn.close()

main_logger.info("researcharr process finished.")

# --- Test: Countdown until next run (for container startup diagnostics) ---
import time
import sys

def countdown(minutes):
    main_logger.info(f"Countdown: {minutes} minutes until next scheduled run (test mode)")
    for i in range(minutes, 0, -1):
        sys.stdout.write(f"\rNext run in {i} minute(s)... ")
        sys.stdout.flush()
        time.sleep(60)
    sys.stdout.write("\n")
    main_logger.info("Countdown complete. If this is a test, the next cron run should now occur.")

# Only run countdown if started with a special env var (to avoid running in cron jobs)
if os.environ.get("RESEARCHARR_STARTUP_COUNTDOWN", "0") == "1":
    countdown(5)  # 5 minute countdown for test/demo

# --- Startup validation for Radarr/Sonarr config ---
def has_valid_url_and_key(instances):
    for inst in instances:
        if inst.get('enabled', False) and inst.get('url', '').startswith(('http://', 'https://')) and inst.get('api_key', ''):
            return True
    return False

if not has_valid_url_and_key(radarr_instances) and not has_valid_url_and_key(sonarr_instances):
    main_logger.warning("No enabled Radarr or Sonarr instance has a valid URL (must start with http:// or https://) and API key. Please update your config.yml using the web UI. The app will not run jobs until this is fixed.")
    print("WARNING: No enabled Radarr or Sonarr instance has a valid URL (must start with http:// or https://) and API key. Please update your config.yml using the web UI. The app will not run jobs until this is fixed.")