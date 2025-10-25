"""Load the top-level `run.py` and expose it as `researcharr.run`.

The shim loads the repository's top-level `run.py` by path and registers
it under the package `researcharr.run`. This keeps imports consistent for
the tests and runtime code.
"""

import importlib.util
import os
import sys

_mod = None
cwd_candidate = os.path.join(os.getcwd(), "run.py")
rel_candidate = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "run.py")
)
for c in (cwd_candidate, rel_candidate):
    if os.path.isfile(c):
        spec = importlib.util.spec_from_file_location("researcharr.run", c)
        if spec and spec.loader:
            _mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_mod)  # type: ignore[arg-type]
            sys.modules[__name__] = _mod
            break

if _mod is None:
    import importlib as _importlib

    _mod = _importlib.import_module("run")
    sys.modules[__name__] = _mod
