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
cwd_candidate = os.path.join(os.getcwd(), "factory.py")
rel_candidate = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "factory.py")
)
for c in (cwd_candidate, rel_candidate):
    if os.path.isfile(c):
        spec = importlib.util.spec_from_file_location("researcharr.factory", c)
        if spec and spec.loader:
            _mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_mod)  # type: ignore[arg-type]
            sys.modules[__name__] = _mod
            break

if _mod is None:
    import importlib as _importlib

    _mod = _importlib.import_module("factory")
    sys.modules[__name__] = _mod
