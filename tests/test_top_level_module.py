import importlib.util
import os
from types import SimpleNamespace


def load_top_level_module(tmp_path):
    path = os.path.abspath("entrypoint.py")
    spec = importlib.util.spec_from_file_location("researcharr_impl", path)
    # Ensure spec and its loader are present before creating a module from it
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


def test_top_level_setup_logger(tmp_path):
    mod = load_top_level_module(tmp_path)
    log_file = tmp_path / "tl.log"
    logger = mod.setup_logger("tl", str(log_file), level=10)
    assert hasattr(logger, "info")
    logger.info("ok")
    assert log_file.exists()
    assert "ok" in log_file.read_text()


def test_top_level_check_radarr_non_200(monkeypatch):
    mod = load_top_level_module(monkeypatch)
    logger = SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None)

    class DummyResp:
        status_code = 500

    monkeypatch.setattr(mod, "requests", SimpleNamespace(get=lambda url: DummyResp()))
    result = mod.check_radarr_connection("http://x", "k", logger)
    assert result is False


def test_top_level_load_config(tmp_path):
    mod = load_top_level_module(tmp_path)
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("radarr: []\n")
    out = mod.load_config(path=str(cfg))
    assert isinstance(out, dict)
