"""Compatibility layer for Python version differences.

Provides fallbacks and shims for features introduced in newer Python versions
to ensure the application runs on all supported versions (3.10+).
"""

import sys
from datetime import datetime, timezone

# Python 3.11+ has datetime.UTC; provide fallback for 3.10
if sys.version_info >= (3, 11):  # noqa: UP036
    from datetime import UTC  # type: ignore[attr-defined]
else:
    # Python 3.10 compatibility: datetime.UTC was added in 3.11
    UTC = timezone.utc  # noqa: UP017

# Werkzeug removed __version__ attribute in newer versions
# Provide a shim for code that expects it
try:
    import werkzeug

    if not hasattr(werkzeug, "__version__"):
        # Set a placeholder version for compatibility
        try:
            from importlib.metadata import version

            werkzeug.__version__ = version("werkzeug")  # type: ignore[attr-defined]
        except Exception:
            werkzeug.__version__ = "3.x"  # type: ignore[attr-defined]
except ImportError:
    pass

__all__ = ["UTC", "datetime", "timezone"]
