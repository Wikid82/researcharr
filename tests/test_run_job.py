import logging
import os


def _write_sleep_script(path, sleep_seconds=2):
    with open(path, "w") as f:
        f.write(
            """
import time
import sys
print('start')
sys.stdout.flush()
time.sleep(%d)
print('end')
"""
            % sleep_seconds
        )
    os.chmod(path, 0o755)


def test_run_job_timeout(tmp_path, monkeypatch, caplog):
    """Verify that a long-running job is killed when JOB_TIMEOUT is set."""
    # Prepare a small python script that sleeps longer than the timeout
    script = tmp_path / "sleep_script.py"
    _write_sleep_script(str(script), sleep_seconds=4)

    # Point the run.SCRIPT to our small script and set environment
    import researcharr.run as run_mod

    monkeypatch.setenv("JOB_TIMEOUT", "1")
    monkeypatch.setenv("RUN_JOB_CONCURRENCY", "1")
    monkeypatch.setenv("JOB_RLIMIT_AS_MB", "")
    monkeypatch.setenv("JOB_RLIMIT_CPU_SECONDS", "")

    # Use a temp log file to capture messages
    logfile = tmp_path / "cron.log"
    monkeypatch.setenv("LOG_PATH", str(logfile))
    run_mod.LOG_PATH = str(logfile)
    run_mod.SCRIPT = str(script)
    # Ensure researcharr.run.run_job reads the script path from the environment,
    # so the subprocess picks up the correct test script path.
    monkeypatch.setenv("SCRIPT", str(script))

    caplog.set_level(logging.INFO)
    # Call run_job() which should timeout and log an error
    run_mod.run_job()

    # Check that a timeout message was logged
    logs = caplog.text
    assert "exceeded timeout" in logs or "was killed" in logs
