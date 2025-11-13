import importlib
import os
import sys
from collections.abc import Generator
from unittest import mock
from unittest.mock import Mock as _Mock

import pytest

# Suppress the helper helper logs written early during import (e.g., during
# package proxy initialization). We do this at module import time so logs from
# `researcharr._factory_proxy` that fire during import/collection are filtered
# before any autouse fixtures run. Use RESEARCHARR_VERBOSE_FACTORY_HELPER=1 to
# opt-into seeing those logs.
_ORIG_STDERR = sys.stderr
_ORIG_STDERR_WRITE = getattr(sys.stderr, "write", None)
try:
    _VERBOSE_FACTORY_HELPER = os.environ.get("RESEARCHARR_VERBOSE_FACTORY_HELPER", "0") == "1"
except Exception:
    _VERBOSE_FACTORY_HELPER = False

if not _VERBOSE_FACTORY_HELPER and _ORIG_STDERR_WRITE is not None:

    class _FilteredStderr:
        """Wrap the original stderr to filter the factory helper logs.

        We proxy the common file-like methods so external libraries that call
        `sys.stderr.write`/`writelines`/`flush` continue to operate normally.
        """

        def __init__(self, orig):
            self._orig = orig

        def write(self, s):
            try:
                if isinstance(s, str) and (
                    "[factory-helper-access]" in s or "[pkg-attr-access]" in s
                ):
                    return len(s)
            except Exception:
                pass
            return self._orig.write(s)

        def writelines(self, lines):
            try:
                return self._orig.writelines(lines)
            except Exception:
                # best-effort; don't break tests if writelines isn't present
                for line in lines:
                    self.write(line)

        def flush(self):
            try:
                return self._orig.flush()
            except Exception:
                pass

        def fileno(self):
            try:
                return self._orig.fileno()
            except Exception:
                raise

        @property
        def encoding(self):
            return getattr(self._orig, "encoding", None)

        @property
        def errors(self):
            return getattr(self._orig, "errors", None)

        def isatty(self):
            try:
                return self._orig.isatty()
            except Exception:
                return False

    # Swap out the global stderr object for our wrapper so import-time writes
    # performed by early module initialization are filtered too.
    try:
        sys.stderr = _FilteredStderr(sys.stderr)
    except Exception:
        # Best-effort: if we can't swap, continue without filtering.
        pass

# Ensure repository root is on sys.path so top-level shim modules
# like `entrypoint`, `run`, and `backups` remain importable after the
# test directory reorganization.
try:
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
except Exception:
    pass

import logging as _logging
import unittest.mock as _um

# Autouse fixture to restore the real run.run_job implementation if earlier tests
# replaced it with a Mock. This prevents later run-focused tests from observing
# a stubbed function and missing expected logging/subprocess behavior.
import pytest as _pytest

# Preserve original logging.getLogger so we can restore if a test leaves a patch behind.
_ORIGINAL_GETLOGGER = getattr(_logging, "getLogger", None)

from researcharr import factory

# Record an early snapshot of sys.modules for a few sensitive module names.
# Capturing this at conftest import time preserves the pre-collection module
# identities (before test modules are imported/collected) so we can restore
# the original module objects if tests later replace or inject alternative
# module objects during collection or test execution.
_EARLY_ORIGINAL_MODULES = {}
try:
    for _m in ("researcharr", "researcharr.backups"):
        _EARLY_ORIGINAL_MODULES[_m] = sys.modules.get(_m)
except Exception:
    _EARLY_ORIGINAL_MODULES = {}

# Also capture early values for __all__ on the same modules so we can restore
# their public export lists if tests mutate them at runtime.
_EARLY_ORIGINAL_ALLS = {}
try:
    import importlib as _il

    for _m in ("researcharr", "researcharr.backups"):
        try:
            _mod = _il.import_module(_m)
            if hasattr(_mod, "__all__"):
                _EARLY_ORIGINAL_ALLS[_m] = list(getattr(_mod, "__all__", None))
            else:
                _EARLY_ORIGINAL_ALLS[_m] = None
        except Exception:
            _EARLY_ORIGINAL_ALLS[_m] = None
except Exception:
    _EARLY_ORIGINAL_ALLS = {}


@_pytest.fixture(autouse=True)
def _restore_run_job_if_mock():
    try:
        import run as _top_run

        if isinstance(getattr(_top_run, "run_job", None), _um.Mock):
            real = getattr(_top_run, "ORIGINAL_RUN_JOB", None)
            if callable(real):
                _top_run.run_job = real
    except Exception:
        pass
    # allow test to run, then perform teardown to restore package-level run_job
    yield
    try:
        import researcharr as _pkg

        _pkg_run = getattr(_pkg, "run", None)
        if _pkg_run is not None and isinstance(getattr(_pkg_run, "run_job", None), _um.Mock):
            real2 = getattr(_pkg_run, "ORIGINAL_RUN_JOB", None)
            if callable(real2):
                _pkg_run.run_job = real2
    except Exception:
        pass


@_pytest.fixture(autouse=True)
def _suppress_factory_helper_logs(monkeypatch):
    """Silently drop noisy factory-helper lines from stderr unless explicitly enabled.

    These helper logs can make test output noisy. By default we suppress them
    in the test run; set RESEARCHARR_VERBOSE_FACTORY_HELPER=1 to opt into
    seeing the helper logs for troubleshooting.
    """
    try:
        verbose = os.environ.get("RESEARCHARR_VERBOSE_FACTORY_HELPER", "0") == "1"
    except Exception:
        verbose = False
    if verbose:
        yield
        return
    # Patch sys.stderr.write to filter the factory helper and pkg-attr logs.
    orig_write = sys.stderr.write

    def _filtered_write(s):
        try:
            if isinstance(s, str) and ("[factory-helper-access]" in s or "[pkg-attr-access]" in s):
                # mimic sys.stderr.write return of number of written chars
                return len(s)
        except Exception:
            pass
        return orig_write(s)

    monkeypatch.setattr(sys.stderr, "write", _filtered_write)
    try:
        yield
    finally:
        monkeypatch.setattr(sys.stderr, "write", orig_write)


def pytest_unconfigure(config):
    """Restore original stderr.write when tests complete.

    This ensures we don't leave the patched write globally changed after the
    test run completes (useful when running tests in interactive sessions).
    """
    # Restore the original sys.stderr object so interactive sessions or
    # other test harnesses are not left with our wrapper.
    try:
        if globals().get("_ORIG_STDERR") is not None:
            sys.stderr = globals().get("_ORIG_STDERR")
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _diagnose_predecessor_module_state(request):
    """If running the known predecessor test, dump a before/after snapshot of
    `sys.modules['researcharr.backups']` and related details to /tmp so we can
    see exactly when and how the mapping or its `__all__` is changed.

    This triggers only when the test nodeid matches the predecessor:
    `tests/package/test_package_shim_reconciliation.py::test_backups_identity_reconciliation`.
    """
    try:
        node = getattr(request, "node", None)
        nodeid = getattr(node, "nodeid", "")
    except Exception:
        nodeid = ""

    target = (
        "tests/package/test_package_shim_reconciliation.py::test_backups_identity_reconciliation"
    )
    if nodeid != target:
        yield
        return

    import json as _json
    import os as _os
    import time as _time

    outdir = "/tmp/researcharr-bisect/predecessor-diag"
    try:
        _os.makedirs(outdir, exist_ok=True)
    except Exception:
        pass

    def _snap(kind: str):
        try:
            import sys as _sys

            mod = _sys.modules.get("researcharr.backups")
            info = {
                "time": _time.time(),
                "nodeid": nodeid,
                "module_present": mod is not None,
                "module_id": id(mod) if mod is not None else None,
                "module_repr": repr(mod) if mod is not None else None,
                "module_file": getattr(mod, "__file__", None) if mod is not None else None,
                "module___all__": list(getattr(mod, "__all__", None))
                if (mod is not None and hasattr(mod, "__all__"))
                else None,
            }
            # Also collect any sys.modules entries that contain 'backups'
            backups_keys = [k for k in _sys.modules.keys() if "backups" in k]
            backups_map = {}
            for k in backups_keys:
                try:
                    m = _sys.modules.get(k)
                    backups_map[k] = {
                        "id": id(m) if m is not None else None,
                        "repr": repr(m) if m is not None else None,
                        "file": getattr(m, "__file__", None) if m is not None else None,
                        "__all__": list(getattr(m, "__all__", None))
                        if (m is not None and hasattr(m, "__all__"))
                        else None,
                    }
                except Exception:
                    backups_map[k] = {"error": "failed to inspect"}
            info["backups_modules_map"] = backups_map
        except Exception as _e:
            info = {"error": str(_e)}

        try:
            p = f"{outdir}/{kind}.json"
            with open(p, "w") as _f:
                _f.write(_json.dumps(info, indent=2, default=str))
        except Exception:
            pass

    # take before snapshot
    _snap("before")
    yield
    # take after snapshot
    _snap("after")


@_pytest.fixture(autouse=True)
def _restore_create_metrics_app_if_mock():
    """Restore real create_metrics_app implementations if they were mocked.

    This prevents mock leakage across parallel test workers where one test
    patches create_metrics_app globally and affects other tests expecting
    the real implementation.
    """
    # Save original implementations before test
    _originals = {}

    try:
        import researcharr

        _originals["researcharr"] = getattr(researcharr, "create_metrics_app", None)
    except Exception:
        pass

    try:
        import researcharr.core.services as _services

        _originals["services"] = getattr(_services, "create_metrics_app", None)
    except Exception:
        pass

    try:
        import researcharr.researcharr as _impl

        _originals["impl"] = getattr(_impl, "create_metrics_app", None)
    except Exception:
        pass

    yield

    # After test: restore originals if they were replaced with mocks
    try:
        import researcharr

        current = getattr(researcharr, "create_metrics_app", None)
        if isinstance(current, _um.Mock) and _originals.get("researcharr") is not None:
            if not isinstance(_originals["researcharr"], _um.Mock):
                researcharr.create_metrics_app = _originals["researcharr"]
    except Exception:
        pass

    try:
        import researcharr.core.services as _services

        current = getattr(_services, "create_metrics_app", None)
        if isinstance(current, _um.Mock) and _originals.get("services") is not None:
            if not isinstance(_originals["services"], _um.Mock):
                _services.create_metrics_app = _originals["services"]
    except Exception:
        pass

    try:
        import researcharr.researcharr as _impl

        current = getattr(_impl, "create_metrics_app", None)
        if isinstance(current, _um.Mock) and _originals.get("impl") is not None:
            if not isinstance(_originals["impl"], _um.Mock):
                _impl.create_metrics_app = _originals["impl"]
    except Exception:
        pass


@_pytest.fixture(autouse=True, scope="function")
def _preserve_root_logger_handlers():
    """Preserve and restore root logger handlers to prevent caplog interference.

    Some tests may call logging.basicConfig() or manipulate root logger handlers,
    which breaks pytest's caplog fixture for subsequent tests. This fixture saves
    the handler list before each test and restores it after.
    """
    import logging

    root = logging.getLogger()
    # Save the current handlers (make a copy of the list)
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_disabled = root.disabled

    yield

    # Restore the original handlers after the test
    root.handlers[:] = saved_handlers
    root.level = saved_level
    root.disabled = saved_disabled


@_pytest.fixture(autouse=True, scope="function")
def _clear_researcharr_cron_handlers():
    """Ensure `researcharr.cron` has no persistent handlers during each test.

    Some tests add handlers directly to `researcharr.cron` and don't restore
    them. That prevents pytest's caplog from reliably capturing messages.
    Clear handlers before the test and restore them afterwards.
    """
    try:
        import logging

        logger = logging.getLogger("researcharr.cron")
        saved = list(logger.handlers)
        logger.handlers[:] = []
    except Exception:
        saved = None
    try:
        yield
    finally:
        try:
            if saved is not None:
                logger.handlers[:] = saved
        except Exception:
            pass


@_pytest.fixture(autouse=True, scope="function")
def _reset_logger_levels_before_and_after_test():
    """Reset all logger levels before and after each test to prevent pollution.

    Running this BEFORE the test ensures caplog gets attached to a clean logger.
    """
    # Reset BEFORE the test
    try:
        import logging

        mgr = logging.root.manager
        # Reset any logger that belongs to the researcharr hierarchy so
        # tests cannot permanently disable them (which breaks pytest caplog).
        try:
            for name, lg in list(mgr.loggerDict.items()):
                if not isinstance(name, str):
                    continue
                if name.startswith("researcharr"):
                    try:
                        real_logger = logging.getLogger(name)
                        real_logger.setLevel(logging.NOTSET)
                        real_logger.propagate = True
                        real_logger.disabled = False
                    except Exception:
                        # best-effort
                        pass
        except Exception:
            # fallback to resetting the most critical researcharr loggers
            logger = logging.getLogger("researcharr.cron")
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
            logger.disabled = False

        # Reset the researcharr.core.lifecycle logger explicitly as a safety-net
        lifecycle_logger = logging.getLogger("researcharr.core.lifecycle")
        lifecycle_logger.setLevel(logging.NOTSET)
        lifecycle_logger.propagate = True
    except Exception:
        pass

    yield

    # Reset AFTER the test as well
    try:
        import logging

        mgr = logging.root.manager
        try:
            for name, lg in list(mgr.loggerDict.items()):
                if not isinstance(name, str):
                    continue
                if name.startswith("researcharr"):
                    try:
                        real_logger = logging.getLogger(name)
                        real_logger.setLevel(logging.NOTSET)
                        real_logger.propagate = True
                        real_logger.disabled = False
                    except Exception:
                        pass
        except Exception:
            # best-effort fallback
            logger = logging.getLogger("researcharr.cron")
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
            logger.disabled = False

        lifecycle_logger = logging.getLogger("researcharr.core.lifecycle")
        lifecycle_logger.setLevel(logging.NOTSET)
        lifecycle_logger.propagate = True
    except Exception:
        pass


@_pytest.fixture(autouse=True)
def _restore_logging_getLogger_if_mock():
    """Ensure logging.getLogger is the real function, not a lingering Mock.

    Some tests patch logging.getLogger; if a patch leaks (due to nested test
    definitions or unexpected exceptions) subsequent tests depending on real
    logger behavior (caplog) will observe a MagicMock and fail to capture.
    This fixture defensively restores the original function before each test.
    """
    try:
        import logging as _lg
        import unittest.mock as _um

        if isinstance(getattr(_lg, "getLogger", None), _um.Mock) and callable(_ORIGINAL_GETLOGGER):
            _lg.getLogger = _ORIGINAL_GETLOGGER  # type: ignore[assignment]
    except Exception:
        pass
    yield


@_pytest.fixture(autouse=True)
def _restore_run_script_after_test():
    """Restore researcharr.run.SCRIPT and run.SCRIPT to their original values after each test.

    This prevents test pollution where one test patches SCRIPT and affects
    subsequent tests that expect the default value. We need to restore both
    the package module and the top-level module.
    """
    _sentinel = object()

    # Save original values from both modules
    try:
        import researcharr.run as _pkg_run_mod

        _pkg_original_script = getattr(_pkg_run_mod, "SCRIPT", _sentinel)
    except Exception:
        _pkg_run_mod = None
        _pkg_original_script = _sentinel

    try:
        import sys

        _top_run_mod = sys.modules.get("run")
        if _top_run_mod is not None:
            _top_original_script = getattr(_top_run_mod, "SCRIPT", _sentinel)
        else:
            _top_original_script = _sentinel
    except Exception:
        _top_run_mod = None
        _top_original_script = _sentinel

    yield

    # Restore original SCRIPT values after test
    if _pkg_run_mod is not None:
        try:
            if _pkg_original_script is not _sentinel:
                _pkg_run_mod.SCRIPT = _pkg_original_script
            elif hasattr(_pkg_run_mod, "SCRIPT"):
                try:
                    delattr(_pkg_run_mod, "SCRIPT")
                except AttributeError:
                    pass
        except Exception:
            pass

    if _top_run_mod is not None:
        try:
            import sys

            _top_run_mod = sys.modules.get("run")  # Re-fetch in case it changed
            if _top_run_mod is not None:
                # For the top-level shim, we need to remove SCRIPT from __dict__
                # if it was added directly, rather than trying to set it (which
                # would add it to __dict__ and bypass the shim's __getattr__).
                # The shim should always forward SCRIPT lookups to _impl.
                if "SCRIPT" in getattr(_top_run_mod, "__dict__", {}):
                    try:
                        delattr(_top_run_mod, "SCRIPT")
                    except AttributeError:
                        pass
        except Exception:
            pass


# Inline the storage layer fixtures locally instead of using pytest_plugins
# to avoid plugin import path issues in certain environments.
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from researcharr.storage.models import Base


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture
def db_session(temp_db):
    engine = create_engine(f"sqlite:///{temp_db}", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


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
            # If there was no original and a test added flask, remove it
            elif orig is None:
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
        # Ensure parent directories exist when opening for write/append/create
        try:
            import os as _os

            if isinstance(file, (str, bytes)) or hasattr(file, "__fspath__"):
                # Only attempt to create parent dir for filesystem paths
                if any(m in mode for m in ("w", "a", "x")):
                    try:
                        parent = _os.path.dirname(str(file))
                        if parent:
                            _os.makedirs(parent, exist_ok=True)
                    except Exception:
                        # Best-effort: do not fail open if directory creation fails
                        pass
        except Exception:
            pass

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
    # Keep the original diagnostic behavior, but also take a pre-test snapshot
    try:
        import json as _json
        import logging as _logging
        import os as _os

        from prometheus_client import core as _core

        _out = "/tmp/researcharr-bisect/logsnap"
        try:
            _os.makedirs(_out, exist_ok=True)
        except Exception:
            pass

        def _take():
            mgr = _logging.root.manager
            d = {}
            try:
                items = list(mgr.loggerDict.items())
            except Exception:
                items = []
            for name, logger in items[:200]:
                try:
                    d[name] = {
                        "type": type(logger).__name__,
                        "handlers": [type(h).__name__ for h in getattr(logger, "handlers", [])],
                        "level": getattr(logger, "level", None),
                        "propagate": getattr(logger, "propagate", None),
                    }
                except Exception as e:
                    d[name] = {"error": str(e)}
            prom = []
            try:
                reg = _core.REGISTRY
                if hasattr(reg, "_collector_to_names"):
                    prom = [type(c).__name__ for c in reg._collector_to_names.keys()]
                elif hasattr(reg, "collectors"):
                    prom = [type(c).__name__ for c in reg.collectors]
                else:
                    prom = [repr(reg)]
            except Exception as e:
                prom = [f"ERR:{e}"]
            return {"logger_sample": dict(list(d.items())[:200]), "prometheus": prom}

        try:
            safe = item.nodeid.replace("::", "__").replace("/", "_")
            p = _os.path.join(_out, f"pre_{safe}.json")
            with open(p, "w") as _f:
                _f.write(_json.dumps(_take(), indent=2, default=str))
        except Exception:
            pass
    except Exception:
        pass

    # Existing flask-pollution diagnostic (post-test actions remain below via hook)
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

    # Also take a post-test snapshot in teardown hook; pytest will call pytest_runtest_teardown separately


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


@pytest.fixture
def mock_filesystem():
    """Mock FileSystemService for testing without actual file I/O.

    Provides an in-memory filesystem mock that tracks all file operations.
    Usage:
        def test_something(mock_filesystem):
            mock_filesystem.files['/path/to/file.txt'] = 'content'
            assert mock_filesystem.read_text('/path/to/file.txt') == 'content'
    """

    class MockFileSystem:
        def __init__(self):
            self.files = {}
            self.directories = {"/"}

        def exists(self, path):
            from pathlib import Path

            p = str(Path(path))
            return p in self.files or p in self.directories

        def read_text(self, path, encoding="utf-8"):
            from pathlib import Path

            p = str(Path(path))
            if p not in self.files:
                raise FileNotFoundError(p)
            content = self.files[p]
            if isinstance(content, bytes):
                return content.decode(encoding)
            return content

        def write_text(self, path, content, encoding="utf-8"):
            from pathlib import Path

            p = str(Path(path))
            self.files[p] = content
            # Ensure parent directories exist
            parent = str(Path(p).parent)
            self.directories.add(parent)

        def read_bytes(self, path):
            from pathlib import Path

            p = str(Path(path))
            if p not in self.files:
                raise FileNotFoundError(p)
            content = self.files[p]
            if isinstance(content, str):
                return content.encode("utf-8")
            return content

        def write_bytes(self, path, content):
            from pathlib import Path

            p = str(Path(path))
            self.files[p] = content
            parent = str(Path(p).parent)
            self.directories.add(parent)

        def mkdir(self, path, parents=True, exist_ok=True):
            from pathlib import Path

            p = str(Path(path))
            if not exist_ok and p in self.directories:
                raise FileExistsError(p)
            self.directories.add(p)
            if parents:
                current = Path(p)
                while str(current.parent) != str(current):
                    self.directories.add(str(current.parent))
                    current = current.parent

        def remove(self, path):
            from pathlib import Path

            p = str(Path(path))
            if p in self.files:
                del self.files[p]
            elif p in self.directories:
                self.directories.remove(p)

        def rmtree(self, path):
            from pathlib import Path

            p = str(Path(path))
            # Remove all files and subdirectories starting with this path
            to_remove_files = [f for f in self.files if f.startswith(p + "/") or f == p]
            to_remove_dirs = [d for d in self.directories if d.startswith(p + "/") or d == p]
            for f in to_remove_files:
                del self.files[f]
            for d in to_remove_dirs:
                self.directories.remove(d)

        def listdir(self, path):
            from pathlib import Path

            p = str(Path(path))
            if not p.endswith("/"):
                p += "/"
            items = set()
            for f in self.files:
                if f.startswith(p):
                    rel = f[len(p) :]
                    if "/" not in rel:
                        items.add(rel)
            for d in self.directories:
                if d.startswith(p) and d != p:
                    rel = d[len(p) :]
                    if "/" in rel:
                        items.add(rel.split("/")[0])
                    else:
                        items.add(rel)
            return list(items)

        def copy(self, src, dst):
            from pathlib import Path

            s = str(Path(src))
            d = str(Path(dst))
            if s not in self.files:
                raise FileNotFoundError(s)
            self.files[d] = self.files[s]

        def move(self, src, dst):
            from pathlib import Path

            s = str(Path(src))
            d = str(Path(dst))
            if s not in self.files:
                raise FileNotFoundError(s)
            self.files[d] = self.files[s]
            del self.files[s]

        def get_size(self, path):
            from pathlib import Path

            p = str(Path(path))
            if p not in self.files:
                raise FileNotFoundError(p)
            content = self.files[p]
            if isinstance(content, bytes):
                return len(content)
            return len(content.encode("utf-8"))

        def is_file(self, path):
            from pathlib import Path

            return str(Path(path)) in self.files

        def is_dir(self, path):
            from pathlib import Path

            return str(Path(path)) in self.directories

        def open(self, path, mode="r", encoding=None):
            """Mock open() that returns a file-like object."""
            from io import BytesIO, StringIO
            from pathlib import Path

            p = str(Path(path))

            if "r" in mode:
                if p not in self.files:
                    raise FileNotFoundError(p)
                content = self.files[p]
                if "b" in mode:
                    if isinstance(content, str):
                        return BytesIO(content.encode(encoding or "utf-8"))
                    return BytesIO(content)
                else:
                    if isinstance(content, bytes):
                        return StringIO(content.decode(encoding or "utf-8"))
                    return StringIO(content)
            elif "b" in mode:
                buffer = BytesIO()
                original_close = buffer.close

                def close_wrapper():
                    self.files[p] = buffer.getvalue()
                    original_close()

                buffer.close = close_wrapper
                return buffer
            else:
                buffer = StringIO()
                original_close = buffer.close

                def close_wrapper():
                    self.files[p] = buffer.getvalue()
                    original_close()

                buffer.close = close_wrapper
                return buffer

    return MockFileSystem()


@pytest.fixture
def mock_http_client():
    """Mock HttpClientService for testing without actual HTTP requests.

    Usage:
        def test_something(mock_http_client):
            mock_http_client.get.return_value.status_code = 200
            mock_http_client.get.return_value.json.return_value = {'key': 'value'}
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    # Setup default responses
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = {}
    mock.post.return_value.status_code = 200
    mock.post.return_value.json.return_value = {}
    mock.put.return_value.status_code = 200
    mock.put.return_value.json.return_value = {}
    mock.delete.return_value.status_code = 204

    return mock


def pytest_collection_modifyitems(config, items):
    """Pytest hook to handle special markers.

    Tests marked with @pytest.mark.no_xdist will be modified to run
    without xdist parallelization by checking if we're in an xdist worker
    and skipping the test if so (it will run in the main process instead).
    """
    # Check if xdist is active
    if hasattr(config, "workerinput"):
        # We're in an xdist worker - skip tests marked no_xdist
        skip_xdist = pytest.mark.skip(reason="Test marked no_xdist, run in main process")
        for item in items:
            if "no_xdist" in item.keywords:
                item.add_marker(skip_xdist)


def pytest_ignore_collect(path, config):
    """Exclude specific duplicate-basename test modules from collection.

    Avoids import file mismatch when two different directories contain
    files with the same basename (e.g., test_webui_shim.py).
    """
    try:
        p = str(path)
    except Exception:
        p = str(path)
    # Ignore the shadowing copy under tests/researcharr; the active tests
    # for the webui shim live in tests/researcharr/test_webui_pkg_shim.py
    if p.endswith("tests/researcharr/test_webui_shim.py"):
        return True
    return False


def pytest_runtest_teardown(item, nextitem):
    # Write a post-test snapshot of logger/Prometheus state
    try:
        import json as _json
        import logging as _logging
        import os as _os

        from prometheus_client import core as _core

        _out = "/tmp/researcharr-bisect/logsnap"
        try:
            _os.makedirs(_out, exist_ok=True)
        except Exception:
            pass

        def _take():
            mgr = _logging.root.manager
            d = {}
            try:
                items = list(mgr.loggerDict.items())
            except Exception:
                items = []
            for name, logger in items[:200]:
                try:
                    d[name] = {
                        "type": type(logger).__name__,
                        "handlers": [type(h).__name__ for h in getattr(logger, "handlers", [])],
                        "level": getattr(logger, "level", None),
                        "propagate": getattr(logger, "propagate", None),
                    }
                except Exception as e:
                    d[name] = {"error": str(e)}
            prom = []
            try:
                reg = _core.REGISTRY
                if hasattr(reg, "_collector_to_names"):
                    prom = [type(c).__name__ for c in reg._collector_to_names.keys()]
                elif hasattr(reg, "collectors"):
                    prom = [type(c).__name__ for c in reg.collectors]
                else:
                    prom = [repr(reg)]
            except Exception as e:
                prom = [f"ERR:{e}"]
            return {"logger_sample": dict(list(d.items())[:200]), "prometheus": prom}

        try:
            safe = item.nodeid.replace("::", "__").replace("/", "_")
            p = _os.path.join(_out, f"post_{safe}.json")
            with open(p, "w") as _f:
                _f.write(_json.dumps(_take(), indent=2, default=str))
        except Exception:
            pass
    except Exception:
        pass


@_pytest.fixture(autouse=True)
def _snapshot_and_restore_small_global_state():
    """Autouse fixture to snapshot and restore a small set of global
    registries/attrs that tests commonly mutate and which cause cascading
    flakes when left mutated.

    This is intentionally narrow: it snapshots/restores:
    - `prometheus_client.core.REGISTRY` (CollectorRegistry)
    - `__all__` on a small set of `researcharr` submodules (backups,
      researcharr top-level) if present

    Keep this as a short-term safety-net while we continue surgical
    fixes for polluter tests.
    """
    # Snapshot
    prom_snapshot = None
    all_snapshot = {}
    # Prefer an early snapshot captured at conftest import time so we can
    # restore module objects that may have been replaced during collection.
    try:
        module_snapshot = dict(_EARLY_ORIGINAL_MODULES) if _EARLY_ORIGINAL_MODULES else {}
    except Exception:
        module_snapshot = {}
    try:
        from prometheus_client import core as _prom_core

        try:
            prom_snapshot = getattr(_prom_core, "REGISTRY", None)
        except Exception:
            prom_snapshot = None
    except Exception:
        _prom_core = None

    try:
        import importlib

        mods = ["researcharr", "researcharr.backups"]
        for m in mods:
            try:
                # Snapshot the module object (may be None) so we can restore exact
                # mappings in sys.modules after the test. Some tests replace the
                # module object (e.g. inject a top-level shim) which breaks
                # assumptions in later tests unless we restore the original
                # module object.
                module_snapshot[m] = sys.modules.get(m)
                mod = importlib.import_module(m)
                if hasattr(mod, "__all__"):
                    all_snapshot[m] = list(getattr(mod, "__all__", None))
            except Exception:
                # ignore import errors; fixture is best-effort
                pass
    except Exception:
        pass

    yield

    # Restore
    try:
        if _prom_core is not None and prom_snapshot is not None:
            try:
                _prom_core.REGISTRY = prom_snapshot
            except Exception:
                pass
    except Exception:
        pass

    try:
        import importlib

        # First, restore module objects in sys.modules to their original
        # identities. This ensures that package-qualified names point back at
        # the original module object if a test replaced them.
        for m, orig in module_snapshot.items():
            try:
                if orig is None:
                    # If it didn't exist originally, remove any test-added module
                    sys.modules.pop(m, None)
                else:
                    sys.modules[m] = orig
                    # If this is a submodule of the package, also restore the
                    # attribute on the package object so attribute access like
                    # `researcharr.backups` resolves to the original module.
                    if m.startswith("researcharr."):
                        try:
                            pkg = importlib.import_module("researcharr")
                            attr = m.split(".", 1)[1]
                            setattr(pkg, attr, orig)
                        except Exception:
                            pass
            except Exception:
                pass

        # Then restore __all__ values for modules we snapped earlier.
        for m, val in all_snapshot.items():
            try:
                mod = importlib.import_module(m)
                # restore __all__ (if it existed originally)
                if val is None:
                    try:
                        delattr(mod, "__all__")
                    except Exception:
                        pass
                else:
                    try:
                        mod.__all__ = list(val)
                    except Exception:
                        pass
            except Exception:
                pass
        # Also ensure we restore any early-captured __all__ values for modules
        # that had a stable export list at conftest-import time.
        try:
            for m, v in _EARLY_ORIGINAL_ALLS.items():
                try:
                    if v is None:
                        # remove __all__ if early snapshot had none
                        mod = importlib.import_module(m)
                        try:
                            delattr(mod, "__all__")
                        except Exception:
                            pass
                    else:
                        mod = importlib.import_module(m)
                        try:
                            mod.__all__ = list(v)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass
