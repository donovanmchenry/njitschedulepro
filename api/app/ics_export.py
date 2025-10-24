"""ICS calendar export functionality."""

from datetime import datetime, timedelta
from typing import Dict

from icalendar import Calendar, Event

from app.models import DayOfWeek, Schedule


# Mapping for days to ISO weekday (Monday=0, Sunday=6)
DAY_TO_ISO_WEEKDAY: Dict[DayOfWeek, int] = {
    DayOfWeek.MONDAY: 0,
    DayOfWeek.TUESDAY: 1,
    DayOfWeek.WEDNESDAY: 2,
    DayOfWeek.THURSDAY: 3,
    DayOfWeek.FRIDAY: 4,
    DayOfWeek.SATURDAY: 5,
    DayOfWeek.SUNDAY: 6,
}


def generate_ics(schedule: Schedule, term_start: datetime, term_end: datetime) -> bytes:
    """
    Generate an ICS calendar file for a schedule.

    Args:
        schedule: Schedule with offerings and meetings
        term_start: First day of the term
        term_end: Last day of the term

    Returns:
        ICS file as bytes
    """
    cal = Calendar()
    cal.add("prodid", "-//NJIT Schedule Pro//njitschedulepro.app//")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "NJIT Schedule")
    cal.add("x-wr-timezone", "America/New_York")

    # Generate events for each meeting
    for offering in schedule.offerings:
        for meeting in offering.meetings:
            # Find the first occurrence of this day on or after term_start
            target_iso_weekday = DAY_TO_ISO_WEEKDAY[meeting.day]
            current_date = term_start

            # Adjust to the first occurrence of the target day
            days_ahead = (target_iso_weekday - current_date.weekday()) % 7
            first_occurrence = current_date + timedelta(days=days_ahead)

            # Create event
            event = Event()
            event.add("summary", f"{offering.course_key} - {offering.title}")

            # Build description
            description_parts = [
                f"Course: {offering.course_key}",
                f"Section: {offering.section}",
                f"CRN: {offering.crn}",
            ]
            if offering.instructor:
                description_parts.append(f"Instructor: {offering.instructor}")
            if meeting.location:
                description_parts.append(f"Location: {meeting.location}")
            if offering.credits:
                description_parts.append(f"Credits: {offering.credits}")

            event.add("description", "\n".join(description_parts))

            if meeting.location:
                event.add("location", meeting.location)

            # Calculate start and end datetime for the first occurrence
            start_time = timedelta(minutes=meeting.start_min)
            end_time = timedelta(minutes=meeting.end_min)

            dtstart = datetime.combine(first_occurrence.date(), datetime.min.time()) + start_time
            dtend = datetime.combine(first_occurrence.date(), datetime.min.time()) + end_time

            event.add("dtstart", dtstart)
            event.add("dtend", dtend)

            # Add recurrence rule (repeat weekly until term end)
            event.add("rrule", {"freq": "weekly", "until": term_end})

            # Add UID
            event.add(
                "uid",
                f"{offering.crn}-{meeting.day.value}-{meeting.start_min}@njitschedulepro.app",
            )

            # Add timestamp
            event.add("dtstamp", datetime.now())

            cal.add_component(event)

    return cal.to_ical()
