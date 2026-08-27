"""Tests for bounded process-local caches."""

import asyncio

from app.performance import AsyncTTLCache


async def test_ttl_cache_evicts_the_oldest_entry():
    cache = AsyncTTLCache[str](max_entries=2, ttl_seconds=60)

    await cache.set("first", "one")
    await cache.set("second", "two")
    assert await cache.get("first") == "one"
    await cache.set("third", "three")

    assert await cache.get("first") == "one"
    assert await cache.get("second") is None
    assert await cache.get("third") == "three"


async def test_ttl_cache_expires_and_clears_entries():
    cache = AsyncTTLCache[str](max_entries=2, ttl_seconds=0)
    await cache.set("short", "value")
    await asyncio.sleep(0)
    assert await cache.get("short") is None

    cache = AsyncTTLCache[str](max_entries=2, ttl_seconds=60)
    await cache.set("kept", "value")
    await cache.clear()
    assert await cache.get("kept") is None
