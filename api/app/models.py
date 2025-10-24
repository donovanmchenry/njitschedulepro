"""Data models for NJIT Schedule Pro."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DayOfWeek(str, Enum):
    """Days of the week."""

    MONDAY = "Mon"
    TUESDAY = "Tue"
    WEDNESDAY = "Wed"
    THURSDAY = "Thu"
    FRIDAY = "Fri"
    SATURDAY = "Sat"
    SUNDAY = "Sun"


class Status(str, Enum):
    """Course section status."""

    OPEN = "Open"
    CLOSED = "Closed"
    WAITLIST = "Waitlist"


class DeliveryMode(str, Enum):
    """Course delivery mode."""

    IN_PERSON = "In-Person"
    ONLINE = "Online"
    HYBRID = "Hybrid"
    ASYNC = "Async"


class Meeting(BaseModel):
    """A single class meeting occurrence."""

    day: DayOfWeek
    start_min: int = Field(..., description="Start time in minutes from midnight (0-1439)")
    end_min: int = Field(..., description="End time in minutes from midnight (0-1439)")
    location: Optional[str] = None

    def overlaps(self, other: "Meeting") -> bool:
        """Check if this meeting overlaps with another on the same day."""
        if self.day != other.day:
            return False
        return not (self.end_min <= other.start_min or self.start_min >= other.end_min)

    def conflicts_with_unavailable(
        self, unavailable_start: int, unavailable_end: int
    ) -> tuple[bool, int]:
        """
        Check if meeting conflicts with an unavailable time block.

        Returns:
            (conflicts, overlap_minutes): Whether there's a conflict and minutes of overlap
        """
        if self.end_min <= unavailable_start or self.start_min >= unavailable_end:
            return False, 0

        overlap_start = max(self.start_min, unavailable_start)
        overlap_end = min(self.end_min, unavailable_end)
        overlap_minutes = overlap_end - overlap_start
        return True, overlap_minutes


class Offering(BaseModel):
    """A course section offering with all metadata."""

    crn: str = Field(..., description="Unique Course Reference Number")
    course_key: str = Field(..., description="Subject + catalog number (e.g., 'ACCT 115')")
    section: str = Field(..., description="Section identifier")
    title: str
    term: Optional[str] = None
    meetings: List[Meeting] = Field(default_factory=list, description="All meetings for this section")
    status: Status = Status.OPEN
    capacity: Optional[int] = None
    enrolled: Optional[int] = None
    instructor: Optional[str] = None
    delivery: DeliveryMode = DeliveryMode.IN_PERSON
    credits: Optional[float] = None
    info: Optional[str] = None
    comments: Optional[str] = None

    @property
    def seats_available(self) -> Optional[int]:
        """Calculate available seats."""
        if self.capacity is not None and self.enrolled is not None:
            return max(0, self.capacity - self.enrolled)
        return None

    @property
    def is_honors(self) -> bool:
        """Check if this is an honors section (section starts with H)."""
        return self.section.upper().startswith('H')

    def overlaps_with(self, other: "Offering") -> bool:
        """Check if any meeting in this offering overlaps with another offering."""
        for m1 in self.meetings:
            for m2 in other.meetings:
                if m1.overlaps(m2):
                    return True
        return False


class AvailabilityBlock(BaseModel):
    """Time block when student is unavailable."""

    day: DayOfWeek
    start_min: int = Field(..., ge=0, lt=1440)
    end_min: int = Field(..., ge=0, le=1440)


class ScheduleFilters(BaseModel):
    """Optional filters for schedule generation."""

    status: List[Status] = Field(default_factory=lambda: [Status.OPEN])
    delivery: Optional[List[DeliveryMode]] = None
    campus_include: Optional[List[str]] = None
    campus_exclude: Optional[List[str]] = None
    avoid_instructors: Optional[List[str]] = None
    prefer_instructors: Optional[List[str]] = None
    earliest_start: Optional[int] = Field(None, ge=0, lt=1440)
    latest_end: Optional[int] = Field(None, ge=0, le=1440)
    max_gap_min: Optional[int] = Field(None, ge=0)
    include_honors: bool = Field(default=True, description="Include honors sections")
    include_non_honors: bool = Field(default=True, description="Include non-honors sections")


class SolveRequest(BaseModel):
    """Request to generate schedules."""

    required_course_keys: List[str] = Field(..., min_length=1)
    optional_course_keys: Optional[List[str]] = None
    min_credits: Optional[float] = None
    max_credits: Optional[float] = None
    unavailable: List[AvailabilityBlock] = Field(default_factory=list)
    filters: ScheduleFilters = Field(default_factory=ScheduleFilters)
    max_results: int = Field(default=500, ge=1, le=2000)


class Schedule(BaseModel):
    """A generated schedule with offerings and metadata."""

    offerings: List[Offering]
    total_credits: float
    score: float = Field(
        ..., description="Lower is better; primary: gaps, instructor prefs, etc."
    )

    def __hash__(self):
        """Hash by sorted CRNs for deduplication."""
        return hash(tuple(sorted(o.crn for o in self.offerings)))

    def __eq__(self, other):
        """Equal if same set of CRNs."""
        if not isinstance(other, Schedule):
            return False
        return set(o.crn for o in self.offerings) == set(o.crn for o in other.offerings)


class SolveResponse(BaseModel):
    """Response from schedule generation."""

    schedules: List[Schedule]
    count: int
    catalog_course_count: int
    catalog_section_count: int
