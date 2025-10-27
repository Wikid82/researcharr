"""Pytest session helpers.

Provide compatibility shim modules under the `researcharr.plugins.*` names
so older-style imports used by the test-suite resolve to the canonical
`plugins.*` implementations located at the repo root.
"""
import sys
import importlib

_mappings = [
    ("plugins.media.example_sonarr", "researcharr.plugins.example_sonarr"),
]

for src, dst in _mappings:
    try:
        mod = importlib.import_module(src)
        sys.modules[dst] = mod
    except Exception:
        # If import fails, don't block test collection; tests that need the
        # module will raise a clear error.
        pass
import importlib
import os
import sys
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def patch_config_and_loggers(tmp_path_factory, monkeypatch):
    temp_dir = tmp_path_factory.mktemp("config")
    # Patch environment and paths before any import of researcharr.researcharr
    monkeypatch.setenv("TZ", "America/New_York")
    # Patch os.environ for tzset
    os.environ["TZ"] = "America/New_York"
    # Patch /config paths to temp_dir
    db_path = str(temp_dir / "researcharr.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    log_dir = temp_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    main_log = str(log_dir / "researcharr.log")
    radarr_log = str(log_dir / "radarr.log")
    sonarr_log = str(log_dir / "sonarr.log")
    config_path = temp_dir / "config.yml"
    with open(config_path, "w") as f:
        f.write(
            "researcharr:\n  timezone: America/New_York\n  puid: 1000\n  pgid: 1000\n"
            "  cron_schedule: '0 * * * *'\nradarr: []\nsonarr: []\n"
        )
    # Patch open for /config/config.yml
    import builtins

    real_open = builtins.open

    def patched_open(file, mode="r", *args, **kwargs):
        if str(file) == "/config/config.yml":
            return real_open(config_path, mode, *args, **kwargs)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", patched_open)

    # Patch logger setup to use temp log files
    def fake_setup_logger(name, log_file, level=None):
        logger = mock.Mock()
        logger.info = mock.Mock()
        logger.warning = mock.Mock()
        logger.error = mock.Mock()
        return logger

    sys.modules.pop("researcharr.researcharr", None)  # Ensure clean import
    monkeypatch.setattr("researcharr.researcharr.DB_PATH", db_path, raising=False)
    monkeypatch.setattr(
        "researcharr.researcharr.setup_logger", fake_setup_logger, raising=False
    )
    monkeypatch.setattr(
        "researcharr.researcharr.main_logger",
        fake_setup_logger("main_logger", main_log),
        raising=False,
    )
    monkeypatch.setattr(
        "researcharr.researcharr.radarr_logger",
        fake_setup_logger("radarr_logger", radarr_log),
        raising=False,
    )
    monkeypatch.setattr(
        "researcharr.researcharr.sonarr_logger",
        fake_setup_logger("sonarr_logger", sonarr_log),
        raising=False,
    )
    # Patch USER_CONFIG_PATH if needed
    monkeypatch.setattr(
        "researcharr.researcharr.USER_CONFIG_PATH",
        str(temp_dir / "webui_user.yml"),
        raising=False,
    )
    # Now import researcharr (all patches in place)
    importlib.import_module("researcharr.researcharr")
    yield
    # Cleanup handled by tmp_path_factory
