"""Constraint-based schedule solver using backtracking."""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from app.models import (
    AvailabilityBlock,
    DayOfWeek,
    Offering,
    Schedule,
    ScheduleFilters,
    SolveRequest,
)


class ScheduleSolver:
    """
    Backtracking solver for generating valid course schedules.

    The solver:
    1. Groups offerings by course key
    2. Pre-filters by status, delivery, instructor, etc.
    3. Orders courses by fewest sections (fail-fast)
    4. Backtracks to find all valid schedules
    5. Computes soft scores for ranking
    """

    def __init__(self, catalog: List[Offering], request: SolveRequest):
        """
        Initialize solver with catalog and request.

        Args:
            catalog: Full list of offerings
            request: Solve request with constraints
        """
        self.catalog = catalog
        self.request = request
        self.results: List[Schedule] = []
        self.seen_signatures: Set[frozenset] = set()

        # Group offerings by course key
        self.offerings_by_course: Dict[str, List[Offering]] = defaultdict(list)
        for offering in catalog:
            self.offerings_by_course[offering.course_key].append(offering)

        # Pre-filter offerings
        self._prefilter_offerings()

        # Build unavailable blocks lookup
        self.unavailable_by_day: Dict[DayOfWeek, List[Tuple[int, int]]] = defaultdict(list)
        for block in request.unavailable:
            self.unavailable_by_day[block.day].append((block.start_min, block.end_min))

    def _prefilter_offerings(self):
        """Pre-filter offerings based on request filters."""
        filters = self.request.filters

        for course_key, offerings in self.offerings_by_course.items():
            filtered = []
            for offering in offerings:
                # Status filter
                if offering.status not in filters.status:
                    continue

                # Delivery filter
                if filters.delivery and offering.delivery not in filters.delivery:
                    continue

                # Instructor filters
                if filters.avoid_instructors and offering.instructor:
                    if any(
                        avoid.lower() in offering.instructor.lower()
                        for avoid in filters.avoid_instructors
                    ):
                        continue

                # Campus filters (check location of meetings)
                if filters.campus_exclude and offering.meetings:
                    exclude = False
                    for meeting in offering.meetings:
                        if meeting.location and any(
                            campus.lower() in meeting.location.lower()
                            for campus in filters.campus_exclude
                        ):
                            exclude = True
                            break
                    if exclude:
                        continue

                if filters.campus_include and offering.meetings:
                    include = False
                    for meeting in offering.meetings:
                        if meeting.location and any(
                            campus.lower() in meeting.location.lower()
                            for campus in filters.campus_include
                        ):
                            include = True
                            break
                    if not include:
                        continue

                # Time window filters
                if filters.earliest_start is not None or filters.latest_end is not None:
                    valid_time = True
                    for meeting in offering.meetings:
                        if (
                            filters.earliest_start is not None
                            and meeting.start_min < filters.earliest_start
                        ):
                            valid_time = False
                            break
                        if (
                            filters.latest_end is not None
                            and meeting.end_min > filters.latest_end
                        ):
                            valid_time = False
                            break
                    if not valid_time:
                        continue

                # Honors filter
                if offering.is_honors and not filters.include_honors:
                    continue
                if not offering.is_honors and not filters.include_non_honors:
                    continue

                filtered.append(offering)

            self.offerings_by_course[course_key] = filtered

    def solve(self) -> List[Schedule]:
        """
        Generate all valid schedules up to max_results.

        Returns:
            List of Schedule objects, sorted by score (lower is better)
        """
        # Order courses by fewest valid sections (fail-fast heuristic)
        required_courses = sorted(
            self.request.required_course_keys,
            key=lambda ck: len(self.offerings_by_course.get(ck, [])),
        )

        # Check if any required course has no valid offerings
        for course_key in required_courses:
            if not self.offerings_by_course.get(course_key):
                # No valid offerings for this course
                return []

        # Start backtracking
        self._backtrack(required_courses, 0, [])

        # Sort by score (lower is better)
        self.results.sort(key=lambda s: s.score)

        return self.results[: self.request.max_results]

    def _backtrack(
        self, course_keys: List[str], course_idx: int, current_schedule: List[Offering]
    ):
        """
        Recursive backtracking to build schedules.

        Args:
            course_keys: Ordered list of required course keys
            course_idx: Current course index being processed
            current_schedule: Current partial schedule
        """
        # Base case: all courses scheduled
        if course_idx >= len(course_keys):
            # Check credits constraint
            total_credits = sum(
                o.credits for o in current_schedule if o.credits is not None
            )
            if self.request.min_credits and total_credits < self.request.min_credits:
                return
            if self.request.max_credits and total_credits > self.request.max_credits:
                return

            # Check for duplicate signature
            sig = frozenset(o.crn for o in current_schedule)
            if sig in self.seen_signatures:
                return
            self.seen_signatures.add(sig)

            # Compute score
            score = self._compute_score(current_schedule)

            schedule = Schedule(
                offerings=current_schedule.copy(),
                total_credits=total_credits,
                score=score,
            )
            self.results.append(schedule)

            # Early termination if we have enough results
            if len(self.results) >= self.request.max_results * 2:
                return

            return

        # Recursive case: try each offering for current course
        course_key = course_keys[course_idx]
        offerings = self.offerings_by_course.get(course_key, [])

        for offering in offerings:
            # Check for conflicts with current schedule
            if self._has_conflict(offering, current_schedule):
                continue

            # Check availability conflicts (strict - no violations allowed)
            if self._conflicts_with_availability(offering):
                continue

            # Add to schedule and recurse
            current_schedule.append(offering)
            self._backtrack(course_keys, course_idx + 1, current_schedule)
            current_schedule.pop()

    def _has_conflict(self, offering: Offering, schedule: List[Offering]) -> bool:
        """Check if offering conflicts with any offering in the schedule."""
        for existing in schedule:
            if offering.overlaps_with(existing):
                return True
        return False

    def _conflicts_with_availability(self, offering: Offering) -> bool:
        """
        Check if offering conflicts with any unavailable time blocks (strict check).

        Args:
            offering: Offering to check

        Returns:
            True if there are any conflicts, False otherwise
        """
        for meeting in offering.meetings:
            unavailable_blocks = self.unavailable_by_day.get(meeting.day, [])
            for unavail_start, unavail_end in unavailable_blocks:
                conflicts, _ = meeting.conflicts_with_unavailable(unavail_start, unavail_end)
                if conflicts:
                    return True
        return False

    def _compute_score(self, schedule: List[Offering]) -> float:
        """
        Compute a score for ranking schedules (lower is better).

        Scoring hierarchy:
        1. Minimize gaps between classes (primary)
        2. Prefer instructors
        3. Maximize open seats
        4. Deterministic tie-break by CRN

        Returns:
            Float score where lower is better
        """
        # Primary: gaps between classes per day (weight 1000)
        total_gap_minutes = self._compute_total_gaps(schedule)
        score = total_gap_minutes * 1000.0

        # Secondary: instructor preference (weight 100)
        prefer_instructors = self.request.filters.prefer_instructors or []
        instructor_bonus = 0
        for offering in schedule:
            if offering.instructor and prefer_instructors:
                if any(
                    pref.lower() in offering.instructor.lower() for pref in prefer_instructors
                ):
                    instructor_bonus += 1
        score -= instructor_bonus * 100.0

        # Tertiary: open seats (weight 1)
        total_seats = sum(offering.seats_available or 0 for offering in schedule)
        score -= total_seats * 1.0

        # Tie-break: deterministic by sorted CRNs
        crn_sum = sum(int(o.crn) if o.crn.isdigit() else hash(o.crn) for o in schedule)
        score += (crn_sum % 1000) * 0.001

        return score

    def _compute_total_gaps(self, schedule: List[Offering]) -> int:
        """
        Compute total gap minutes across all days.

        A gap is time between classes on the same day.

        Returns:
            Total gap minutes
        """
        # Group meetings by day
        meetings_by_day: Dict[DayOfWeek, List[Tuple[int, int]]] = defaultdict(list)
        for offering in schedule:
            for meeting in offering.meetings:
                meetings_by_day[meeting.day].append((meeting.start_min, meeting.end_min))

        total_gap = 0
        max_gap = self.request.filters.max_gap_min

        for day, meetings in meetings_by_day.items():
            if len(meetings) <= 1:
                continue

            # Sort by start time
            meetings = sorted(meetings)

            # Compute gaps
            for i in range(len(meetings) - 1):
                gap = meetings[i + 1][0] - meetings[i][1]
                if gap > 0:
                    # If max_gap is set and exceeded, heavily penalize
                    if max_gap and gap > max_gap:
                        total_gap += gap * 10  # Heavily penalize
                    else:
                        total_gap += gap

        return total_gap


def solve_schedules(catalog: List[Offering], request: SolveRequest) -> List[Schedule]:
    """
    Main entry point for schedule solving.

    Args:
        catalog: List of all offerings
        request: Solve request with constraints

    Returns:
        List of valid schedules, sorted by score
    """
    solver = ScheduleSolver(catalog, request)
    return solver.solve()
