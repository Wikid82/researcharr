import logging


def test_dump_researcharr_cron_logger_state():
    cron_logger = logging.getLogger("researcharr.cron")
    root = logging.getLogger()
    print("DBG: researcharr.cron handlers:", len(cron_logger.handlers))
    print("DBG: researcharr.cron propagate:", cron_logger.propagate)
    print("DBG: researcharr.cron level:", cron_logger.level)
    print("DBG: root handlers:", len(root.handlers))
    # show names of handlers
    try:
        names = [getattr(h, "__class__", type(h)).__name__ for h in cron_logger.handlers]
        print("DBG: researcharr.cron handler types:", names)
    except Exception:
        pass


def test_debug_subprocess_capture(tmp_path):
    # Create a simple script and run it via subprocess.run using sys.executable
    import subprocess
    import sys

    script = tmp_path / "dbg_script.py"
    script.write_text("print('PKG_STDOUT')\nprint('PKG_STDERR', file=__import__('sys').stderr)\n")
    proc = subprocess.run(
        [sys.executable, str(script)], check=False, capture_output=True, text=True
    )
    print("DBG: child returncode:", proc.returncode)
    print("DBG: child stdout repr:", repr(proc.stdout))
    print("DBG: child stderr repr:", repr(proc.stderr))


def test_debug_invoke_run_job_and_dump_caplog(tmp_path, caplog):
    import importlib.util
    import os
    import sys

    # Create script
    script = tmp_path / "dbg_script2.py"
    script.write_text("print('PKG_STDOUT')\nprint('PKG_STDERR', file=__import__('sys').stderr)\n")

    # Set up caplog and env
    caplog.set_level("INFO", logger="researcharr.cron")
    os.environ["SCRIPT"] = str(script)

    # Force-load run module like the test does
    import researcharr

    path = os.path.join(os.path.dirname(researcharr.__file__), "run.py")
    sys.modules.pop("researcharr.run", None)
    spec = importlib.util.spec_from_file_location("researcharr.run", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    sys.modules["researcharr.run"] = mod

    # Call run_job and then dump caplog contents
    mod.run_job()
    print("DBG-CAPLOG: records count:", len(caplog.records))
    for r in caplog.records:
        print("DBG-CAPLOG: rec ->", r.levelname, r.getMessage())
    print("DBG-CAPLOG: text->", repr(caplog.text))
