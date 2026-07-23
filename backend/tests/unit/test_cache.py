from app.services.cache import BoundedTTLCache


def test_bounded_cache_evicts_least_recently_used_entry() -> None:
    cache = BoundedTTLCache[str, int](max_size=2, ttl_seconds=60)
    cache.set("first", 1)
    cache.set("second", 2)
    assert cache.get("first") == 1

    cache.set("third", 3)

    assert cache.get("second") is None
    assert cache.get("first") == 1
    assert len(cache) == 2


def test_bounded_cache_expires_stale_entries(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    clock = iter([0.0, 2.0])
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: next(clock))
    cache = BoundedTTLCache[str, int](max_size=1, ttl_seconds=1)

    cache.set("key", 1)

    assert cache.get("key") is None
    assert len(cache) == 0
