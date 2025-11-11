"""Simple in-process TTL cache and decorator for researcharr.

Provides lightweight caching for high-read repository methods. Designed
for single-process usage; can be swapped for Redis later by replacing
backend functions.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

_lock = threading.RLock()
_store: dict[str, tuple[float, Any]] = {}
_metrics = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

# Optional Prometheus counters (lazy; only if env enabled and library present)
_PROM_COUNTERS = {}


def _prometheus_enabled() -> bool:
    return os.getenv("RESEARCHARR_PROMETHEUS_CACHE", "false").lower() in ("1", "true", "yes")


def _ensure_prometheus():
    if not _prometheus_enabled():
        return
    if _PROM_COUNTERS:
        return
    try:
        from prometheus_client import Counter  # type: ignore

        _PROM_COUNTERS["hits"] = Counter(
            "cache_hits_total", "Total cache hits", ["component"], registry=None
        ).labels(component="cache")
        _PROM_COUNTERS["misses"] = Counter(
            "cache_misses_total", "Total cache misses", ["component"], registry=None
        ).labels(component="cache")
        _PROM_COUNTERS["sets"] = Counter(
            "cache_sets_total", "Total cache sets", ["component"], registry=None
        ).labels(component="cache")
        _PROM_COUNTERS["evictions"] = Counter(
            "cache_evictions_total", "Total cache evictions", ["component"], registry=None
        ).labels(component="cache")
    except Exception:  # nosec B110 -- intentional broad except for resilience
        # Library missing or counter creation failed; leave counters disabled
        pass


def cache_enabled() -> bool:
    val = os.getenv("RESEARCHARR_CACHE_DISABLED", "false").lower()
    return val not in ("1", "true", "yes")


def make_key(parts: tuple[Any, ...]) -> str:
    return ":".join(str(p) for p in parts)


def get(key: str) -> Any:
    if not cache_enabled():
        return None
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            _metrics["misses"] += 1
            _ensure_prometheus()
            c = _PROM_COUNTERS.get("misses")
            try:
                c and c.inc()
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            return None
        expires, value = entry
        if expires < now:
            _metrics["evictions"] += 1
            _store.pop(key, None)
            _metrics["misses"] += 1
            _ensure_prometheus()
            try:
                c1 = _PROM_COUNTERS.get("evictions")
                c2 = _PROM_COUNTERS.get("misses")
                if c1:
                    c1.inc()
                if c2:
                    c2.inc()
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            return None
        _metrics["hits"] += 1
        _ensure_prometheus()
        c = _PROM_COUNTERS.get("hits")
        try:
            c and c.inc()
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
        return value


def set(key: str, value: Any, ttl: int) -> None:
    if not cache_enabled():
        return
    expires = time.time() + ttl
    with _lock:
        _store[key] = (expires, value)
        _metrics["sets"] += 1
        _ensure_prometheus()
        c = _PROM_COUNTERS.get("sets")
        try:
            c and c.inc()
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass


def invalidate(prefix: str) -> None:
    """Invalidate all keys matching prefix (exact or startswith)."""
    with _lock:
        for k in list(_store.keys()):
            if k == prefix or k.startswith(prefix):
                _store.pop(k, None)
                _metrics["evictions"] += 1
                _ensure_prometheus()
                c = _PROM_COUNTERS.get("evictions")
                try:
                    c and c.inc()
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass


def clear_all() -> None:
    with _lock:
        _store.clear()
        _metrics["evictions"] += 1
        _ensure_prometheus()
        c = _PROM_COUNTERS.get("evictions")
        try:
            c and c.inc()
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass


def metrics() -> dict[str, int]:
    return dict(_metrics)


def cached(ttl: int, key_builder: Callable[..., tuple[Any, ...]] | None = None):
    """Decorator for caching pure-ish function results.

    Args:
        ttl: Time-to-live in seconds.
        key_builder: Optional function that returns tuple of key parts.
    """

    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not cache_enabled():
                return fn(*args, **kwargs)
            parts = (fn.__module__, fn.__name__)
            if key_builder:
                parts += tuple(key_builder(*args, **kwargs))
            else:
                parts += args
                if kwargs:
                    parts += tuple(sorted(kwargs.items()))
            key = make_key(parts)
            value = get(key)
            if value is not None:
                return value
            value = fn(*args, **kwargs)
            set(key, value, ttl)
            return value

        return wrapper

    return decorator


__all__ = [
    "cache_enabled",
    "make_key",
    "get",
    "set",
    "invalidate",
    "clear_all",
    "metrics",
    "cached",
    "_prometheus_enabled",
    "_ensure_prometheus",
]
