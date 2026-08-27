"""Schedule intent extraction, requirement resolution, and conflict detection."""

from __future__ import annotations

import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import DayOfWeek, DeliveryMode, Offering, Status


class ConstraintStrength(str, Enum):
    """Whether a student stated a hard limit or a ranking preference."""

    REQUIRED = "required"
    PREFERRED = "preferred"


class IntentIssueSeverity(str, Enum):
    """Whether an interpretation can be safely applied without another answer."""

    WARNING = "warning"
    BLOCKING = "blocking"


class IntentIssue(BaseModel):
    """A deterministic problem found while resolving an extracted intent."""

    code: str
    severity: IntentIssueSeverity
    message: str
    source_text: str | None = None


class ExtractedCourseGroup(BaseModel):
    """A model-extracted request to choose courses matching a level rule."""

    model_config = ConfigDict(extra="forbid")

    departments: list[str] = Field(..., min_length=1, max_length=8)
    minimum_level: int = Field(..., ge=0, le=9999)
    course_count: int = Field(..., ge=1, le=8)
    source_text: str = Field(..., max_length=300)

    @field_validator("departments")
    @classmethod
    def normalize_departments(cls, departments: list[str]) -> list[str]:
        normalized: list[str] = []
        for department in departments:
            value = department.strip().upper()
            if re.fullmatch(r"[A-Z]{2,5}", value) and value not in normalized:
                normalized.append(value)
        if not normalized:
            raise ValueError("At least one valid department is required")
        return normalized


class ExtractedNamedRequirement(BaseModel):
    """A model-extracted reference to a curated NJIT requirement."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: Literal["computing_literacy_ger"]
    course_count: int = Field(..., ge=1, le=8)
    source_text: str = Field(..., max_length=300)


class ExtractedScheduleIntent(BaseModel):
    """Strict single-call output expected from the language model."""

    model_config = ConfigDict(extra="forbid")

    courses: list[str]
    excluded_courses: list[str]
    course_groups: list[ExtractedCourseGroup]
    named_requirements: list[ExtractedNamedRequirement]
    unavailable_blocks: list["ParsedAvailabilityBlock"]
    min_credits: int | None = Field(..., ge=0, le=30)
    max_credits: int | None = Field(..., ge=0, le=30)
    time_preference: Literal["morning", "afternoon", "evening"] | None
    time_preference_strength: ConstraintStrength | None
    delivery_preference: DeliveryMode | None
    delivery_preference_strength: ConstraintStrength | None
    unresolved_requests: list[str]
    confidence: Literal["high", "medium", "low"]

    @field_validator("courses", "excluded_courses", mode="before")
    @classmethod
    def normalize_courses(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Course values must be lists")

        courses: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            match = re.fullmatch(r"\s*([A-Za-z]{2,5})\s*[- ]?\s*(\d{3,4}[A-Za-z]?)\s*", item)
            if not match:
                continue
            course_key = f"{match.group(1).upper()} {match.group(2).upper()}"
            if course_key not in courses:
                courses.append(course_key)
        return courses

    @field_validator("unavailable_blocks", mode="before")
    @classmethod
    def normalize_unavailable_blocks(cls, value: object) -> object:
        return [] if value is None else value


class ParsedAvailabilityBlock(BaseModel):
    """A validated unavailable period extracted from the user's description."""

    model_config = ConfigDict(extra="forbid")

    day: DayOfWeek
    start_min: int = Field(..., ge=0, lt=1440)
    end_min: int = Field(..., ge=1, le=1440)

    @field_validator("end_min")
    @classmethod
    def validate_end(cls, end_min: int, info) -> int:
        start_min = info.data.get("start_min")
        if start_min is not None and end_min <= start_min:
            raise ValueError("Unavailable block must end after it starts")
        return end_min


ExtractedScheduleIntent.model_rebuild()


class ResolvedCourseChoiceGroup(BaseModel):
    """A requirement expanded into current-term catalog course keys."""

    id: str
    label: str
    eligible_course_keys: list[str]
    choose: int = Field(..., ge=1, le=8)
    total_course_count: int = Field(..., ge=0)
    open_course_count: int = Field(..., ge=0)
    departments: list[str] = Field(default_factory=list)
    minimum_level: int | None = None
    requirement_id: str | None = None
    source_text: str | None = None


class ResolvedScheduleIntent(BaseModel):
    """Catalog-validated constraints safe for review and schedule generation."""

    schema_version: Literal["1.0"] = "1.0"
    courses: list[str] = Field(default_factory=list)
    excluded_courses: list[str] = Field(default_factory=list)
    course_groups: list[ResolvedCourseChoiceGroup] = Field(default_factory=list)
    unavailable_blocks: list[ParsedAvailabilityBlock] = Field(default_factory=list)
    min_credits: int | None = None
    max_credits: int | None = None
    time_preference: Literal["morning", "afternoon", "evening"] | None = None
    time_preference_strength: ConstraintStrength | None = None
    delivery_preference: DeliveryMode | None = None
    delivery_preference_strength: ConstraintStrength | None = None
    unresolved_requests: list[str] = Field(default_factory=list)
    issues: list[IntentIssue] = Field(default_factory=list)


class RequirementDefinition(BaseModel):
    """A curated, source-backed named academic requirement."""

    id: str
    label: str
    catalog_year: str
    choose: int = Field(..., ge=1, le=8)
    course_keys: list[str]
    source_url: str


class RequirementRegistry(BaseModel):
    """Versioned collection of named requirements."""

    catalog_year: str
    requirements: list[RequirementDefinition]


REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "requirements" / "2026-2027.json"
)


@lru_cache(maxsize=1)
def load_requirement_registry() -> dict[str, RequirementDefinition]:
    """Load the checked-in requirement registry once per API process."""
    registry = RequirementRegistry.model_validate_json(REGISTRY_PATH.read_text())
    return {requirement.id: requirement for requirement in registry.requirements}


def _course_parts(course_key: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"([A-Z]{2,5})\s+(\d{3,4})(?:[A-Z])?", course_key)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def _window_is_fully_blocked(
    blocks: list[ParsedAvailabilityBlock], start_min: int, end_min: int
) -> bool:
    """Return true when every weekday has the whole requested window blocked."""
    weekdays = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ]
    for day in weekdays:
        intervals = sorted(
            (max(block.start_min, start_min), min(block.end_min, end_min))
            for block in blocks
            if block.day == day and block.end_min > start_min and block.start_min < end_min
        )
        cursor = start_min
        for interval_start, interval_end in intervals:
            if interval_start > cursor:
                break
            cursor = max(cursor, interval_end)
        if cursor < end_min:
            return False
    return True


def resolve_schedule_intent(
    extracted: ExtractedScheduleIntent,
    catalog: list[Offering] | None = None,
) -> ResolvedScheduleIntent:
    """Resolve model output against curated requirements and the current catalog."""
    catalog_keys = {offering.course_key for offering in catalog or []}
    catalog_was_provided = catalog is not None
    open_keys = {
        offering.course_key for offering in catalog or [] if offering.status == Status.OPEN
    }
    issues: list[IntentIssue] = []

    courses = [course for course in extracted.courses if course not in extracted.excluded_courses]
    if catalog_was_provided:
        missing_courses = [course for course in courses if course not in catalog_keys]
        courses = [course for course in courses if course in catalog_keys]
        for course in missing_courses:
            issues.append(
                IntentIssue(
                    code="course_not_offered",
                    severity=IntentIssueSeverity.BLOCKING,
                    message=f"{course} is not offered in the loaded term.",
                    source_text=course,
                )
            )

    groups: list[ResolvedCourseChoiceGroup] = []
    for index, group in enumerate(extracted.course_groups):
        candidates: list[str] = []
        if catalog_was_provided:
            for course_key in catalog_keys:
                parts = _course_parts(course_key)
                if (
                    parts
                    and parts[0] in group.departments
                    and parts[1] >= group.minimum_level
                    and course_key not in extracted.excluded_courses
                    and course_key not in courses
                ):
                    candidates.append(course_key)
        candidates.sort()
        label = (
            f"{('/'.join(group.departments))} elective · "
            f"{group.minimum_level}+ · choose {group.course_count}"
        )
        resolved = ResolvedCourseChoiceGroup(
            id=f"elective-{index}-{'-'.join(group.departments).lower()}-{group.minimum_level}",
            label=label,
            eligible_course_keys=candidates,
            choose=group.course_count,
            total_course_count=len(candidates),
            open_course_count=len(set(candidates) & open_keys),
            departments=group.departments,
            minimum_level=group.minimum_level,
            source_text=group.source_text,
        )
        groups.append(resolved)
        if catalog_was_provided and len(candidates) < group.course_count:
            issues.append(
                IntentIssue(
                    code="insufficient_requirement_courses",
                    severity=IntentIssueSeverity.BLOCKING,
                    message=f"{label} has only {len(candidates)} matching courses this term.",
                    source_text=group.source_text,
                )
            )

    registry = load_requirement_registry()
    for named in extracted.named_requirements:
        definition = registry[named.requirement_id]
        choose = named.course_count or definition.choose
        candidates = [
            course
            for course in definition.course_keys
            if course not in extracted.excluded_courses
            and course not in courses
            and (not catalog_was_provided or course in catalog_keys)
        ]
        resolved = ResolvedCourseChoiceGroup(
            id=f"requirement-{definition.id}",
            label=f"{definition.label} · choose {choose}",
            eligible_course_keys=candidates,
            choose=choose,
            total_course_count=len(candidates),
            open_course_count=len(set(candidates) & open_keys),
            requirement_id=definition.id,
            source_text=named.source_text,
        )
        groups.append(resolved)
        if catalog_was_provided and len(candidates) < choose:
            issues.append(
                IntentIssue(
                    code="insufficient_requirement_courses",
                    severity=IntentIssueSeverity.BLOCKING,
                    message=(
                        f"{definition.label} has only {len(candidates)} matching courses this term."
                    ),
                    source_text=named.source_text,
                )
            )

    if (
        extracted.min_credits is not None
        and extracted.max_credits is not None
        and extracted.min_credits > extracted.max_credits
    ):
        issues.append(
            IntentIssue(
                code="conflicting_credit_range",
                severity=IntentIssueSeverity.BLOCKING,
                message=(
                    f"The minimum of {extracted.min_credits} credits is greater than the "
                    f"maximum of {extracted.max_credits}."
                ),
            )
        )

    if extracted.time_preference:
        windows = {
            "morning": (0, 720),
            "afternoon": (720, 1020),
            "evening": (1020, 1440),
        }
        start_min, end_min = windows[extracted.time_preference]
        if _window_is_fully_blocked(extracted.unavailable_blocks, start_min, end_min):
            severity = (
                IntentIssueSeverity.BLOCKING
                if extracted.time_preference_strength == ConstraintStrength.REQUIRED
                else IntentIssueSeverity.WARNING
            )
            issues.append(
                IntentIssue(
                    code="conflicting_time_constraints",
                    severity=severity,
                    message=(
                        f"The unavailable times leave no {extracted.time_preference} window "
                        "on weekdays."
                    ),
                )
            )

    for unresolved in extracted.unresolved_requests:
        issues.append(
            IntentIssue(
                code="unresolved_request",
                severity=(
                    IntentIssueSeverity.BLOCKING
                    if not courses and not groups
                    else IntentIssueSeverity.WARNING
                ),
                message=f"This still needs a course or requirement: {unresolved}",
                source_text=unresolved,
            )
        )

    return ResolvedScheduleIntent(
        courses=courses,
        excluded_courses=extracted.excluded_courses,
        course_groups=groups,
        unavailable_blocks=extracted.unavailable_blocks,
        min_credits=extracted.min_credits,
        max_credits=extracted.max_credits,
        time_preference=extracted.time_preference,
        time_preference_strength=extracted.time_preference_strength,
        delivery_preference=extracted.delivery_preference,
        delivery_preference_strength=extracted.delivery_preference_strength,
        unresolved_requests=extracted.unresolved_requests,
        issues=issues,
    )
