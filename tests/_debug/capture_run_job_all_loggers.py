import importlib
import logging
import pathlib

OUTDIR = pathlib.Path("/tmp/researcharr-bisect")
OUTDIR.mkdir(parents=True, exist_ok=True)


def _write_script(tmp_path):
    p = tmp_path / "script.py"
    p.write_text("""
import sys
print('PKG_STDOUT')
print('PKG_STDERR', file=sys.stderr)
""")
    return str(p)


def test_capture_run_job_to_file(tmp_path, monkeypatch):
    # prepare environment similar to test_pkg_run_job_executes_and_logs
    script = _write_script(tmp_path)
    monkeypatch.setenv("SCRIPT", script)
    monkeypatch.delenv("JOB_TIMEOUT", raising=False)

    # attach a root handler that writes to a file to capture any emitted logs
    out = OUTDIR / "run_job_all.log"
    # ensure file is empty
    open(out, "w").close()

    fh = out.open("a")
    h = logging.StreamHandler(fh)
    h.setLevel(logging.INFO)
    logging.getLogger().addHandler(h)
    try:
        # import the module that provides run_job
        run_mod = importlib.import_module("researcharr.run")
        # call run_job() which should emit logs about child stdout/stderr
        run_mod.run_job()
    finally:
        logging.getLogger().removeHandler(h)
        fh.close()

    content = out.read_text()
    assert ("PKG_STDOUT" in content) or ("PKG_STDERR" in content)
