import importlib.util
import os
import sys
import textwrap
from pathlib import Path


def _write_script(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "script.py"
    p.write_text(textwrap.dedent(content))
    return p


def _load_pkg_run():
    pkg = importlib.import_module("researcharr")
    path = os.path.join(os.path.dirname(pkg.__file__), "run.py")
    sys.modules.pop("researcharr.run", None)
    sys.modules.pop("run", None)
    spec = importlib.util.spec_from_file_location("researcharr.run", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    sys.modules["researcharr.run"] = mod
    return mod


def test_caplog_global_captures(tmp_path, monkeypatch, caplog):
    caplog.set_level("INFO")
    script = _write_script(
        tmp_path,
        """
        import sys
        print('PKG_STDOUT')
        print('PKG_STDERR', file=sys.stderr)
        """,
    )
    monkeypatch.setenv("SCRIPT", str(script))
    monkeypatch.delenv("JOB_TIMEOUT", raising=False)
    run_mod = _load_pkg_run()
    run_mod.run_job()
    # persist caplog records for inspection
    out = Path("/tmp/researcharr-bisect/caplog_all_records.log")
    out.write_text("\n".join([repr(r) for r in caplog.records]))
    assert any("PKG_STDOUT" in r.message for r in caplog.records) or any(
        "PKG_STDERR" in r.message for r in caplog.records
    )
