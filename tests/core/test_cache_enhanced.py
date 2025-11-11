"""Enhanced tests for researcharr.cache module."""

import sys
import time

import pytest

from researcharr import cache


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear cache between tests."""
    cache.clear_all()
    cache.reset_metrics()
    yield
    cache.clear_all()


def test_cache_enabled_default(monkeypatch):
    monkeypatch.delenv("RESEARCHARR_CACHE_DISABLED", raising=False)
    assert cache.cache_enabled() is True


def test_cache_disabled_via_env(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_CACHE_DISABLED", "true")
    assert cache.cache_enabled() is False
    monkeypatch.setenv("RESEARCHARR_CACHE_DISABLED", "1")
    assert cache.cache_enabled() is False


def test_prometheus_enabled(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "true")
    assert cache._prometheus_enabled() is True
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "false")
    assert cache._prometheus_enabled() is False


def test_make_key():
    key = cache.make_key(("a", "b", 123))
    assert key == "a:b:123"


def test_get_miss():
    result = cache.get("nonexistent")
    assert result is None
    assert cache.metrics()["misses"] >= 1


def test_set_and_get():
    cache.set("key1", "value1", ttl=60)
    result = cache.get("key1")
    assert result == "value1"
    assert cache.metrics()["hits"] >= 1
    assert cache.metrics()["sets"] >= 1


def test_get_expired_entry():
    cache.set("key_expire", "val", ttl=1)
    time.sleep(1.1)
    result = cache.get("key_expire")
    assert result is None
    assert cache.metrics()["evictions"] >= 1


def test_invalidate_prefix():
    cache.set("user:123:profile", "data1", ttl=60)
    cache.set("user:123:settings", "data2", ttl=60)
    cache.set("user:456:profile", "data3", ttl=60)
    cache.invalidate("user:123")
    assert cache.get("user:123:profile") is None
    assert cache.get("user:123:settings") is None
    assert cache.get("user:456:profile") == "data3"


def test_invalidate_exact_match():
    cache.set("exact_key", "value", ttl=60)
    cache.invalidate("exact_key")
    assert cache.get("exact_key") is None


def test_clear_all():
    cache.set("key1", "val1", ttl=60)
    cache.set("key2", "val2", ttl=60)
    cache.clear_all()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cached_decorator():
    call_count = 0

    @cache.cached(ttl=60)
    def expensive_func(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive_func(5)
    assert result1 == 10
    assert call_count == 1

    result2 = expensive_func(5)
    assert result2 == 10
    assert call_count == 1  # Cached, not called again


def test_cached_decorator_with_kwargs():
    call_count = 0

    @cache.cached(ttl=60)
    def func_with_kwargs(a, b=None):
        nonlocal call_count
        call_count += 1
        return f"{a}-{b}"

    result1 = func_with_kwargs(1, b=2)
    assert result1 == "1-2"
    assert call_count == 1

    result2 = func_with_kwargs(1, b=2)
    assert result2 == "1-2"
    assert call_count == 1  # Cached


def test_cached_decorator_custom_key_builder():
    call_count = 0

    def key_builder(obj):
        return (obj["id"],)

    @cache.cached(ttl=60, key_builder=key_builder)
    def fetch_user(obj):
        nonlocal call_count
        call_count += 1
        return f"User-{obj['id']}"

    result1 = fetch_user({"id": 123, "name": "Alice"})
    assert result1 == "User-123"
    assert call_count == 1

    result2 = fetch_user({"id": 123, "name": "Bob"})
    assert result2 == "User-123"
    assert call_count == 1  # Same ID, cached


def test_operations_disabled(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_CACHE_DISABLED", "1")
    cache.set("disabled_key", "value", ttl=60)
    assert cache.get("disabled_key") is None


def test_cached_decorator_disabled(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_CACHE_DISABLED", "1")
    call_count = 0

    @cache.cached(ttl=60)
    def func(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    func(5)
    func(5)
    assert call_count == 2  # Not cached when disabled


def test_ensure_prometheus_no_library(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "true")
    # Clear any existing counters
    cache._PROM_COUNTERS.clear()

    # Simulate prometheus_client not being installed by patching sys.modules
    original_modules = sys.modules.copy()
    if "prometheus_client" in sys.modules:
        del sys.modules["prometheus_client"]

    try:
        cache._ensure_prometheus()
        # Should not crash even if library missing
    finally:
        # Restore modules
        sys.modules.update(original_modules)
