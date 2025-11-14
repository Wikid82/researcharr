import importlib
import textwrap
from pathlib import Path

import pytest


def _get_run_mod():
    # Import the package submodule explicitly to exercise researcharr/run.py
    return importlib.import_module("researcharr.run")


def _write_script(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "script.py"
    p.write_text(textwrap.dedent(content))
    return p


@pytest.mark.no_xdist
def test_run_job_success_captures_output(tmp_path, monkeypatch, caplog):
    caplog.set_level("INFO", logger="researcharr.cron")
    script = _write_script(
        tmp_path,
        """
        import sys
        print('STDOUT_LINE')
        print('ERR_LINE', file=sys.stderr)
        """,
    )
    monkeypatch.setenv("SCRIPT", str(script))
    # Ensure no timeout so normal branch executes
    monkeypatch.delenv("JOB_TIMEOUT", raising=False)
    _get_run_mod().run_job()
    assert any("STDOUT_LINE" in r.message for r in caplog.records)
    assert any("ERR_LINE" in r.message for r in caplog.records)


@pytest.mark.no_xdist
def test_run_job_timeout_branch(tmp_path, monkeypatch, caplog):
    caplog.set_level("INFO", logger="researcharr.cron")
    script = _write_script(
        tmp_path,
        """
        import time
        time.sleep(0.2)
        print('NEVER_REACHED')
        """,
    )
    monkeypatch.setenv("SCRIPT", str(script))
    # Force very small timeout to trigger the timeout path
    monkeypatch.setenv("JOB_TIMEOUT", "0.01")
    _get_run_mod().run_job()
    assert any("exceeded timeout" in r.message for r in caplog.records)
