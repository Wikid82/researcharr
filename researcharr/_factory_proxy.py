"""Lightweight helper module to install short-name module proxies.

This mirrors the behavior previously in ``researcharr.__init__`` but
lives in a small dedicated module so the package init stays easy to
analyze by static tools. It is defensive and best-effort: failures
during proxy creation are swallowed to preserve import-time stability.
"""
from __future__ import annotations

import importlib.util as importlib_util
import os
import sys
from types import ModuleType


class _ModuleProxy(ModuleType):
    def __init__(self, pkg_name: str, short_name: str, repo_fp: str | None = None):
        super().__init__(pkg_name)
        object.__setattr__(self, "_pkg_name", pkg_name)
        object.__setattr__(self, "_short_name", short_name)
        object.__setattr__(self, "_repo_fp", repo_fp)
        object.__setattr__(self, "_target", None)

    def _ensure_target(self):
        tgt = object.__getattribute__(self, "_target")
        if tgt is not None:
            return tgt
        try:
            _sys_local = sys
            pkg = _sys_local.modules.get(object.__getattribute__(self, "_pkg_name"))
            if pkg is not None and pkg is not self:
                object.__setattr__(self, "_target", pkg)
                return pkg
            short = _sys_local.modules.get(object.__getattribute__(self, "_short_name"))
            if short is not None and short is not self:
                object.__setattr__(self, "_target", short)
                return short
            repo_fp = object.__getattribute__(self, "_repo_fp")
            if repo_fp:
                try:
                    _spec = importlib_util.spec_from_file_location(
                        object.__getattribute__(self, "_short_name"), repo_fp
                    )
                    if _spec and _spec.loader:
                        _m = importlib_util.module_from_spec(_spec)
                        _spec.loader.exec_module(_m)  # type: ignore[arg-type]
                        object.__setattr__(self, "_target", _m)
                        return _m
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def __getattr__(self, name: str):
        if name in ("_pkg_name", "_short_name", "_repo_fp", "_target"):
            return object.__getattribute__(self, name)
        tgt = self._ensure_target()
        if tgt is not None:
            return getattr(tgt, name)
        raise AttributeError(f"module {object.__getattribute__(self, '_pkg_name')} has no attribute {name}")

    def __setattr__(self, name: str, value):
        if name in ("_pkg_name", "_short_name", "_repo_fp", "_target"):
            return object.__setattr__(self, name, value)
        tgt = self._ensure_target()
        if tgt is not None:
            setattr(tgt, name, value)
            return
        return object.__setattr__(self, name, value)

    def __delattr__(self, name: str):
        if name in ("_pkg_name", "_short_name", "_repo_fp", "_target"):
            return object.__delattr__(self, name)
        tgt = self._ensure_target()
        if tgt is not None:
            try:
                delattr(tgt, name)
                return
            except AttributeError:
                pass
        return object.__delattr__(self, name)

    def __dir__(self):
        tgt = self._ensure_target()
        names = set(dir(type(self)))
        if tgt is not None:
            names.update(dir(tgt))
        names.update(self.__dict__.keys())
        return sorted(names)


def create_proxies(repo_root: str | None = None) -> None:
    """Create short-name proxies for a small set of modules.

    This is intentionally conservative: any exception during creation is
    swallowed so package import remains robust.
    """
    try:
        if repo_root is None:
            here = os.path.abspath(os.path.dirname(__file__))
            repo_root = os.path.abspath(os.path.join(here, os.pardir))

        _shorts = {
            "factory": os.path.join(repo_root, "factory.py"),
            "backups": os.path.join(repo_root, "backups.py"),
            "webui": os.path.join(repo_root, "webui.py"),
        }
        for _short, _fp in _shorts.items():
            _pkg_name = f"researcharr.{_short}"
            existing = sys.modules.get(_pkg_name) or sys.modules.get(_short)
            if isinstance(existing, _ModuleProxy):
                continue
            _proxy = _ModuleProxy(_pkg_name, _short, _fp if os.path.isfile(_fp) else None)
            try:
                _spec = None
                if os.path.isfile(_fp):
                    try:
                        _spec = importlib_util.spec_from_file_location(_pkg_name, _fp)
                    except Exception:
                        _spec = None
                if _spec is None:
                    _real_pkg = sys.modules.get(_pkg_name)
                    _real_short = sys.modules.get(_short)
                    if getattr(_real_pkg, "__spec__", None) is not None:
                        _spec = getattr(_real_pkg, "__spec__")
                    elif getattr(_real_short, "__spec__", None) is not None:
                        _spec = getattr(_real_short, "__spec__")
                if _spec is not None:
                    try:
                        object.__setattr__(_proxy, "__spec__", _spec)
                    except Exception:
                        pass
            except Exception:
                pass

            _real_pkg = sys.modules.get(_pkg_name)
            _real_short = sys.modules.get(_short)
            if _real_pkg is not None and _real_pkg is not _proxy:
                object.__setattr__(_proxy, "_target", _real_pkg)
            elif _real_short is not None and _real_short is not _proxy:
                object.__setattr__(_proxy, "_target", _real_short)

            sys.modules[_pkg_name] = _proxy
            sys.modules.setdefault(_short, _proxy)
            try:
                pkg_mod = sys.modules.get("researcharr")
                if pkg_mod is not None:
                    pkg_mod.__dict__.setdefault(_short, _proxy)
            except Exception:
                pass
    except Exception:
        # Best-effort only
        pass


def install_create_app_helpers(repo_root: str | None = None) -> None:
    """Install runtime create_app helpers onto the package module.

    This creates a best-effort `_runtime_create_app` function and a
    stable `_create_app_delegate` instance on the `researcharr` package
    module and on `researcharr.factory` when present. It mirrors the
    earlier behavior in `__init__.py` but lives here to keep the
    package init small.
    """
    try:
        if repo_root is None:
            here = os.path.abspath(os.path.dirname(__file__))
            repo_root = os.path.abspath(os.path.join(here, os.pardir))

        pkg_mod = sys.modules.get("researcharr")

        def _runtime_create_app(*a, **kw):
            try:
                import importlib

                # 1) prefer top-level factory
                try:
                    top = importlib.import_module("factory")
                    f = getattr(top, "create_app", None)
                    if callable(f):
                        return f(*a, **kw)
                except Exception:
                    pass

                # 2) prefer cached repo-level impl
                try:
                    cached = sys.modules.get("researcharr._factory_impl_loaded")
                    if cached is not None:
                        f2 = getattr(cached, "create_app", None)
                        if callable(f2):
                            return f2(*a, **kw)
                except Exception:
                    pass

                # 3) try importing the package submodule
                try:
                    mod = importlib.import_module("researcharr.factory")
                    f3 = getattr(mod, "create_app", None)
                    if callable(f3):
                        return f3(*a, **kw)
                except Exception:
                    pass

                # 4) transiently load repo-level file
                try:
                    _fp = os.path.join(repo_root, "factory.py")
                    if os.path.isfile(_fp):
                        spec = importlib_util.spec_from_file_location(
                            "researcharr._factory_impl_early", _fp
                        )
                        if spec and spec.loader:
                            mod = importlib_util.module_from_spec(spec)
                            spec.loader.exec_module(mod)  # type: ignore[arg-type]
                            f4 = getattr(mod, "create_app", None)
                            if callable(f4):
                                sys.modules.setdefault("researcharr._factory_impl_loaded", mod)
                                return f4(*a, **kw)
                except Exception:
                    pass
            except Exception:
                pass
            raise ImportError("create_app implementation not available")

        class _CreateAppDelegate:
            def __init__(self):
                self._cached = None

            def __call__(self, *a, **kw):
                try:
                    import importlib

                    try:
                        top = importlib.import_module("factory")
                        f = getattr(top, "create_app", None)
                        if callable(f) and f is not self:
                            return f(*a, **kw)
                    except Exception:
                        pass

                    try:
                        cached = sys.modules.get("researcharr._factory_impl_loaded")
                        if cached is not None:
                            f2 = getattr(cached, "create_app", None)
                            if callable(f2) and f2 is not self:
                                return f2(*a, **kw)
                    except Exception:
                        pass

                    try:
                        mod = importlib.import_module("researcharr.factory")
                        f3 = getattr(mod, "create_app", None)
                        if callable(f3) and f3 is not self:
                            return f3(*a, **kw)
                    except Exception:
                        pass

                    try:
                        _fp = os.path.join(repo_root, "factory.py")
                        if os.path.isfile(_fp):
                            spec = importlib_util.spec_from_file_location(
                                "researcharr._factory_impl_call_delegate", _fp
                            )
                            if spec and spec.loader:
                                mod = importlib_util.module_from_spec(spec)
                                spec.loader.exec_module(mod)  # type: ignore[arg-type]
                                f4 = getattr(mod, "create_app", None)
                                if callable(f4) and f4 is not self:
                                    return f4(*a, **kw)
                    except Exception:
                        pass

                except Exception:
                    pass
                raise ImportError("create_app implementation not available")

            def __repr__(self):
                return "<CreateAppDelegate for researcharr.factory.create_app>"

        delegate = _CreateAppDelegate()
        # Attach markers
        try:
            setattr(delegate, "_is_stable_delegate", True)
        except Exception:
            pass
        try:
            setattr(delegate, "_is_delegate", True)
        except Exception:
            pass

        # Install into package module namespace when available
        try:
            if pkg_mod is not None:
                pkg_mod.__dict__.setdefault("_runtime_create_app", _runtime_create_app)
                pkg_mod.__dict__.setdefault("_create_app_delegate", delegate)
                # Ensure researcharr.factory also gets the delegate when present
                try:
                    pf = sys.modules.get("researcharr.factory")
                    if pf is not None and getattr(pf, "create_app", None) is None:
                        try:
                            setattr(pf, "create_app", _runtime_create_app)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass
