"""AI-powered natural language schedule parsing using Anthropic Claude."""

import json
import os
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from pydantic import BaseModel

from app.models import DayOfWeek


class ParsedConstraints(BaseModel):
    """Parsed constraints from natural language input."""

    courses: List[str] = []
    unavailable_blocks: List[Dict[str, Any]] = []
    min_credits: Optional[int] = None
    max_credits: Optional[int] = None
    time_preferences: Optional[str] = None
    delivery_preference: Optional[str] = None


class AIParseRequest(BaseModel):
    """Request to parse natural language schedule description."""

    prompt: str
    user_api_key: Optional[str] = None


class AIParseResponse(BaseModel):
    """Response from AI parsing."""

    constraints: ParsedConstraints
    confidence: str
    raw_response: str


# In-memory rate limiting storage
# Format: {ip_address: {"count": int, "reset_time": datetime}}
rate_limit_storage: Dict[str, Dict] = {}


DAY_MAP = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
    "mon": "Mon",
    "tue": "Tue",
    "wed": "Wed",
    "thu": "Thu",
    "fri": "Fri",
    "sat": "Sat",
    "sun": "Sun",
    "m": "Mon",
    "t": "Tue",
    "w": "Wed",
    "r": "Thu",  # Common abbreviation
    "f": "Fri",
}


SYSTEM_PROMPT = """You are an AI assistant that helps students describe their ideal course schedule. Parse natural language into structured JSON constraints.

Output ONLY valid JSON in this exact format:
{
  "courses": ["CS 100", "MATH 111"],
  "unavailable_blocks": [
    {"day": "Tue", "start_min": 840, "end_min": 960},
    {"day": "Thu", "start_min": 840, "end_min": 960}
  ],
  "min_credits": 12,
  "max_credits": 18,
  "time_preferences": "morning",
  "delivery_preference": "in-person",
  "confidence": "high"
}

Rules:
- Course keys: "SUBJ ###" format (e.g., "CS 100", "MATH 111")
- Days: Mon, Tue, Wed, Thu, Fri, Sat, Sun
- Times: minutes from midnight (e.g., 10am = 600, 2pm = 840)
- Common times: 8am=480, 9am=540, 10am=600, 12pm=720, 2pm=840, 4pm=960, 6pm=1080
- Time preferences: "morning" (before 12pm), "afternoon" (12pm-5pm), "evening" (after 5pm)
- Delivery: "in-person", "online", "hybrid", "async"
- Confidence: "high", "medium", "low" based on clarity

Examples:
Input: "I need CS 100 and CS 114, no Friday classes"
Output: {"courses": ["CS 100", "CS 114"], "unavailable_blocks": [{"day": "Fri", "start_min": 0, "end_min": 1439}], "confidence": "high"}

Input: "MATH 111 and PHYS 111, prefer morning classes, 12-15 credits"
Output: {"courses": ["MATH 111", "PHYS 111"], "time_preferences": "morning", "min_credits": 12, "max_credits": 15, "confidence": "high"}

Input: "CS courses, busy Tuesdays 2-4pm, no classes before 10am"
Output: {"courses": [], "unavailable_blocks": [{"day": "Tue", "start_min": 840, "end_min": 960}, {"day": "Mon", "start_min": 0, "end_min": 600}, {"day": "Tue", "start_min": 0, "end_min": 600}, {"day": "Wed", "start_min": 0, "end_min": 600}, {"day": "Thu", "start_min": 0, "end_min": 600}, {"day": "Fri", "start_min": 0, "end_min": 600}], "confidence": "medium"}

Return ONLY the JSON object, no explanations."""


async def parse_natural_language(
    prompt: str, user_api_key: Optional[str] = None
) -> AIParseResponse:
    """
    Parse natural language schedule description into structured constraints.

    Args:
        prompt: User's natural language description
        user_api_key: Optional user-provided API key

    Returns:
        Parsed constraints and confidence score
    """
    # Use user's key if provided, otherwise use shared pool key
    api_key = user_api_key or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("No Anthropic API key available")

    client = Anthropic(api_key=api_key)

    # Call Claude API
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Haiku is fast and cheap
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract response
    response_text = message.content[0].text.strip()

    # Parse JSON response
    try:
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(response_text)

        # Extract confidence (default to medium if not provided)
        confidence = parsed.pop("confidence", "medium")

        # Create constraints object
        constraints = ParsedConstraints(**parsed)

        return AIParseResponse(
            constraints=constraints, confidence=confidence, raw_response=response_text
        )

    except (json.JSONDecodeError, Exception) as e:
        # If parsing fails, return empty constraints with low confidence
        return AIParseResponse(
            constraints=ParsedConstraints(),
            confidence="low",
            raw_response=f"Error parsing response: {str(e)}\n\nRaw: {response_text}",
        )
