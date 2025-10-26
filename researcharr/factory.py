"""Load top-level `factory.py` and register it as `researcharr.factory`.

This shim loads the repo's top-level `factory.py` by path and registers it
under the package name `researcharr.factory`. This keeps the repository's
flattened layout compatible with tests and importers that expect a package
namespace.
"""

import importlib.util
import os
import sys

_mod = None
# Look for a top-level factory.py file (project root) first, then a
# relative candidate. When we load the top-level module we purposely
# load it with the top-level name 'factory' so that Flask's package
# based template/resource lookup resolves relative to the file's
# directory. After loading we register the module under both the
# real top-level name and the package name `researcharr.factory` so
# imports using either form work the same.
cwd_candidate = os.path.join(os.getcwd(), "factory.py")
rel_candidate = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "factory.py")
)
for c in (cwd_candidate, rel_candidate):
    if os.path.isfile(c):
        # Load the module from file using the top-level name so
        # Flask/PackageLoader will locate templates next to that file.
        spec = importlib.util.spec_from_file_location("factory", c)
        if spec and spec.loader:
            _mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_mod)  # type: ignore[arg-type]
            # Ensure the module reports a top-level name/package so
            # Flask's template lookup uses the module file path.
            try:
                _mod.__name__ = "factory"
                _mod.__package__ = None
            except Exception:
                pass
            # Register under both names so `import researcharr.factory`
            # and `import factory` both resolve to the same module.
            sys.modules["factory"] = _mod
            sys.modules[__name__] = _mod
            break

if _mod is None:
    import importlib as _importlib

    _mod = _importlib.import_module("factory")
    sys.modules[__name__] = _mod
