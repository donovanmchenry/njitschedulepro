"""Tests for the constraint solver."""

import pytest

from app.models import (
    AvailabilityBlock,
    DayOfWeek,
    Meeting,
    Offering,
    ScheduleFilters,
    SolveRequest,
    Status,
)
from app.solver import solve_schedules


class TestScheduleSolver:
    """Tests for schedule solver."""

    @pytest.fixture
    def sample_offerings(self):
        """Create sample offerings for testing."""
        return [
            # CS 100 - Section 1 (MW 10:00-11:20)
            Offering(
                crn="11001",
                course_key="CS 100",
                section="001",
                title="Intro to CS",
                meetings=[
                    Meeting(day=DayOfWeek.MONDAY, start_min=600, end_min=680, location="CKB 101"),
                    Meeting(day=DayOfWeek.WEDNESDAY, start_min=600, end_min=680, location="CKB 101"),
                ],
                status=Status.OPEN,
                capacity=40,
                enrolled=30,
                credits=3.0,
            ),
            # CS 100 - Section 2 (TR 14:00-15:20)
            Offering(
                crn="11002",
                course_key="CS 100",
                section="002",
                title="Intro to CS",
                meetings=[
                    Meeting(day=DayOfWeek.TUESDAY, start_min=840, end_min=920, location="CKB 102"),
                    Meeting(day=DayOfWeek.THURSDAY, start_min=840, end_min=920, location="CKB 102"),
                ],
                status=Status.OPEN,
                capacity=40,
                enrolled=25,
                credits=3.0,
            ),
            # MATH 111 - Section 1 (MWF 9:00-9:50)
            Offering(
                crn="12001",
                course_key="MATH 111",
                section="001",
                title="Calculus I",
                meetings=[
                    Meeting(day=DayOfWeek.MONDAY, start_min=540, end_min=590, location="TIER 201"),
                    Meeting(day=DayOfWeek.WEDNESDAY, start_min=540, end_min=590, location="TIER 201"),
                    Meeting(day=DayOfWeek.FRIDAY, start_min=540, end_min=590, location="TIER 201"),
                ],
                status=Status.OPEN,
                capacity=50,
                enrolled=40,
                credits=4.0,
            ),
            # MATH 111 - Section 2 (TR 11:00-12:15)
            Offering(
                crn="12002",
                course_key="MATH 111",
                section="002",
                title="Calculus I",
                meetings=[
                    Meeting(day=DayOfWeek.TUESDAY, start_min=660, end_min=735, location="TIER 202"),
                    Meeting(day=DayOfWeek.THURSDAY, start_min=660, end_min=735, location="TIER 202"),
                ],
                status=Status.OPEN,
                capacity=50,
                enrolled=35,
                credits=4.0,
            ),
        ]

    def test_basic_schedule_generation(self, sample_offerings):
        """Test basic schedule generation with two courses."""
        request = SolveRequest(
            required_course_keys=["CS 100", "MATH 111"],
            unavailable=[],
            filters=ScheduleFilters(status=[Status.OPEN]),
        )

        schedules = solve_schedules(sample_offerings, request)

        # Should find multiple valid schedules
        assert len(schedules) > 0

        # All schedules should have both courses
        for schedule in schedules:
            course_keys = {o.course_key for o in schedule.offerings}
            assert course_keys == {"CS 100", "MATH 111"}

        # All schedules should meet credit total
        for schedule in schedules:
            assert schedule.total_credits == 7.0

    def test_no_overlapping_meetings(self, sample_offerings):
        """Ensure generated schedules have no overlapping meetings."""
        request = SolveRequest(
            required_course_keys=["CS 100", "MATH 111"],
            unavailable=[],
        )

        schedules = solve_schedules(sample_offerings, request)

        for schedule in schedules:
            # Check all pairs of offerings
            offerings_list = schedule.offerings
            for i in range(len(offerings_list)):
                for j in range(i + 1, len(offerings_list)):
                    assert not offerings_list[i].overlaps_with(offerings_list[j])

    def test_availability_constraints(self, sample_offerings):
        """Test that availability constraints are respected."""
        # Block Monday 10:00-11:00 (overlaps with CS 100 Section 1)
        request = SolveRequest(
            required_course_keys=["CS 100", "MATH 111"],
            unavailable=[
                AvailabilityBlock(day=DayOfWeek.MONDAY, start_min=600, end_min=660),
            ],
        )

        schedules = solve_schedules(sample_offerings, request)

        # Should still find schedules (using CS 100 Section 2)
        assert len(schedules) > 0

        # None should include CS 100 Section 1 (CRN 11001)
        for schedule in schedules:
            crns = {o.crn for o in schedule.offerings}
            assert "11001" not in crns

    def test_near_miss_tolerance(self, sample_offerings):
        """Test near-miss tolerance for slight constraint violations."""
        # Block Monday 10:00-11:00, but allow 30 min tolerance
        request = SolveRequest(
            required_course_keys=["CS 100"],
            unavailable=[
                AvailabilityBlock(day=DayOfWeek.MONDAY, start_min=600, end_min=660),
            ],
            near_miss_tolerance_min=30,
            weekly_violation_cap_min=60,
        )

        schedules = solve_schedules(sample_offerings, request)

        # Should find schedules including near-misses
        assert len(schedules) > 0

        # Some may have violations
        near_misses = [s for s in schedules if s.is_near_miss]
        if near_misses:
            for schedule in near_misses:
                assert schedule.total_violation_minutes > 0
                assert schedule.total_violation_minutes <= 60

    def test_credit_constraints(self, sample_offerings):
        """Test min/max credit constraints."""
        # Require at least 6 credits
        request = SolveRequest(
            required_course_keys=["CS 100", "MATH 111"],
            min_credits=6.0,
            max_credits=8.0,
            unavailable=[],
        )

        schedules = solve_schedules(sample_offerings, request)

        for schedule in schedules:
            assert 6.0 <= schedule.total_credits <= 8.0

    def test_no_valid_schedules(self, sample_offerings):
        """Test case where no valid schedules exist."""
        # Make constraints impossible: block all times
        request = SolveRequest(
            required_course_keys=["CS 100"],
            unavailable=[
                AvailabilityBlock(day=DayOfWeek.MONDAY, start_min=0, end_min=1440),
                AvailabilityBlock(day=DayOfWeek.TUESDAY, start_min=0, end_min=1440),
                AvailabilityBlock(day=DayOfWeek.WEDNESDAY, start_min=0, end_min=1440),
                AvailabilityBlock(day=DayOfWeek.THURSDAY, start_min=0, end_min=1440),
                AvailabilityBlock(day=DayOfWeek.FRIDAY, start_min=0, end_min=1440),
            ],
        )

        schedules = solve_schedules(sample_offerings, request)

        # Should return empty list
        assert len(schedules) == 0

    def test_schedule_scoring(self, sample_offerings):
        """Test that schedules are properly scored and sorted."""
        request = SolveRequest(
            required_course_keys=["CS 100"],
            unavailable=[],
        )

        schedules = solve_schedules(sample_offerings, request)

        # Schedules should be sorted by score (lower is better)
        if len(schedules) > 1:
            for i in range(len(schedules) - 1):
                assert schedules[i].score <= schedules[i + 1].score

    def test_deduplication(self, sample_offerings):
        """Test that duplicate schedules are removed."""
        # Add a duplicate offering
        duplicate = Offering(
            crn="11001",  # Same CRN as first CS 100
            course_key="CS 100",
            section="001",
            title="Intro to CS",
            meetings=[
                Meeting(day=DayOfWeek.MONDAY, start_min=600, end_min=680),
                Meeting(day=DayOfWeek.WEDNESDAY, start_min=600, end_min=680),
            ],
            status=Status.OPEN,
            credits=3.0,
        )

        offerings_with_dupe = sample_offerings + [duplicate]

        request = SolveRequest(
            required_course_keys=["CS 100"],
            unavailable=[],
        )

        schedules = solve_schedules(offerings_with_dupe, request)

        # Should not have duplicate schedules (same set of CRNs)
        seen = set()
        for schedule in schedules:
            sig = frozenset(o.crn for o in schedule.offerings)
            assert sig not in seen
            seen.add(sig)
