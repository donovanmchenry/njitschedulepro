"""Rate limiting for AI features."""

from datetime import datetime, timedelta
from typing import Dict, Optional

# In-memory storage for rate limiting
# In production, this should be Redis or a database
# Format: {ip_address: {"daily_count": int, "total_count": int, "last_reset": datetime}}
usage_storage: Dict[str, Dict] = {}

# Rate limits based on $10 budget (~7,000 requests with Haiku)
# Conservative limits to prevent abuse
DAILY_LIMIT_PER_IP = 5  # 5 requests per day per IP
TOTAL_LIMIT_PER_IP = 15  # 15 total requests per IP (lifetime)
HOURLY_LIMIT_PER_IP = 3  # 3 requests per hour (prevents rapid abuse)
GLOBAL_TOTAL_LIMIT = 7000  # Total requests across all users

# Track global usage
global_usage = {"total_count": 0, "started_at": datetime.now()}


def get_usage_stats(ip_address: str) -> Dict:
    """Get current usage stats for an IP address."""
    if ip_address not in usage_storage:
        return {
            "daily_count": 0,
            "hourly_count": 0,
            "total_count": 0,
            "daily_remaining": DAILY_LIMIT_PER_IP,
            "hourly_remaining": HOURLY_LIMIT_PER_IP,
            "total_remaining": TOTAL_LIMIT_PER_IP,
            "global_remaining": GLOBAL_TOTAL_LIMIT - global_usage["total_count"],
        }

    usage = usage_storage[ip_address]
    now = datetime.now()

    # Reset daily count if it's a new day
    if usage.get("daily_reset", now) < now:
        usage["daily_count"] = 0
        usage["daily_reset"] = now + timedelta(days=1)

    # Reset hourly count if it's a new hour
    if usage.get("hourly_reset", now) < now:
        usage["hourly_count"] = 0
        usage["hourly_reset"] = now + timedelta(hours=1)

    return {
        "daily_count": usage.get("daily_count", 0),
        "hourly_count": usage.get("hourly_count", 0),
        "total_count": usage.get("total_count", 0),
        "daily_remaining": max(0, DAILY_LIMIT_PER_IP - usage.get("daily_count", 0)),
        "hourly_remaining": max(0, HOURLY_LIMIT_PER_IP - usage.get("hourly_count", 0)),
        "total_remaining": max(0, TOTAL_LIMIT_PER_IP - usage.get("total_count", 0)),
        "global_remaining": max(0, GLOBAL_TOTAL_LIMIT - global_usage["total_count"]),
    }


def check_rate_limit(ip_address: str, use_user_key: bool = False) -> tuple[bool, Optional[str]]:
    """
    Check if request is within rate limits.

    Args:
        ip_address: User's IP address
        use_user_key: True if user is using their own API key (no limits)

    Returns:
        (allowed, error_message): Whether request is allowed and error message if not
    """
    # No limits if user provides their own API key
    if use_user_key:
        return True, None

    # Check global limit
    if global_usage["total_count"] >= GLOBAL_TOTAL_LIMIT:
        return False, "Shared API quota exhausted. Please provide your own Anthropic API key."

    # Initialize if first time
    if ip_address not in usage_storage:
        now = datetime.now()
        usage_storage[ip_address] = {
            "daily_count": 0,
            "hourly_count": 0,
            "total_count": 0,
            "daily_reset": now + timedelta(days=1),
            "hourly_reset": now + timedelta(hours=1),
        }

    usage = usage_storage[ip_address]
    now = datetime.now()

    # Reset counters if needed
    if usage.get("daily_reset", now) < now:
        usage["daily_count"] = 0
        usage["daily_reset"] = now + timedelta(days=1)

    if usage.get("hourly_reset", now) < now:
        usage["hourly_count"] = 0
        usage["hourly_reset"] = now + timedelta(hours=1)

    # Check limits
    if usage["total_count"] >= TOTAL_LIMIT_PER_IP:
        return (
            False,
            f"Total quota exceeded ({TOTAL_LIMIT_PER_IP} requests). Please provide your own API key for unlimited access.",
        )

    if usage["daily_count"] >= DAILY_LIMIT_PER_IP:
        reset_time = usage["daily_reset"].strftime("%H:%M")
        return (
            False,
            f"Daily quota exceeded ({DAILY_LIMIT_PER_IP} requests/day). Resets at {reset_time}.",
        )

    if usage["hourly_count"] >= HOURLY_LIMIT_PER_IP:
        reset_time = usage["hourly_reset"].strftime("%H:%M")
        return False, f"Too many requests. Try again after {reset_time}."

    return True, None


def increment_usage(ip_address: str, use_user_key: bool = False):
    """Increment usage counters after successful API call."""
    # Don't track if using own key
    if use_user_key:
        return

    # Always increment global counter
    global_usage["total_count"] += 1

    # Increment IP-specific counters
    if ip_address in usage_storage:
        usage_storage[ip_address]["daily_count"] += 1
        usage_storage[ip_address]["hourly_count"] += 1
        usage_storage[ip_address]["total_count"] += 1


def get_global_stats() -> Dict:
    """Get global usage statistics."""
    return {
        "total_requests": global_usage["total_count"],
        "total_limit": GLOBAL_TOTAL_LIMIT,
        "remaining": max(0, GLOBAL_TOTAL_LIMIT - global_usage["total_count"]),
        "percentage_used": round(
            (global_usage["total_count"] / GLOBAL_TOTAL_LIMIT) * 100, 2
        ),
        "started_at": global_usage["started_at"].isoformat(),
        "estimated_cost": round(global_usage["total_count"] * 0.0014, 2),  # $0.0014 per request
    }
