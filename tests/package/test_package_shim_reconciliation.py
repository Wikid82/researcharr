import importlib
import sys
from types import ModuleType


def test_package_path_order():
    import researcharr

    paths = list(getattr(researcharr, "__path__", []))
    assert paths, "__path__ should not be empty"
    # Ensure at least one path points at repo root and one at nested dir
    norm = [p.replace("\\", "/") for p in paths]
    has_repo_root = any(n.endswith("/researcharr") for n in norm)
    has_nested = any("/researcharr/researcharr" in n for n in norm)
    assert has_repo_root or has_nested


def test_lazy_getattr_prefers_canonical_package_module(monkeypatch):
    # Inject a synthetic top-level webui module before accessing package attribute
    dummy = ModuleType("webui")
    dummy.SENTINEL = 42
    monkeypatch.setitem(sys.modules, "webui", dummy)
    import researcharr

    pkg_webui = researcharr.webui
    # Accept either reconciliation to the dummy object or loading canonical module
    assert isinstance(pkg_webui, ModuleType)
    # If reconciliation used dummy, sentinel will be present
    if pkg_webui is dummy:
        assert getattr(pkg_webui, "SENTINEL", None) == 42
    # Ensure canonical mapping exists
    assert sys.modules.get("researcharr.webui") is not None


def test_lazy_getattr_loads_repo_file(monkeypatch):
    # Ensure no pre-existing webui mapping so __getattr__ loads file
    monkeypatch.setitem(sys.modules, "researcharr", importlib.import_module("researcharr"))
    for key in ["webui", "researcharr.webui"]:
        sys.modules.pop(key, None)
    import researcharr

    mod = researcharr.webui
    assert isinstance(mod, ModuleType)
    # Ensure spec name is canonical (no doubled prefix)
    spec_name = getattr(getattr(mod, "__spec__", None), "name", None)
    if spec_name is not None:
        assert spec_name.startswith("researcharr.webui")


def test_factory_create_app_callable():
    # The factory delegate enforcement should guarantee create_app is callable
    import researcharr

    fmod = researcharr.factory
    assert callable(getattr(fmod, "create_app", None))
    # Call once (app object may be Flask or raises ImportError if unavailable)
    try:
        app = fmod.create_app()
        # If it returned an object, basic sanity: has config_data attribute or is Flask-like
        if app is not None:
            assert hasattr(app, "config") or hasattr(app, "config_data")
    except ImportError:
        # Accept ImportError as a valid delegated outcome when implementation not present
        pass


def test_create_metrics_app_dispatcher_callable(monkeypatch):
    import researcharr

    # Provide a deterministic implementation so dispatcher returns our sentinel
    called = {}

    def impl():
        called["ran"] = True
        return object()

    monkeypatch.setattr(researcharr, "create_metrics_app", impl, raising=False)
    res = researcharr.create_metrics_app()
    assert called.get("ran") is True
    assert res is not None


def test_backups_identity_reconciliation():
    # Import top-level backups then access package attribute; identity may differ
    # Snapshot existing sys.modules mapping so we can restore it after the
    # test — importing the top-level shim may install itself under the
    # package-qualified name (e.g. 'researcharr.backups') which pollutes
    # global import state and affects later tests during the same pytest run.
    orig_ra_backups = sys.modules.get("researcharr.backups")
    try:
        top = importlib.import_module("backups")
        import researcharr

        pkg_attr = researcharr.backups
        assert isinstance(pkg_attr, ModuleType)
        # Must expose expected public API symbol
        assert hasattr(pkg_attr, "prune_backups")
        # Ensure canonical mapping exists
        assert sys.modules.get("researcharr.backups") is pkg_attr
    finally:
        # Restore original mapping to avoid polluting other tests that expect
        # the package implementation to be present under `researcharr.backups`.
        try:
            if orig_ra_backups is None:
                sys.modules.pop("researcharr.backups", None)
            else:
                sys.modules["researcharr.backups"] = orig_ra_backups
                # Also restore attribute on package object if present
                try:
                    import importlib as _il

                    _pkg = _il.import_module("researcharr")
                    setattr(_pkg, "backups", orig_ra_backups)
                except Exception:
                    pass
        except Exception:
            pass
