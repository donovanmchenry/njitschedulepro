"""AI-assisted schedule intent extraction with deterministic resolution."""

from __future__ import annotations

import json
import os
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field, ValidationError

from app.intent import (
    ExtractedScheduleIntent,
    IntentIssueSeverity,
    ResolvedScheduleIntent,
    resolve_schedule_intent,
)
from app.models import Offering


class AIParseRequest(BaseModel):
    """Request to interpret a natural-language schedule description."""

    prompt: str = Field(..., min_length=3, max_length=1000)


class AIParseResponse(BaseModel):
    """Catalog-resolved interpretation returned to the review UI."""

    constraints: ResolvedScheduleIntent
    confidence: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


SYSTEM_PROMPT = """You extract scheduling intent from an NJIT student's description.

The API constrains your response to a JSON schema. Fill every field.

Rules:
- Exact courses belong in courses, normalized as "SUBJ ###".
- A negated course belongs only in excluded_courses.
- If the student corrects a course, keep only the corrected course.
- Requirements such as "two CS electives 300 or above" belong in course_groups.
- Never turn a level requirement into fake courses such as "CS 300" or "CS 300+".
- "Computing Literacy" or "Computing Literacy GER" maps to named requirement
  computing_literacy_ger. Do not choose an arbitrary course for it.
- A broad topic without course numbers or a supported named requirement, such as
  "cybersecurity stuff", belongs in unresolved_requests. Do not invent courses.
- Valid days are Mon, Tue, Wed, Thu, Fri, Sat, and Sun.
- Times are minutes from midnight. A full unavailable day is 0 through 1440.
- In ordinary student schedule language, bare hours 1 through 7 mean PM unless the
  student says AM, morning, or overnight. Thus "2 to 6" is 840 through 1080,
  "after 4" starts at 960, and "before 1" ends at 780.
- Bare hours 8 through 11 mean AM unless the surrounding text says PM or evening.
- "Noon" is 720 and "midnight" is 0.
- "Only", "must", "nothing", "no classes", and "can't" indicate required constraints.
- "Prefer", "would like", "if possible", and "I guess" indicate preferred constraints.
- Use required for an unqualified delivery request such as "online only".
- time_preference is morning, afternoon, evening, or null.
- delivery_preference is In-Person, Online, Hybrid, Async, or null.
- If a preference value is null, its strength must also be null.
- Preserve contradictory statements instead of silently fixing them. Deterministic code
  will identify conflicts for the student.
- confidence is high, medium, or low based on how clearly the text maps to this schema.
"""


def _legacy_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep local tests and saved fixtures compatible with the richer schema."""
    defaults: dict[str, Any] = {
        "courses": [],
        "excluded_courses": [],
        "course_groups": [],
        "named_requirements": [],
        "unavailable_blocks": [],
        "min_credits": None,
        "max_credits": None,
        "time_preference": None,
        "time_preference_strength": None,
        "delivery_preference": None,
        "delivery_preference_strength": None,
        "unresolved_requests": [],
        "confidence": "medium",
    }
    return {**defaults, **payload}


def _resolved_confidence(extracted: ExtractedScheduleIntent, resolved: ResolvedScheduleIntent) -> str:
    """Blocking deterministic conflicts always make the interpretation low confidence."""
    if any(issue.severity == IntentIssueSeverity.BLOCKING for issue in resolved.issues):
        return "low"
    return extracted.confidence


def parse_constraint_response(
    response_text: str,
    catalog: list[Offering] | None = None,
) -> AIParseResponse:
    """Parse structured model output and resolve it against application data."""
    cleaned = response_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        payload = json.loads(cleaned)
        extracted = ExtractedScheduleIntent.model_validate(_legacy_defaults(payload))
        resolved = resolve_schedule_intent(extracted, catalog)
        return AIParseResponse(
            constraints=resolved,
            confidence=_resolved_confidence(extracted, resolved),
        )
    except (json.JSONDecodeError, ValidationError, AttributeError, TypeError) as exc:
        raise ValueError("The AI returned an invalid schedule description") from exc


async def parse_natural_language(
    prompt: str,
    catalog: list[Offering] | None = None,
) -> AIParseResponse:
    """Extract one strict model response, then resolve it deterministically."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("AI schedule parsing is not configured")

    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    client = AsyncAnthropic(api_key=api_key)
    message = await client.messages.parse(
        model=model,
        max_tokens=1536,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_format=ExtractedScheduleIntent,
    )

    if message.stop_reason in {"refusal", "max_tokens"}:
        raise ValueError(f"The AI response stopped with reason: {message.stop_reason}")
    if not message.content or not hasattr(message.content[0], "parsed_output"):
        raise ValueError("The AI returned an empty schedule description")
    extracted = message.content[0].parsed_output
    if extracted is None:
        raise ValueError("The AI returned an invalid schedule description")
    resolved = resolve_schedule_intent(extracted, catalog)
    return AIParseResponse(
        constraints=resolved,
        confidence=_resolved_confidence(extracted, resolved),
        model=model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
