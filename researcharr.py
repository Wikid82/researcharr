# -*- coding: utf-8 -*-
import os
import sqlite3
import logging
import requests
import yaml
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DB_PATH", "config/researcharr.db")
USER_CONFIG_PATH = os.environ.get("USER_CONFIG_PATH", "config/webui_user.yml")
main_logger = None
radarr_logger = None
sonarr_logger = None

def init_db():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS radarr_queue (
			movie_id INTEGER PRIMARY KEY,
			last_processed TEXT
		)
		"""
	)
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS sonarr_queue (
			episode_id INTEGER PRIMARY KEY,
			last_processed TEXT
		)
		"""
	)
	conn.commit()
	conn.close()

def setup_logger(name, log_file, level=logging.INFO):
	logger = logging.getLogger(name)
	logger.setLevel(level)
	fh = logging.FileHandler(log_file)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	fh.setFormatter(formatter)
	if not logger.handlers:
		logger.addHandler(fh)
	return logger

def has_valid_url_and_key(instances):
	for inst in instances:
		if inst.get("enabled") and (not inst.get("url") or not inst.get("api_key")):
			return False
		if inst.get("url", "").startswith("ftp://"):
			return False
	return True

def check_radarr_connection(url, api_key, logger):
	if not url or not api_key:
		logger.warning("Radarr URL or API key missing.")
		return
	try:
		resp = requests.get(f"{url}/api/v3/system/status", headers={"X-Api-Key": api_key}, timeout=5)
		if resp.status_code == 200:
			logger.info("Radarr connection successful.")
		else:
			logger.error(f"Radarr connection failed: {resp.status_code} {resp.text}")
	except Exception as e:
		logger.error(f"Radarr connection error: {e}")

def check_sonarr_connection(url, api_key, logger):
	if not url or not api_key:
		logger.warning("Sonarr URL or API key missing.")
		return
	try:
		resp = requests.get(f"{url}/api/v3/system/status", headers={"X-Api-Key": api_key}, timeout=5)
		if resp.status_code == 200:
			logger.info("Sonarr connection successful.")
		else:
			logger.error(f"Sonarr connection failed: {resp.status_code} {resp.text}")
	except Exception as e:
		logger.error(f"Sonarr connection error: {e}")

def load_config(path="config/config.yml"):
	if not os.path.exists(path):
		raise FileNotFoundError(f"Config file not found: {path}")
	with open(path, "r") as f:
		try:
			config = yaml.safe_load(f)
		except yaml.YAMLError as e:
			raise
	return config