import importlib
import os
import sys
from typing import Generator
from unittest import mock
from unittest.mock import Mock as _Mock

import pytest

from researcharr import factory


@pytest.fixture(autouse=True, scope="function")
def restore_researcharr_create_metrics_app():
    """Autouse fixture: backup and restore researcharr.create_metrics_app.

    Some tests (notably in test_package_helpers.py) directly mutate
    `researcharr.create_metrics_app` by assigning a Mock to it. This fixture
    ensures that the real function is restored after each test so subsequent
    tests don't inherit a Mock.
    """
    import researcharr
    from researcharr.core.services import create_metrics_app as _real_create

    # Backup the current value (which might already be a mock from a prior test)
    # We don't use the backup value — always restore the real function
    yield
    # Restore the real create_metrics_app function after the test
    researcharr.create_metrics_app = _real_create


@pytest.fixture(autouse=True)
def ensure_real_flask_module(request):
    """Autouse fixture to prevent tests from leaving a Mock under 'flask'.

    If a test has injected a Mock into `sys.modules['flask']`, replace it
    temporarily with the real `flask` package (if available) for the
    duration of the test, then restore the original value afterwards.
    """
    orig = sys.modules.get("flask")
    replaced = False

    # If the module is already a Mock at test-start, log which test is starting
    try:
        if isinstance(orig, _Mock):
            try:
                print(f"STARTING {request.node.nodeid}: sys.modules['flask'] is Mock at test start")
            except Exception:
                print("STARTING test: sys.modules['flask'] is Mock at test start")
        else:
            # Also detect if Flask.test_client is already mocked on the class
            try:
                FlaskCls = getattr(orig, "Flask", None)
                if FlaskCls is not None and isinstance(
                    getattr(FlaskCls, "test_client", None), _Mock
                ):
                    try:
                        print(
                            f"STARTING {request.node.nodeid}: flask.Flask.test_client is Mock at test start"
                        )
                    except Exception:
                        print("STARTING test: flask.Flask.test_client is Mock at test start")
            except Exception:
                pass
    except Exception:
        pass

    # Try to proactively ensure the real `flask` package is installed in
    # `sys.modules` for the duration of the test. This defends against
    # prior tests that mutated the module object or the `Flask` class
    # (for example replacing `Flask.test_client` with a Mock).
    try:
        spec = importlib.util.find_spec("flask")
        if spec and getattr(spec, "loader", None):
            try:
                real_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(real_mod)  # type: ignore[attr-defined]
                # Install the real module for the test duration (restored later)
                sys.modules["flask"] = real_mod
                replaced = True
            except Exception:
                # If we fail to load the real package, fall back to leaving
                # whatever is in sys.modules untouched.
                replaced = False
    except Exception:
        # Defensive: don't let fixture fail test setup
        replaced = False

    try:
        yield
    finally:
        # Restore original module state
        try:
            if replaced:
                # restore the original Mock
                sys.modules["flask"] = orig
            else:
                # If there was no original and a test added flask, remove it
                if orig is None:
                    sys.modules.pop("flask", None)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def detect_flask_pollution(request):
    """Autouse fixture: after each test, detect if sys.modules['flask'] is a Mock.

    If a test leaves a Mock in `sys.modules['flask']`, print the test nodeid so
    we can identify the polluter, and attempt to restore the real `flask`
    module for subsequent tests to reduce cascade failures.
    """
    yield
    try:
        import sys as _sys
        from unittest.mock import Mock as _Mock

        fm = _sys.modules.get("flask")
        if isinstance(fm, _Mock):
            print(f"POLLUTION DETECTED after {request.node.nodeid}: sys.modules['flask'] is Mock")
            try:
                import importlib.util as _util

                spec = _util.find_spec("flask")
                if spec is not None and getattr(spec, "loader", None):
                    mod = _util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    _sys.modules["flask"] = mod
                    print("Restored real 'flask' module after pollution")
            except Exception as _e:
                print("Failed to restore real flask module:", _e)
        else:
            # Also detect if the Flask class or its `test_client` attribute was mocked
            try:
                FlaskCls = getattr(fm, "Flask", None)
                if FlaskCls is not None:
                    tc = getattr(FlaskCls, "test_client", None)
                    if isinstance(tc, _Mock):
                        print(
                            f"POLLUTION DETECTED after {request.node.nodeid}: flask.Flask.test_client is Mock"
                        )
                        try:
                            import importlib.util as _util

                            spec = _util.find_spec("flask")
                            if spec is not None and getattr(spec, "loader", None):
                                mod = _util.module_from_spec(spec)
                                spec.loader.exec_module(mod)
                                _sys.modules["flask"] = mod
                                print("Restored real 'flask' module after class-level pollution")
                        except Exception as _e:
                            print("Failed to restore real flask module:", _e)
            except Exception:
                pass
    except Exception:
        # Never let this diagnostic break tests
        pass


"""Pytest session helpers.

Provide compatibility shim modules under the `researcharr.plugins.*` names
so older-style imports used by the test-suite resolve to the canonical
`plugins.*` implementations located at the repo root. Also provide a set
of shared fixtures used across the factory tests (app, client, login) and
an autouse patch that configures temporary paths and loggers.
"""

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


@pytest.fixture(autouse=True)
def patch_config_and_loggers(tmp_path_factory, monkeypatch):
    temp_dir = tmp_path_factory.mktemp("config")
    # Patch environment and paths before any import of researcharr.researcharr
    monkeypatch.setenv("TZ", "America/New_York")
    os.environ["TZ"] = "America/New_York"
    # Patch /config paths to temp_dir
    db_path = str(temp_dir / "researcharr.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # Ensure database is created in temp directory
    monkeypatch.setenv("RESEARCHARR_DB", db_path)
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
    sys.modules.pop("researcharr.db", None)  # Ensure clean db module import
    sys.modules.pop("webui", None)  # Ensure clean webui module import
    sys.modules.pop("researcharr.webui", None)  # Ensure clean webui package import
    monkeypatch.setattr("researcharr.researcharr.DB_PATH", db_path, raising=False)
    monkeypatch.setattr("researcharr.researcharr.setup_logger", fake_setup_logger, raising=False)
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
    # Ensure `researcharr.__path__` is deterministic for the test run.
    try:
        import researcharr as _ra

        _first = os.path.abspath(os.path.dirname(getattr(_ra, "__file__", "")))
        _second = os.path.abspath(os.path.join(_first, "researcharr"))
        if not os.path.isdir(_second):
            _second = _first
        try:
            _ra.__path__ = [_first, _second]
        except Exception:
            pass
    except Exception:
        pass
    yield
    # Cleanup handled by tmp_path_factory


def pytest_runtest_setup(item):
    # Debug hook removed; no-op to keep pytest hook signature available.
    yield
    try:
        import sys as _sys
        from unittest.mock import Mock as _Mock

        fl_mod = _sys.modules.get("flask")

        # Case A: the whole flask module is a Mock
        if isinstance(fl_mod, _Mock):
            print(f"POLLUTION DETECTED after {item.nodeid}: sys.modules['flask'] is Mock")
            try:
                import importlib.util as _util

                spec = _util.find_spec("flask")
                if spec is not None and getattr(spec, "loader", None):
                    real_mod = _util.module_from_spec(spec)
                    spec.loader.exec_module(real_mod)
                    _sys.modules["flask"] = real_mod
                    print("Restored real 'flask' module after pollution")
            except Exception as _e:
                print("Failed to restore real flask module:", _e)

        else:
            # Case B: flask module is present but its Flask class or test_client were mutated
            try:
                Flask_cls = getattr(fl_mod, "Flask", None)
                if Flask_cls is not None:
                    tc = getattr(Flask_cls, "test_client", None)
                    if isinstance(tc, _Mock):
                        print(f"POLLUTION DETECTED after {item.nodeid}: Flask.test_client is Mock")
                        # Try to restore the real Flask.test_client from the installed package
                        try:
                            import importlib.util as _util

                            spec = _util.find_spec("flask")
                            if spec is not None and getattr(spec, "loader", None):
                                real_mod = _util.module_from_spec(spec)
                                spec.loader.exec_module(real_mod)
                                real_Flask = getattr(real_mod, "Flask", None)
                                if real_Flask is not None and hasattr(real_Flask, "test_client"):
                                    # restore class attribute
                                    Flask_cls.test_client = real_Flask.test_client
                                    # replace module in sys.modules so future imports see the real one
                                    _sys.modules["flask"] = real_mod
                                    print(
                                        "Restored real Flask.test_client from real 'flask' module"
                                    )
                        except Exception as _e:
                            print("Failed to restore Flask.test_client:", _e)
            except Exception:
                # Defensive: don't let diagnostic break tests
                pass
    except Exception:
        # Never let this diagnostic break tests
        pass


@pytest.fixture(autouse=True)
def detect_flask_class_mutation(request):
    """Autouse fixture: snapshot `flask.Flask` identity and detect changes.

    This prints a concise diagnostic when the `Flask` class object changes
    between the start and end of a test so we can identify the test that
    mutates the class or replaces the module with a Mock.
    """
    import sys as _sys

    try:
        fm = _sys.modules.get("flask")
        before = getattr(fm, "Flask", None) if fm is not None else None
        before_id = id(before) if before is not None else None
    except Exception:
        before = None
        before_id = None

    yield

    try:
        fm2 = _sys.modules.get("flask")
        after = getattr(fm2, "Flask", None) if fm2 is not None else None
        after_id = id(after) if after is not None else None
        if before_id != after_id:
            try:
                print(
                    f"FLASK_CLASS_MUTATED after {request.node.nodeid}: before_id={before_id} after_id={after_id} type(before)={type(before)} type(after)={type(after)}"
                )
            except Exception:
                print("FLASK_CLASS_MUTATED: (failed to format nodeid)")
    except Exception:
        # Do not let diagnostic break tests
        pass


@pytest.fixture
def login(client):
    def _login(username: str = "admin", password: str = "password"):
        return client.post("/login", data={"username": username, "password": password})

    return _login


@pytest.fixture
def app(monkeypatch, tmp_path) -> Generator:
    # Provide a shared application fixture for tests that rely on a global
    # `client` fixture being available from conftest. Keep this lightweight
    # because `patch_config_and_loggers` already prepares env and config.
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    app = factory.create_app()
    app.testing = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
