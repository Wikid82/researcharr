import os
import types

import pytest

import researcharr.run as run


def make_dummy_result(stdout="", stderr="", returncode=0):
    r = types.SimpleNamespace()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def test_run_job_logs_success(tmp_path, monkeypatch):
    # Use a temp log path
    lp = tmp_path / "cron.log"
    monkeypatch.setattr(run, "LOG_PATH", str(lp))

    # Replace subprocess.run so no real process is spawned
    def fake_run(cmd, capture_output=True, text=True):
        return make_dummy_result(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr(run, "subprocess", types.SimpleNamespace(run=fake_run))

    # Setup logger and run the job
    run.setup_logger()
    run.run_job()

    txt = lp.read_text()
    assert "Starting scheduled job" in txt
    assert "Job stdout" in txt
    assert "Job finished with returncode 0" in txt


def test_main_once_mode_shuts_down_quickly(tmp_path, monkeypatch):
    # Ensure config path exists and set default cron
    cfg = tmp_path / "config.yml"
    cfg.write_text("researcharr:\n  cron_schedule: '*/5 * * * *'\n")
    monkeypatch.setattr(run, "CONFIG_PATH", str(cfg))

    # Use temp log path
    lp = tmp_path / "cron2.log"
    monkeypatch.setattr(run, "LOG_PATH", str(lp))

    # Patch run_job to avoid spawning processes and to record it was called
    called = {"v": 0}

    def fake_run_job():
        called["v"] += 1

    monkeypatch.setattr(run, "run_job", fake_run_job)

    # Call main in once mode; it should return quickly after running fake_run_job
    run.main(once=True)

    assert called["v"] == 1
    # Check for the one-shot log message
    txt = lp.read_text()
    assert "One-shot mode: exiting after running scheduled job once" in txt
