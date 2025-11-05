# Compatibility shim so environments that try to import
# `researcharr.tests` (like the pre-commit pytest wrapper) succeed.
#
# This module attempts to re-export the top-level `tests` package as
# `researcharr.tests`. If that fails, it creates an empty namespace
# module so import attempts do not raise during pre-commit collection.

import importlib
import sys
import types

try:
    _mod = importlib.import_module("tests")
    sys.modules["researcharr.tests"] = _mod
except Exception:
    pkg = types.ModuleType("researcharr.tests")
    pkg.__path__ = []
    sys.modules["researcharr.tests"] = pkg
