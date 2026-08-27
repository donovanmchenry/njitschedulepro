"""Atomic shared rate limiting and AI usage telemetry."""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from dotenv import load_dotenv
from redis import asyncio as redis
from redis.exceptions import RedisError


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class RateLimitConfig:
    """Environment-configurable request ceilings."""

    ai_hourly_per_user: int = 3
    ai_daily_per_user: int = 5
    ai_total_per_user: int = 15
    ai_global_total: int = 7000
    solve_per_minute: int = 30
    key_prefix: str = "schedule-pro"

    @classmethod
    def from_environment(cls) -> "RateLimitConfig":
        return cls(
            ai_hourly_per_user=_positive_int("AI_HOURLY_LIMIT_PER_USER", 3),
            ai_daily_per_user=_positive_int("AI_DAILY_LIMIT_PER_USER", 5),
            ai_total_per_user=_positive_int("AI_TOTAL_LIMIT_PER_USER", 15),
            ai_global_total=_positive_int("AI_GLOBAL_TOTAL_LIMIT", 7000),
            solve_per_minute=_positive_int("SOLVE_RATE_LIMIT_PER_MINUTE", 30),
            key_prefix=os.getenv("RATE_LIMIT_KEY_PREFIX", "schedule-pro").strip()
            or "schedule-pro",
        )


@dataclass(frozen=True)
class CounterRule:
    name: str
    key: str
    limit: int
    ttl_seconds: int | None


@dataclass(frozen=True)
class AcquireResult:
    allowed: bool
    blocked_rule: str | None = None
    retry_after_seconds: int | None = None


class RateLimitExceededError(Exception):
    """A request exceeded one of the configured ceilings."""

    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RateLimitUnavailableError(Exception):
    """The configured shared counter store could not be reached."""


class CounterStore(Protocol):
    backend_name: str

    async def acquire(self, rules: list[CounterRule]) -> AcquireResult: ...

    async def counts(self, rules: list[CounterRule]) -> dict[str, int]: ...

    async def increment(self, values: dict[str, int]) -> None: ...

    async def get_values(self, keys: list[str]) -> dict[str, int]: ...

    async def started_at(self, key: str) -> str: ...

    async def healthy(self) -> bool: ...


class MemoryCounterStore:
    """Process-local fallback for development and tests."""

    backend_name = "memory"

    def __init__(self, clock=time.time):
        self._clock = clock
        self._counters: dict[str, tuple[int, float | None]] = {}
        self._values: dict[str, int] = {}
        self._started: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def _active_counter(self, key: str, now: float) -> tuple[int, float | None]:
        count, expires_at = self._counters.get(key, (0, None))
        if expires_at is not None and expires_at <= now:
            return 0, None
        return count, expires_at

    async def acquire(self, rules: list[CounterRule]) -> AcquireResult:
        async with self._lock:
            now = self._clock()
            active = {rule.name: self._active_counter(rule.key, now) for rule in rules}
            for rule in rules:
                count, expires_at = active[rule.name]
                if count >= rule.limit:
                    retry_after = (
                        max(1, math.ceil(expires_at - now)) if expires_at is not None else None
                    )
                    return AcquireResult(False, rule.name, retry_after)

            for rule in rules:
                count, expires_at = active[rule.name]
                if count == 0 and expires_at is None and rule.ttl_seconds is not None:
                    expires_at = now + rule.ttl_seconds
                self._counters[rule.key] = (count + 1, expires_at)
            return AcquireResult(True)

    async def counts(self, rules: list[CounterRule]) -> dict[str, int]:
        async with self._lock:
            now = self._clock()
            return {rule.name: self._active_counter(rule.key, now)[0] for rule in rules}

    async def increment(self, values: dict[str, int]) -> None:
        async with self._lock:
            for key, value in values.items():
                self._values[key] = self._values.get(key, 0) + value

    async def get_values(self, keys: list[str]) -> dict[str, int]:
        async with self._lock:
            return {key: self._values.get(key, 0) for key in keys}

    async def started_at(self, key: str) -> str:
        async with self._lock:
            return self._started.setdefault(key, datetime.now(timezone.utc).isoformat())

    async def healthy(self) -> bool:
        return True


ACQUIRE_SCRIPT = """
for index, key in ipairs(KEYS) do
  local current = tonumber(redis.call('GET', key) or '0')
  local limit = tonumber(ARGV[(index - 1) * 2 + 1])
  if current >= limit then
    local ttl = redis.call('TTL', key)
    return {0, index, ttl}
  end
end

for index, key in ipairs(KEYS) do
  local ttl = tonumber(ARGV[(index - 1) * 2 + 2])
  local current = redis.call('INCR', key)
  if current == 1 and ttl > 0 then
    redis.call('EXPIRE', key, ttl)
  end
end

return {1, 0, 0}
"""


class RedisCounterStore:
    """Redis/Valkey counter store using one Lua script per atomic reservation."""

    backend_name = "redis"

    def __init__(self, url: str):
        self._client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            health_check_interval=30,
        )

    @staticmethod
    def _unavailable() -> RateLimitUnavailableError:
        return RateLimitUnavailableError("Shared rate limiting is temporarily unavailable")

    async def acquire(self, rules: list[CounterRule]) -> AcquireResult:
        keys = [rule.key for rule in rules]
        arguments: list[int] = []
        for rule in rules:
            arguments.extend([rule.limit, rule.ttl_seconds or 0])
        try:
            result = await self._client.eval(ACQUIRE_SCRIPT, len(keys), *keys, *arguments)
        except RedisError as exc:
            raise self._unavailable() from exc
        allowed, blocked_index, ttl = (int(value) for value in result)
        if allowed:
            return AcquireResult(True)
        blocked_rule = rules[blocked_index - 1]
        return AcquireResult(False, blocked_rule.name, ttl if ttl > 0 else None)

    async def counts(self, rules: list[CounterRule]) -> dict[str, int]:
        try:
            values = await self._client.mget([rule.key for rule in rules])
        except RedisError as exc:
            raise self._unavailable() from exc
        return {
            rule.name: int(value or 0) for rule, value in zip(rules, values, strict=True)
        }

    async def increment(self, values: dict[str, int]) -> None:
        try:
            async with self._client.pipeline(transaction=True) as pipeline:
                for key, value in values.items():
                    pipeline.incrby(key, value)
                await pipeline.execute()
        except RedisError as exc:
            raise self._unavailable() from exc

    async def get_values(self, keys: list[str]) -> dict[str, int]:
        try:
            values = await self._client.mget(keys)
        except RedisError as exc:
            raise self._unavailable() from exc
        return {key: int(value or 0) for key, value in zip(keys, values, strict=True)}

    async def started_at(self, key: str) -> str:
        value = datetime.now(timezone.utc).isoformat()
        try:
            await self._client.set(key, value, nx=True)
            stored = await self._client.get(key)
        except RedisError as exc:
            raise self._unavailable() from exc
        return stored or value

    async def healthy(self) -> bool:
        try:
            return bool(await self._client.ping())
        except RedisError:
            return False


class RateLimiter:
    """Application policy over either local or shared atomic counters."""

    def __init__(self, store: CounterStore, config: RateLimitConfig):
        self.store = store
        self.config = config

    @classmethod
    def from_environment(cls) -> "RateLimiter":
        url = os.getenv("REDIS_URL", "").strip()
        store: CounterStore = RedisCounterStore(url) if url else MemoryCounterStore()
        return cls(store, RateLimitConfig.from_environment())

    @property
    def backend_name(self) -> str:
        return self.store.backend_name

    def _identity(self, client_address: str) -> str:
        return hashlib.sha256(client_address.encode("utf-8")).hexdigest()[:32]

    def _key(self, suffix: str) -> str:
        return f"{self.config.key_prefix}:rate-limit:{suffix}"

    def _ai_rules(self, client_address: str) -> list[CounterRule]:
        identity = self._identity(client_address)
        return [
            CounterRule(
                "global",
                self._key("ai:global"),
                self.config.ai_global_total,
                None,
            ),
            CounterRule(
                "total",
                self._key(f"ai:user:{identity}:total"),
                self.config.ai_total_per_user,
                2_592_000,
            ),
            CounterRule(
                "daily",
                self._key(f"ai:user:{identity}:daily"),
                self.config.ai_daily_per_user,
                86_400,
            ),
            CounterRule(
                "hourly",
                self._key(f"ai:user:{identity}:hourly"),
                self.config.ai_hourly_per_user,
                3_600,
            ),
        ]

    def _solve_rules(self, client_address: str) -> list[CounterRule]:
        identity = self._identity(client_address)
        return [
            CounterRule(
                "minute",
                self._key(f"solve:user:{identity}:minute"),
                self.config.solve_per_minute,
                60,
            )
        ]

    @staticmethod
    def _retry_text(seconds: int | None) -> str:
        if seconds is None:
            return ""
        minutes = max(1, math.ceil(seconds / 60))
        suffix = "s" if minutes != 1 else ""
        return f" Try again in about {minutes} minute{suffix}."

    async def acquire_ai(self, client_address: str) -> dict[str, int | str]:
        result = await self.store.acquire(self._ai_rules(client_address))
        if not result.allowed:
            messages = {
                "global": "The shared AI quota is currently exhausted.",
                "total": "This device has reached its AI request allowance.",
                "daily": "This device has reached its daily AI request allowance.",
                "hourly": "Too many AI requests from this device.",
            }
            message = messages[result.blocked_rule or "hourly"]
            raise RateLimitExceededError(
                message + self._retry_text(result.retry_after_seconds),
                result.retry_after_seconds,
            )
        return await self.usage_stats(client_address)

    async def acquire_solve(self, client_address: str) -> None:
        result = await self.store.acquire(self._solve_rules(client_address))
        if not result.allowed:
            raise RateLimitExceededError(
                "Too many schedule requests." + self._retry_text(result.retry_after_seconds),
                result.retry_after_seconds,
            )

    async def usage_stats(self, client_address: str) -> dict[str, int | str]:
        counts = await self.store.counts(self._ai_rules(client_address))
        return {
            "daily_count": counts["daily"],
            "hourly_count": counts["hourly"],
            "total_count": counts["total"],
            "daily_remaining": max(0, self.config.ai_daily_per_user - counts["daily"]),
            "hourly_remaining": max(0, self.config.ai_hourly_per_user - counts["hourly"]),
            "total_remaining": max(0, self.config.ai_total_per_user - counts["total"]),
            "global_remaining": max(0, self.config.ai_global_total - counts["global"]),
            "storage_backend": self.backend_name,
        }

    async def record_ai_tokens(self, input_tokens: int, output_tokens: int) -> None:
        await self.store.increment(
            {
                self._key("ai:successful"): 1,
                self._key("ai:input_tokens"): input_tokens,
                self._key("ai:output_tokens"): output_tokens,
            }
        )

    async def global_stats(self) -> dict[str, int | float | str]:
        global_rule = self._ai_rules("global-stats")[0]
        request_counts = await self.store.counts([global_rule])
        telemetry_keys = [
            self._key("ai:successful"),
            self._key("ai:input_tokens"),
            self._key("ai:output_tokens"),
        ]
        telemetry = await self.store.get_values(telemetry_keys)
        total_requests = request_counts["global"]
        return {
            "total_requests": total_requests,
            "successful_requests": telemetry[telemetry_keys[0]],
            "input_tokens": telemetry[telemetry_keys[1]],
            "output_tokens": telemetry[telemetry_keys[2]],
            "total_limit": self.config.ai_global_total,
            "remaining": max(0, self.config.ai_global_total - total_requests),
            "percentage_used": round(total_requests / self.config.ai_global_total * 100, 2),
            "started_at": await self.store.started_at(self._key("started_at")),
            "storage_backend": self.backend_name,
        }

    async def health(self) -> dict[str, str | bool]:
        return {"backend": self.backend_name, "healthy": await self.store.healthy()}


load_dotenv()
rate_limiter = RateLimiter.from_environment()


async def acquire_ai_request(client_address: str) -> dict[str, int | str]:
    return await rate_limiter.acquire_ai(client_address)


async def acquire_solve_request(client_address: str) -> None:
    await rate_limiter.acquire_solve(client_address)


async def record_ai_tokens(input_tokens: int, output_tokens: int) -> None:
    await rate_limiter.record_ai_tokens(input_tokens, output_tokens)


async def get_usage_stats(client_address: str) -> dict[str, int | str]:
    return await rate_limiter.usage_stats(client_address)


async def get_global_stats() -> dict[str, int | float | str]:
    return await rate_limiter.global_stats()


async def get_rate_limiter_health() -> dict[str, str | bool]:
    return await rate_limiter.health()
