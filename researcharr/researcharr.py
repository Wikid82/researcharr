"""Wrapper so `researcharr.researcharr` points at the top-level `researcharr.py` module.

This file loads the top-level ``researcharr.py`` by file path and inserts the
loaded module into ``sys.modules`` under the package name so imports and
``importlib.reload`` behave the same as when the project is installed.
"""

import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional

# Load the top-level `researcharr.py` module by file path to avoid importing
# this package (which would otherwise shadow the module name).
_mod: Optional[ModuleType] = None
# Exposed name for the loaded module (or None when not found).
module: Optional[ModuleType] = None

# Candidate locations for the top-level module. We prefer the current working
# directory (CI/test runners commonly run from the repo root) and then fall
# back to paths relative to this file.
cwd_candidate = os.path.join(os.getcwd(), "researcharr.py")
rel_candidate = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "researcharr.py")
)
rel_candidate2 = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "researcharr.py")
)
TOP_LEVEL = None
for c in (cwd_candidate, rel_candidate, rel_candidate2):
    if os.path.isfile(c):
        TOP_LEVEL = c
        break

if TOP_LEVEL:
    # Use the package module name so importlib.reload and sys.modules behave
    # as callers expect (i.e. the module is known as 'researcharr.researcharr').
    spec = importlib.util.spec_from_file_location("researcharr.researcharr", TOP_LEVEL)
    if spec and spec.loader:
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)  # type: ignore[arg-type]

if _mod:
    # Replace this shim module in sys.modules with the loaded top-level
    # module so callers receive the real module object (functions will use
    # the correct globals and monkeypatching will work as expected).

    sys.modules[__name__] = _mod

    # Also expose the loaded module on the name 'module' for debugging
    module = _mod
else:
    module = None
