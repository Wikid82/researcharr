#!/usr/bin/env python3
"""Compatibility shim for `scripts/researcharr.py`.

The canonical implementation remains at the repository root (`researcharr.py`) and
the `researcharr/` package. This shim ensures any callers that execute
`scripts/researcharr.py` still import the canonical module.
"""

from importlib import import_module


def _bootstrap():
    # Import the canonical top-level module so attributes are available.
    try:
        import_module("researcharr")
    except Exception:
        # If importing the top-level module fails, surface a clear error.
        raise


if __name__ == "__main__":
    _bootstrap()
