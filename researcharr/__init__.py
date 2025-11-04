"""Fallback package shim for the directory-import path.

When the import system resolves the name `researcharr` to the nested
directory (`researcharr/researcharr`) this module will be executed as the
package `researcharr`. Provide the minimal behavior the test-suite expects:
attach the implementation module as the `researcharr` attribute on the
package object so `from researcharr import researcharr` works regardless of
which filesystem entry was selected by the importer.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from types import ModuleType


def _load_impl() -> ModuleType | None:
    """Load an implementation module from several candidate locations.

    Order of attempts:
    1. importlib.import_module("researcharr.researcharr") if it looks like a
       full implementation (has required symbols).
    2. package-local file (researcharr/researcharr.py).
    3. repository root top-level file (../researcharr.py).

    We check for a small set of required public names to decide whether a
    loaded module is a complete implementation or just a placeholder.
    """
    required = (
        "create_metrics_app",
        "setup_logger",
        "init_db",
        "load_config",
        "check_radarr_connection",
        "check_sonarr_connection",
        "has_valid_url_and_key",
    )

    def _looks_complete(m: ModuleType | None) -> bool:
        if m is None:
            return False
        return all(hasattr(m, name) for name in required)

    # 1) Try normal import first
    try:
        mod = importlib.import_module("researcharr.researcharr")
        if _looks_complete(mod):
            return mod
    except Exception:
        mod = None

    # helper to load from a file path
    def _load_from_path(path: str) -> ModuleType | None:
        try:
            name = "researcharr.researcharr"
            spec = importlib.util.spec_from_file_location(name, path)
            if spec and spec.loader:
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)  # type: ignore[arg-type]
                # Ensure __file__ is set so consumers can inspect it
                try:
                    if not getattr(m, "__file__", None):
                        setattr(m, "__file__", os.path.abspath(path))
                except Exception:
                    pass
                return m
        except Exception:
            return None
        return None

    here = os.path.abspath(os.path.dirname(__file__))

    # 2) package-local file
    pkg_local = os.path.join(here, "researcharr.py")
    if os.path.isfile(pkg_local):
        m = _load_from_path(pkg_local)
        if _looks_complete(m):
            return m

    # 3) repo-root top-level file (one dir above the package)
    repo_level = os.path.abspath(os.path.join(here, os.pardir, "researcharr.py"))
    if os.path.isfile(repo_level):
        m = _load_from_path(repo_level)
        if _looks_complete(m):
            return m

    # If nothing looks fully complete, prefer any module we managed to import
    # earlier (mod) or the package-local one as a last resort.
    if mod is not None:
        return mod
    if os.path.isfile(pkg_local):
        return _load_from_path(pkg_local)
    return None


impl = _load_impl()
if impl is not None:
    # Register under the expected name and attach to the package namespace
    sys.modules["researcharr.researcharr"] = impl
    # Expose requests/yaml submodule names so import-style lookups (used by
    # monkeypatch.setattr with dotted strings) succeed when they attempt
    # to import 'researcharr.researcharr.requests' or '...yaml'.
    try:
        if getattr(impl, "requests", None) is not None:
            name = "researcharr.researcharr.requests"
            sys.modules.setdefault(name, getattr(impl, "requests"))
    except Exception:
        pass
    try:
        if getattr(impl, "yaml", None) is not None:
            name = "researcharr.researcharr.yaml"
            sys.modules.setdefault(name, getattr(impl, "yaml"))
    except Exception:
        pass
    try:
        globals()["researcharr"] = impl
    except Exception:
        pass

    # Expose the top-level `plugins` package as `researcharr.plugins` so imports
    # like `from researcharr.plugins.registry import PluginRegistry` resolve in
    # environments where the `plugins/` package lives at the repository root.
    try:
        import sys

        import plugins as _plugins_pkg  # type: ignore

        sys.modules.setdefault("researcharr.plugins", _plugins_pkg)
    except Exception:
        pass

# Additionally expose common top-level modules (factory, run, webui, backups,
# api) as submodules of the `researcharr` package when those modules exist at
# the repository root. This improves static analysis/editor resolution for
# imports like `from researcharr import factory` or `import researcharr.factory`.
_here = os.path.abspath(os.path.dirname(__file__))
_repo_root = os.path.abspath(os.path.join(_here, os.pardir))
for _mname in ("factory", "run", "webui", "backups", "api"):
    _path = os.path.join(_repo_root, f"{_mname}.py")
    if os.path.isfile(_path):
        try:
            spec = importlib.util.spec_from_file_location("researcharr." + _mname, _path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[arg-type]
                sys.modules.setdefault(f"researcharr.{_mname}", mod)
                try:
                    globals()[_mname] = mod
                except Exception:
                    pass
        except Exception:
            # Non-fatal; this is only for editor/static analysis friendliness
            # and should not prevent runtime.
            pass

# Import missing functions that tests expect to be available at package level
try:
    from .db import (  # type: ignore[attr-defined]; noqa: F401
        _conn as get_connection,
    )
    from .db import (  # type: ignore[attr-defined]; noqa: F401
        init_db as create_tables,
    )
    from .db import (  # type: ignore[attr-defined]; noqa: F401
        load_user as get_user_by_username,
    )
    from .db import (  # type: ignore[attr-defined]; noqa: F401
        save_user as create_user,
    )
    from .researcharr import DB_PATH  # noqa: F401
    from .researcharr import check_radarr_connection  # noqa: F401
    from .researcharr import check_sonarr_connection  # noqa: F401
    from .researcharr import create_metrics_app  # noqa: F401
    from .researcharr import has_valid_url_and_key  # noqa: F401
    from .researcharr import init_db  # noqa: F401
    from .researcharr import load_config  # noqa: F401
    from .researcharr import serve  # type: ignore[attr-defined]  # noqa: F401
    from .researcharr import (  # type: ignore[attr-defined]; noqa: F401
        setup_logger,
    )
except ImportError:
    # Functions may not be available in all contexts
    pass

# Add version information
__version__ = "0.1.0"
