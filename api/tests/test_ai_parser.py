"""Tests for validated AI constraint parsing."""

import pytest

from app.ai_parser import parse_constraint_response
from app.models import DayOfWeek, DeliveryMode


def test_parse_constraint_response():
    result = parse_constraint_response(
        """```json
        {
          "courses": ["CS 114"],
          "unavailable_blocks": [{"day": "Fri", "start_min": 0, "end_min": 1440}],
          "min_credits": 12,
          "max_credits": 15,
          "time_preference": "morning",
          "delivery_preference": "In-Person",
          "confidence": "high"
        }
        ```"""
    )

    assert result.confidence == "high"
    assert result.constraints.courses == ["CS 114"]
    assert result.constraints.unavailable_blocks[0].day == DayOfWeek.FRIDAY
    assert result.constraints.delivery_preference == DeliveryMode.IN_PERSON.value


def test_parse_constraint_response_normalizes_nullable_lists_and_course_keys():
    result = parse_constraint_response(
        """{
          "courses": ["cs-114", "CS 114", "CS 300+", 123],
          "unavailable_blocks": null,
          "confidence": "medium"
        }"""
    )

    assert result.constraints.courses == ["CS 114"]
    assert result.constraints.unavailable_blocks == []


def test_parse_constraint_response_reports_contradictory_credit_range():
    result = parse_constraint_response(
        '{"courses":["CS 100"],"min_credits":18,"max_credits":12,"confidence":"high"}'
    )

    assert result.constraints.courses == ["CS 100"]
    assert result.constraints.min_credits == 18
    assert result.constraints.max_credits == 12
    assert result.constraints.issues[0].code == "conflicting_credit_range"
    assert result.constraints.issues[0].severity == "blocking"


@pytest.mark.parametrize(
    "response",
    [
        "not json",
        '{"unavailable_blocks":[{"day":"Fri","start_min":700,"end_min":600}]}',
    ],
)
def test_invalid_constraint_response(response):
    with pytest.raises(ValueError, match="invalid schedule description"):
        parse_constraint_response(response)
