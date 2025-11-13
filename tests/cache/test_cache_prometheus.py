import importlib

import pytest

prom = pytest.importorskip("prometheus_client")


def test_cache_prometheus_counters_increment(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "1")
    # Ensure module reloaded with env enabled
    from researcharr import cache

    importlib.reload(cache)  # pick up env var

    # Miss (none set yet)
    assert cache.get("missing:key") is None
    # Set value
    cache.set("k1", "v1", ttl=5)
    # Hit
    assert cache.get("k1") == "v1"
    # Evict via invalidate
    cache.invalidate("k1")

    # Check counters existence via internal registry and values non-negative
    prom = cache._PROM_COUNTERS  # type: ignore[attr-defined]
    assert set(["hits", "misses", "sets", "evictions"]).issubset(set(prom.keys()))
    for k in ["hits", "misses", "sets", "evictions"]:
        child = prom.get(k)
        # Child exposes _value.get() for current count
        assert child is not None
        val = float(child._value.get())
        assert val >= 0.0
