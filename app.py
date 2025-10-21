from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
import requests as requests
import random
import logging
import sqlite3

# --- Database Setup ---
DB_PATH = "/config/researcharr.db"

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Radarr queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS radarr_queue (
            movie_id INTEGER PRIMARY KEY
        )
    ''')
    # Sonarr queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sonarr_queue (
            episode_id INTEGER PRIMARY KEY
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

# Initialize the database
init_db()

# Load .env
load_dotenv(dotenv_path="/config/.env")

# Set radarr variables
process_radarr_str = os.getenv("PROCESS_RADARR")
PROCESS_RADARR = process_radarr_str.lower() == "true" if process_radarr_str else False
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL")
NUM_MOVIES_TO_UPGRADE = int(os.getenv("NUM_MOVIES_TO_UPGRADE"))
MOVIE_ENDPOINT = "movie"
MOVIEFILE_ENDPOINT = "moviefile/"

# Set sonarr varaibles
process_sonarr_str = os.getenv("PROCESS_SONARR")
PROCESS_SONARR = process_sonarr_str.lower() == "true" if process_sonarr_str else False
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL")
NUM_EPISODES_TO_UPGRADE = int(os.getenv("NUM_EPISODES_TO_UPGRADE"))
SERIES_ENDPOINT = "series"
EPISODEFILE_ENDPOINT = "episodefile"
EPISODE_ENDPOINT = "episode"

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