import importlib
import subprocess
from unittest.mock import patch

import pytest


@pytest.mark.no_xdist
def test_run_job_handles_timeout(caplog, monkeypatch, tmp_path):
    caplog.set_level("INFO", logger="researcharr.cron")
    run_mod = importlib.import_module("researcharr.run")

    # Force TimeoutExpired from subprocess.run
    def _raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["x"], timeout=0.01)

    with patch("subprocess.run", _raise_timeout):
        run_mod.run_job()
    assert any("timeout" in r.message.lower() for r in caplog.records)


@pytest.mark.no_xdist
def test_run_job_handles_generic_exception(caplog, monkeypatch):
    caplog.set_level("INFO", logger="researcharr.cron")
    run_mod = importlib.import_module("researcharr.run")

    def _raise_error(*a, **k):
        raise RuntimeError("boom")

    with patch("subprocess.run", _raise_error):
        run_mod.run_job()
    assert any("encountered an error" in r.message for r in caplog.records)
