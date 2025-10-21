from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
import requests as requests
import random
import logging

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
        radarr_logger.info("Querying MovieFiles API")
        for movie in movies:
            monitored_str = str(movie["monitored"])
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            if movie["movieFileId"] > 0 and is_monitored:
                MOVIE_FILE_GET_API_CALL = RADARR_URL + API_PATH + MOVIEFILE_ENDPOINT + str(movie["movieFileId"])
                movie_file = requests.get(MOVIE_FILE_GET_API_CALL, headers=radarr_headers).json()
                movie_quality_profile_id = movie["qualityProfileId"]
                # Build dictionary of movie files needing upgrades
                if movie_file["customFormatScore"] < quality_to_formats[movie_quality_profile_id]:
                    movie_files[movie["id"]] = {}
                    movie_files[movie["id"]]["title"] = movie["title"]
                    movie_files[movie["id"]]["customFormatScore"] = movie_file["customFormatScore"]
                    movie_files[movie["id"]]["wantedCustomFormatScore"] = quality_to_formats[movie_quality_profile_id]
        return movie_files


    # Get all quality profile ids and their cutoff scores and add to dictionary
    radarr_logger.info("Querying Radarr Quality Custom Format Cutoff Scores")
    get_radarr_quality_cutoff_scores()

    # Select random movies to upgrade
    random_keys = list(set(random.choices(list(get_movie_files(get_movies()).keys()), k=NUM_MOVIES_TO_UPGRADE)))

    # Set data payload for the movies to search
    data = {
        "name": "MoviesSearch",
        "movieIds": random_keys
    }
    # Do the thing
    radarr_logger.info("Keys to search are " + str(random_keys))
    radarr_logger.info("Searching for movies...")
    MOVIE_COMMAND_API_CALL = RADARR_URL + API_PATH + COMMAND_ENDPOINT
    requests.post(MOVIE_COMMAND_API_CALL, headers=radarr_headers, json=data)
    radarr_logger.info("Movie search command sent to Radarr.")

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
        sonarr_logger.info("Querying EpisodeFiles API")
        for show in series:
            monitored_str = str(show["monitored"])
            is_monitored = monitored_str.lower() == "true" if monitored_str else False
            episode_quality_profile_id = show["qualityProfileId"]
            if show["statistics"]["episodeFileCount"] > 0 and is_monitored:
                EPISODE_FILE_GET_API_CALL = SONARR_URL + API_PATH + EPISODEFILE_ENDPOINT + "?seriesId=" + str(show["id"])
                show_episode_files = requests.get(EPISODE_FILE_GET_API_CALL, headers=sonarr_headers).json()
                for episode in show_episode_files:
                    # Build dictionary of episode files needing upgrades
                    if episode["customFormatScore"] < quality_to_formats[episode_quality_profile_id]:
                        EPISODE_GET_API_CALL = SONARR_URL + API_PATH + EPISODE_ENDPOINT + "?episodeFileId=" + str(episode["id"])
                        episode_data = requests.get(EPISODE_GET_API_CALL, headers=sonarr_headers).json()
                        monitored_str = str(episode_data[0]["monitored"])
                        is_monitored = monitored_str.lower() == "true" if monitored_str else False
                        if is_monitored:
                            episode_files[episode["id"]] = {}
                            episode_files[episode["id"]]["title"] = episode_data[0]["title"]
                            episode_files[episode["id"]]["customFormatScore"] = episode["customFormatScore"]
                            episode_files[episode["id"]]["wantedCustomFormatScore"] = quality_to_formats[episode_quality_profile_id]
        return episode_files

    # Get all quality profile ids and their cutoff scores and add to dictionary
    sonarr_logger.info("Querying Sonarr Quality Custom Format Cutoff Scores")
    get_sonarr_quality_cutoff_scores()

    # Select random episodes to upgrade
    random_keys = list(set(random.choices(list(get_episode_files(get_series()).keys()), k=NUM_EPISODES_TO_UPGRADE)))

    # Set data payload for the movies to search
    data = {
        "name": "EpisodeSearch",
        "episodeIds": random_keys
    }
    # Do the thing
    sonarr_logger.info("Keys to search are " + str(random_keys))
    sonarr_logger.info("Searching for episodes...")
    EPISODE_COMMAND_API_CALL = SONARR_URL + API_PATH + COMMAND_ENDPOINT
    requests.post(EPISODE_COMMAND_API_CALL, headers=sonarr_headers, json=data)
    sonarr_logger.info("Episode search command sent to Sonarr.")

main_logger.info("researcharr process finished.")