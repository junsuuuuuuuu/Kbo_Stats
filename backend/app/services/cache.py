"""Thread-safe bounded TTL cache for upstream KBO responses."""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import TypeVar

Key = TypeVar("Key")
Value = TypeVar("Value")


class BoundedTTLCache[Key, Value]:
    """Expire stale entries and evict the least recently used entry at capacity."""

    def __init__(self, *, max_size: int, ttl_seconds: int) -> None:
        if max_size < 1 or ttl_seconds < 1:
            raise ValueError("max_size and ttl_seconds must be positive")
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._items: OrderedDict[Key, tuple[float, Value]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: Key) -> Value | None:
        now = time.monotonic()
        with self._lock:
            cached = self._items.get(key)
            if cached is None:
                return None
            created_at, value = cached
            if now - created_at >= self._ttl_seconds:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: Key, value: Value) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), value)
            self._items.move_to_end(key)
            while len(self._items) > self._max_size:
                self._items.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
