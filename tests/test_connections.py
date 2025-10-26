import logging

import pytest

from researcharr.researcharr import (
    setup_logger,
    check_radarr_connection,
    check_sonarr_connection,
)


def _make_logger(tmp_path):
    # Use a unique logger name per test run so handlers don't collide between
    # pytest temporary directories.
    name = f"test_conn_{tmp_path.name}"
    log_file = tmp_path / "conn.log"
    return setup_logger(name, str(log_file))


def test_check_radarr_missing_params(tmp_path):
    logger = _make_logger(tmp_path)
    assert check_radarr_connection("", "", logger) is False
    content = (tmp_path / "conn.log").read_text()
    assert "Missing Radarr URL or API key" in content


def test_check_radarr_status_non200(tmp_path, monkeypatch):
    class R:
        status_code = 404

    monkeypatch.setattr("researcharr.researcharr.requests.get", lambda url: R())
    logger = _make_logger(tmp_path)
    assert check_radarr_connection("http://example", "key", logger) is False
    assert "Radarr connection failed with status" in (tmp_path / "conn.log").read_text()


def test_check_radarr_exception(tmp_path, monkeypatch):
    def bad(url):
        raise RuntimeError("boom")

    monkeypatch.setattr("researcharr.researcharr.requests.get", bad)
    logger = _make_logger(tmp_path)
    assert check_radarr_connection("http://example", "key", logger) is False
    assert "Radarr connection failed:" in (tmp_path / "conn.log").read_text()


def test_check_sonarr_variants(tmp_path, monkeypatch):
    logger = _make_logger(tmp_path)
    # Missing params
    assert check_sonarr_connection("", "", logger) is False
    # Non-200 status
    class R:
        status_code = 500

    monkeypatch.setattr("researcharr.researcharr.requests.get", lambda url: R())
    assert check_sonarr_connection("http://x", "k", logger) is False
    # Exception
    def bad(url):
        raise ValueError("err")

    monkeypatch.setattr("researcharr.researcharr.requests.get", bad)
    assert check_sonarr_connection("http://x", "k", logger) is False
