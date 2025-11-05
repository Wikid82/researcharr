"""Lightweight stub of the third-party `schedule` module used in tests.

This minimal implementation provides the names tests patch (`every`,
`run_pending`) so imports succeed when the real package is not installed
in the environment. The functions do nothing by default; tests typically
mock them.
"""
from __future__ import annotations

from typing import Any, Callable


class _Every:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._args = args

    def do(self, fn: Callable[..., Any]) -> None:
        # No-op: tests generally patch this method.
        return None


def every(*args: Any, **kwargs: Any) -> _Every:
    return _Every(*args, **kwargs)


def run_pending() -> None:
    # No-op placeholder
    return None


def cancel(job: Any) -> None:
    # No-op placeholder
    return None
