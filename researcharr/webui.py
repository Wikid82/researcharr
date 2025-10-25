"""Load the top-level `webui.py` module and register it as
`researcharr.webui` so tests and callers get the real module object.
"""
import importlib.util
import os
import sys

_mod = None
cwd_candidate = os.path.join(os.getcwd(), 'webui.py')
rel_candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'webui.py'))
for c in (cwd_candidate, rel_candidate):
    if os.path.isfile(c):
        spec = importlib.util.spec_from_file_location('researcharr.webui', c)
        if spec and spec.loader:
            _mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_mod)  # type: ignore[arg-type]
            sys.modules[__name__] = _mod
            break

if _mod is None:
    # Fallback: import by name (should rarely be needed in tests)
    import importlib as _importlib

    _mod = _importlib.import_module('webui')
    sys.modules[__name__] = _mod

