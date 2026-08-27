"""Tests for deterministic requirement resolution and conflict detection."""

from app.intent import ExtractedScheduleIntent, resolve_schedule_intent
from app.models import Offering, Status


def offering(course_key: str, status: Status = Status.OPEN) -> Offering:
    return Offering(
        crn=course_key.replace(" ", "") + status.value[:1],
        course_key=course_key,
        section="001",
        title=course_key,
        status=status,
        credits=3,
    )


def base_intent(**overrides) -> ExtractedScheduleIntent:
    values = {
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
        "confidence": "high",
    }
    return ExtractedScheduleIntent.model_validate({**values, **overrides})


def test_resolves_department_level_requirement_against_current_catalog():
    extracted = base_intent(
        course_groups=[
            {
                "departments": ["CS", "IS"],
                "minimum_level": 300,
                "course_count": 2,
                "source_text": "two CS or IS electives at 300+",
            }
        ]
    )
    catalog = [
        offering("CS 288"),
        offering("CS 350"),
        offering("IS 392", Status.CLOSED),
        offering("IT 400"),
    ]

    resolved = resolve_schedule_intent(extracted, catalog)

    assert resolved.course_groups[0].eligible_course_keys == ["CS 350", "IS 392"]
    assert resolved.course_groups[0].choose == 2
    assert resolved.course_groups[0].open_course_count == 1
    assert resolved.issues == []


def test_resolves_computing_literacy_without_choosing_for_student():
    extracted = base_intent(
        named_requirements=[
            {
                "requirement_id": "computing_literacy_ger",
                "course_count": 1,
                "source_text": "something for computing literacy",
            }
        ]
    )
    catalog = [offering("CS 100"), offering("DS 100"), offering("CS 114")]

    resolved = resolve_schedule_intent(extracted, catalog)

    assert resolved.courses == []
    assert resolved.course_groups[0].requirement_id == "computing_literacy_ger"
    assert resolved.course_groups[0].eligible_course_keys == ["CS 100", "DS 100"]


def test_exact_course_is_not_reused_to_satisfy_a_separate_requirement():
    extracted = base_intent(
        courses=["CS 350"],
        course_groups=[
            {
                "departments": ["CS"],
                "minimum_level": 300,
                "course_count": 1,
                "source_text": "CS 350 and another 300-level CS elective",
            }
        ],
    )
    catalog = [offering("CS 350"), offering("CS 375")]

    resolved = resolve_schedule_intent(extracted, catalog)

    assert resolved.courses == ["CS 350"]
    assert resolved.course_groups[0].eligible_course_keys == ["CS 375"]


def test_reports_conflicting_hard_time_window():
    blocks = [
        {"day": day, "start_min": 0, "end_min": 720}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]
    ]
    extracted = base_intent(
        time_preference="morning",
        time_preference_strength="required",
        unavailable_blocks=blocks,
    )

    resolved = resolve_schedule_intent(extracted)

    assert resolved.issues[0].code == "conflicting_time_constraints"
    assert resolved.issues[0].severity == "blocking"
