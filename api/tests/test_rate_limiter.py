"""Tests for atomic rate limits and token telemetry."""

import asyncio

import pytest
from fakeredis.aioredis import FakeRedis
from redis.exceptions import ConnectionError

from app.shared_rate_limiter import (
    MemoryCounterStore,
    RateLimitConfig,
    RateLimiter,
    RateLimitExceededError,
    RateLimitUnavailableError,
    RedisCounterStore,
)


class FakeClock:
    def __init__(self, value: float = 1_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value


def limiter(
    *,
    clock=None,
    hourly: int = 2,
    daily: int = 20,
    total: int = 30,
    global_total: int = 40,
    solve: int = 2,
) -> RateLimiter:
    return RateLimiter(
        MemoryCounterStore(clock=clock or FakeClock()),
        RateLimitConfig(
            ai_hourly_per_user=hourly,
            ai_daily_per_user=daily,
            ai_total_per_user=total,
            ai_global_total=global_total,
            solve_per_minute=solve,
            key_prefix="test",
        ),
    )


@pytest.mark.asyncio
async def test_concurrent_ai_reservations_cannot_exceed_limit():
    rate_limiter = limiter(hourly=2)

    async def reserve():
        try:
            await rate_limiter.acquire_ai("203.0.113.8")
            return "allowed"
        except RateLimitExceededError:
            return "blocked"

    results = await asyncio.gather(*(reserve() for _ in range(20)))

    assert results.count("allowed") == 2
    assert results.count("blocked") == 18


@pytest.mark.asyncio
async def test_expiring_window_reopens_without_resetting_longer_windows():
    clock = FakeClock()
    rate_limiter = limiter(clock=clock, hourly=1, daily=3)

    first = await rate_limiter.acquire_ai("203.0.113.8")
    with pytest.raises(RateLimitExceededError) as blocked:
        await rate_limiter.acquire_ai("203.0.113.8")
    clock.value += 3_601
    second = await rate_limiter.acquire_ai("203.0.113.8")

    assert first["hourly_count"] == 1
    assert blocked.value.retry_after_seconds == 3_600
    assert second["hourly_count"] == 1
    assert second["daily_count"] == 2


@pytest.mark.asyncio
async def test_global_limit_is_shared_between_users():
    rate_limiter = limiter(global_total=2)

    await rate_limiter.acquire_ai("203.0.113.1")
    await rate_limiter.acquire_ai("203.0.113.2")

    with pytest.raises(RateLimitExceededError, match="shared AI quota"):
        await rate_limiter.acquire_ai("203.0.113.3")


@pytest.mark.asyncio
async def test_token_telemetry_uses_actual_counts_without_cost_guess():
    rate_limiter = limiter()

    await rate_limiter.acquire_ai("203.0.113.8")
    await rate_limiter.record_ai_tokens(420, 85)
    stats = await rate_limiter.global_stats()

    assert stats["total_requests"] == 1
    assert stats["successful_requests"] == 1
    assert stats["input_tokens"] == 420
    assert stats["output_tokens"] == 85
    assert "estimated_cost" not in stats


@pytest.mark.asyncio
async def test_solve_limit_is_atomic_and_returns_retry_after():
    rate_limiter = limiter(solve=1)

    await rate_limiter.acquire_solve("203.0.113.8")

    with pytest.raises(RateLimitExceededError) as blocked:
        await rate_limiter.acquire_solve("203.0.113.8")
    assert blocked.value.retry_after_seconds == 60


@pytest.mark.asyncio
async def test_raw_client_address_is_not_stored_in_counter_keys():
    store = MemoryCounterStore()
    rate_limiter = RateLimiter(store, RateLimitConfig(key_prefix="test"))

    await rate_limiter.acquire_ai("student-device.example")

    assert all("student-device.example" not in key for key in store._counters)


@pytest.mark.asyncio
async def test_redis_lua_reservation_is_atomic_under_concurrency():
    store = RedisCounterStore("redis://localhost:6379/0")
    store._client = FakeRedis(decode_responses=True)
    rate_limiter = RateLimiter(
        store,
        RateLimitConfig(
            ai_hourly_per_user=3,
            ai_daily_per_user=20,
            ai_total_per_user=30,
            ai_global_total=40,
            solve_per_minute=10,
            key_prefix="redis-test",
        ),
    )

    async def reserve():
        try:
            await rate_limiter.acquire_ai("203.0.113.8")
            return "allowed"
        except RateLimitExceededError:
            return "blocked"

    results = await asyncio.gather(*(reserve() for _ in range(25)))

    assert results.count("allowed") == 3
    assert results.count("blocked") == 22
    await store._client.aclose()


class UnavailableRedis:
    async def eval(self, *args):
        raise ConnectionError("offline")


@pytest.mark.asyncio
async def test_configured_redis_failure_does_not_fall_back_silently():
    store = RedisCounterStore("redis://localhost:6379/0")
    store._client = UnavailableRedis()
    rate_limiter = RateLimiter(store, RateLimitConfig())

    with pytest.raises(RateLimitUnavailableError):
        await rate_limiter.acquire_ai("203.0.113.8")
