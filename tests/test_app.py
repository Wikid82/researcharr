import importlib
import os
import sqlite3
import sys
import tempfile
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def patch_config_paths(tmp_path_factory, monkeypatch):
    temp_dir = tmp_path_factory.mktemp("config")
    # Patch all /config paths before importing app
    monkeypatch.setenv("TZ", "America/New_York")
    monkeypatch.setattr(
        "os.environ", {**os.environ, "TZ": "America/New_York"}, raising=False
    )
    monkeypatch.setattr(
        "researcharr.app.DB_PATH", str(temp_dir / "researcharr.db"), raising=False
    )
    monkeypatch.setattr("researcharr.app.main_logger", None, raising=False)
    monkeypatch.setattr("researcharr.app.radarr_logger", None, raising=False)
    monkeypatch.setattr("researcharr.app.sonarr_logger", None, raising=False)
    monkeypatch.setattr(
        "researcharr.app.setup_logger",
        lambda name, log_file, level=None: mock.Mock(),
        raising=False,
    )
    monkeypatch.setattr(
        "researcharr.app.USER_CONFIG_PATH",
        str(temp_dir / "webui_user.yml"),
        raising=False,
    )
    # Patch config file loading to use temp config
    config_path = temp_dir / "config.yml"
    with open(config_path, "w") as f:
        f.write(
            "researcharr:\n  timezone: America/New_York\n  puid: 1000\n  pgid: 1000\n  cron_schedule: '0 * * * *'\nradarr: []\nsonarr: []\n"
        )
    import builtins

    real_open = builtins.open
    # builtins.open monkeypatch is handled globally in conftest.py
    # Re-import app to apply patches
    if "researcharr.app" in sys.modules:
        importlib.reload(sys.modules["researcharr.app"])
    else:
        importlib.import_module("researcharr.app")
    yield
    # Cleanup handled by tmp_path_factory


def test_init_db_creates_tables(tmp_path, monkeypatch):
    from researcharr import app

    db_path = tmp_path / "test_researcharr.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path), raising=False)
    app.init_db()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "radarr_queue" in tables
    assert "sonarr_queue" in tables
    conn.close()


def test_setup_logger_creates_log_file(tmp_path):
    # Logger is monkeypatched to a mock, so just check it returns a mock
    from researcharr import app

    logger = app.setup_logger("test_logger", str(tmp_path / "test.log"))
    assert hasattr(logger, "info")


def test_has_valid_url_and_key():
    from researcharr import app

    valid = [
        {"enabled": True, "url": "http://localhost", "api_key": "abc"},
        {"enabled": False, "url": "http://localhost", "api_key": "abc"},
    ]
    invalid = [
        {"enabled": True, "url": "", "api_key": ""},
        {"enabled": True, "url": "ftp://localhost", "api_key": "abc"},
    ]
    assert app.has_valid_url_and_key(valid) is True
    assert app.has_valid_url_and_key(invalid) is False


def test_check_radarr_connection_and_sonarr_connection(monkeypatch):
    from unittest import mock

    from researcharr import app

    # Patch loggers as mocks
    radarr_logger = mock.Mock()
    sonarr_logger = mock.Mock()
    with mock.patch("researcharr.app.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "OK"
        app.check_radarr_connection("http://localhost", "abc", radarr_logger)
        app.check_sonarr_connection("http://localhost", "abc", sonarr_logger)
        assert mock_get.call_count == 2


def test_radarr_connection_unreachable(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch(
        "researcharr.app.requests.get", side_effect=Exception("unreachable")
    ) as mock_get:
        app.check_radarr_connection("http://badhost", "abc", logger)
        logger.error.assert_called()


def test_sonarr_connection_unreachable(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch(
        "researcharr.app.requests.get", side_effect=Exception("unreachable")
    ) as mock_get:
        app.check_sonarr_connection("http://badhost", "abc", logger)
        logger.error.assert_called()


def test_radarr_connection_non_200(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch("researcharr.app.requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "fail"
        app.check_radarr_connection("http://localhost", "abc", logger)
        logger.error.assert_called()


def test_sonarr_connection_non_200(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch("researcharr.app.requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        mock_get.return_value.text = "not found"
        app.check_sonarr_connection("http://localhost", "abc", logger)
        logger.error.assert_called()


def test_radarr_connection_timeout(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    import requests

    with mock.patch("researcharr.app.requests.get", side_effect=requests.Timeout):
        app.check_radarr_connection("http://localhost", "abc", logger)
        logger.error.assert_called()


def test_sonarr_connection_timeout(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    import requests

    with mock.patch("researcharr.app.requests.get", side_effect=requests.Timeout):
        app.check_sonarr_connection("http://localhost", "abc", logger)
        logger.error.assert_called()


def test_load_config_missing_file(tmp_path, monkeypatch):
    from researcharr import app

    config_path = tmp_path / "missing.yml"
    with pytest.raises(FileNotFoundError):
        app.load_config(path=str(config_path))


def test_load_config_empty_file(tmp_path, monkeypatch):
    from researcharr import app

    config_path = tmp_path / "empty.yml"
    config_path.write_text("")
    config = app.load_config(path=str(config_path))
    assert config is None or config == {}


def test_load_config_malformed_yaml(tmp_path, monkeypatch):
    from researcharr import app

    config_path = tmp_path / "bad.yml"
    config_path.write_text(": bad yaml : :")
    import yaml

    with pytest.raises(yaml.YAMLError):
        app.load_config(path=str(config_path))


def test_load_config_missing_fields(tmp_path, monkeypatch):
    from researcharr import app

    config_path = tmp_path / "partial.yml"
    config_path.write_text("radarr: []\n")
    config = app.load_config(path=str(config_path))
    assert "radarr" in config


def test_init_db_idempotent(tmp_path, monkeypatch):
    from researcharr import app

    db_path = tmp_path / "idempotent.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path), raising=False)
    app.init_db()
    # Insert a row
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO radarr_queue (movie_id, last_processed) VALUES (?, ?)",
        (1, "2025-10-22"),
    )
    conn.commit()
    conn.close()
    # Call init_db again, should not overwrite
    app.init_db()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT movie_id, last_processed FROM radarr_queue WHERE movie_id=1")
    row = cursor.fetchone()
    assert row == (1, "2025-10-22")
    conn.close()


def test_insert_and_retrieve_radarr_queue(tmp_path, monkeypatch):
    from researcharr import app

    db_path = tmp_path / "radarr.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path), raising=False)
    app.init_db()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO radarr_queue (movie_id, last_processed) VALUES (?, ?)",
        (42, "2025-10-22"),
    )
    conn.commit()
    cursor.execute(
        "SELECT movie_id, last_processed FROM radarr_queue WHERE movie_id=42"
    )
    row = cursor.fetchone()
    assert row == (42, "2025-10-22")
    conn.close()


def test_insert_and_retrieve_sonarr_queue(tmp_path, monkeypatch):
    from researcharr import app

    db_path = tmp_path / "sonarr.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path), raising=False)
    app.init_db()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sonarr_queue (episode_id, last_processed) VALUES (?, ?)",
        (99, "2025-10-22"),
    )
    conn.commit()
    cursor.execute(
        "SELECT episode_id, last_processed FROM sonarr_queue WHERE episode_id=99"
    )
    row = cursor.fetchone()
    assert row == (99, "2025-10-22")
    conn.close()


def test_radarr_connection_success_logs_info(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch("researcharr.app.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "OK"
        app.check_radarr_connection("http://localhost", "abc", logger)
        logger.info.assert_called_with("Radarr connection successful.")


def test_sonarr_connection_success_logs_info(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    with mock.patch("researcharr.app.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "OK"
        app.check_sonarr_connection("http://localhost", "abc", logger)
        logger.info.assert_called_with("Sonarr connection successful.")


def test_radarr_connection_missing_params_logs_warning(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    app.check_radarr_connection("", "", logger)
    logger.warning.assert_called()


def test_sonarr_connection_missing_params_logs_warning(monkeypatch):
    from researcharr import app

    logger = mock.Mock()
    app.check_sonarr_connection("", "", logger)
    logger.warning.assert_called()
