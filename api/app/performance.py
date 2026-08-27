"""Small, process-local performance primitives for the single-instance API."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Generic, TypeVar

ValueT = TypeVar("ValueT")


class AsyncTTLCache(Generic[ValueT]):
    """A bounded TTL cache safe to use from FastAPI request handlers."""

    def __init__(self, *, max_entries: int, ttl_seconds: int):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: OrderedDict[str, tuple[float, ValueT]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ValueT | None:
        now = time.monotonic()
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return value

    async def set(self, key: str, value: ValueT) -> None:
        async with self._lock:
            self._entries[key] = (time.monotonic() + self.ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()
