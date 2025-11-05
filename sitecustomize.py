"""Project-local sitecustomize to ensure the nested `researcharr` package
is registered early during test runs.

Pytest imports this (from the CWD) before test collection. When both a
top-level ``researcharr.py`` file and a ``researcharr/`` package directory
exist in the repository root, import order can cause Python to bind the
module name to the top-level file, preventing subpackage imports like
``researcharr.core``. To avoid that, load the nested package ``__init__.py``
and register it under the name ``researcharr`` in sys.modules early.

This is intentionally conservative and best-effort: if loading fails we
don't raise so test collection can continue and produce normal import
errors that are easier to reason about.
"""

import importlib.util
import os
import sys

try:
    if "researcharr" not in sys.modules:
        repo_root = os.path.abspath(os.getcwd())
        nested_init = os.path.join(repo_root, "researcharr", "__init__.py")
        if os.path.isfile(nested_init):
            spec = importlib.util.spec_from_file_location("researcharr", nested_init)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # register before executing to break potential import cycles
                sys.modules.setdefault("researcharr", mod)
                try:
                    spec.loader.exec_module(mod)  # type: ignore[arg-type]
                except Exception:
                    # If execution fails, remove the partially-registered module
                    # so subsequent normal imports can surface meaningful errors.
                    try:
                        sys.modules.pop("researcharr", None)
                    except Exception:
                        pass
except Exception:
    # Never fail import/site initialization because of this helper.
    pass
