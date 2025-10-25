"""CSV normalization for NJIT course schedules."""

import re
from typing import Dict, List, Optional

import pandas as pd

from app.models import DayOfWeek, DeliveryMode, Meeting, Offering, Status


# Days parsing map
DAY_MAP = {
    "M": DayOfWeek.MONDAY,
    "T": DayOfWeek.TUESDAY,
    "W": DayOfWeek.WEDNESDAY,
    "R": DayOfWeek.THURSDAY,
    "F": DayOfWeek.FRIDAY,
    "S": DayOfWeek.SATURDAY,
    "U": DayOfWeek.SUNDAY,
}


def parse_days(days_str: str) -> List[DayOfWeek]:
    """
    Parse a day string like 'MW', 'TR', 'MWF', 'TF', 'S' into a list of DayOfWeek.

    Args:
        days_str: String representation of days (e.g., 'MW', 'TR', 'MWF')

    Returns:
        List of DayOfWeek enums
    """
    if not days_str or days_str.strip() == "" or days_str.upper() == "TBA":
        return []

    days_str = days_str.strip().upper()
    result = []

    # Handle special case: Thursday is 'R' not 'T'
    i = 0
    while i < len(days_str):
        char = days_str[i]
        if char in DAY_MAP:
            result.append(DAY_MAP[char])
        i += 1

    return result


def parse_time(time_str: str) -> Optional[int]:
    """
    Parse a time string like '8:30 AM' or '11:20 PM' into minutes from midnight.

    Args:
        time_str: Time string in format 'H:MM AM/PM' or 'HH:MM AM/PM'

    Returns:
        Minutes from midnight (0-1439), or None if unparseable
    """
    if not time_str or time_str.strip() == "" or time_str.upper() == "TBA":
        return None

    time_str = time_str.strip()

    # Match patterns like "8:30 AM", "11:20 PM", "10:00 am"
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)", time_str)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3).upper()

    # Convert to 24-hour format
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0

    # Convert to minutes from midnight
    return hour * 60 + minute


def parse_times(times_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse a times string like '8:30 AM - 9:50 AM' into (start_min, end_min).

    Args:
        times_str: Time range string

    Returns:
        Tuple of (start_minutes, end_minutes) or (None, None) if unparseable
    """
    if not times_str or times_str.strip() == "" or times_str.upper() == "TBA":
        return None, None

    # Split on '-' or 'to'
    parts = re.split(r"\s*-\s*|\s+to\s+", times_str.strip(), maxsplit=1)
    if len(parts) != 2:
        return None, None

    start = parse_time(parts[0])
    end = parse_time(parts[1])

    return start, end


def normalize_status(status_str: str) -> Status:
    """Normalize status field to Status enum."""
    if not status_str:
        return Status.OPEN

    status_str = status_str.strip().lower()
    if "closed" in status_str:
        return Status.CLOSED
    elif "wait" in status_str:
        return Status.WAITLIST
    else:
        return Status.OPEN


def normalize_delivery(delivery_str: str, location: str = "") -> DeliveryMode:
    """
    Normalize delivery mode field.

    Args:
        delivery_str: Delivery mode from CSV
        location: Location field to help infer online/hybrid

    Returns:
        DeliveryMode enum
    """
    if not delivery_str:
        # Try to infer from location
        if location and ("online" in location.lower() or "web" in location.lower()):
            return DeliveryMode.ONLINE
        return DeliveryMode.IN_PERSON

    delivery_str = delivery_str.strip().lower()

    if "online" in delivery_str or "web" in delivery_str or "distance" in delivery_str:
        return DeliveryMode.ONLINE
    elif "hybrid" in delivery_str or "blended" in delivery_str:
        return DeliveryMode.HYBRID
    elif "async" in delivery_str or "asynchronous" in delivery_str:
        return DeliveryMode.ASYNC
    elif "face-to-face" in delivery_str or "in-person" in delivery_str or "in person" in delivery_str:
        return DeliveryMode.IN_PERSON
    else:
        return DeliveryMode.IN_PERSON


def extract_course_key(course_str: str) -> str:
    """
    Extract course key (e.g., 'CS 100', 'PHYS 111A') from course string.

    Args:
        course_str: Course identifier from CSV

    Returns:
        Normalized course key
    """
    if not course_str:
        return ""

    # Extract subject code, catalog number, and optional suffix (like A for labs)
    # Patterns: "CS100", "CS 100", "ACCT115", "PHYS111A", etc.
    match = re.match(r"([A-Z]+)\s*(\d+)([A-Z]*)", course_str.strip().upper())
    if match:
        subject = match.group(1)
        catalog = match.group(2)
        suffix = match.group(3)
        return f"{subject} {catalog}{suffix}"

    return course_str.strip().upper()


def normalize_csv_row(row: pd.Series) -> Optional[Offering]:
    """
    Normalize a single CSV row into an Offering.

    Args:
        row: pandas Series representing one CSV row

    Returns:
        Offering object, or None if row is invalid/unparseable
    """
    try:
        # Extract basic fields
        crn = str(row.get("CRN", "")).strip()
        if not crn:
            return None

        course_raw = str(row.get("Course", "")).strip()
        course_key = extract_course_key(course_raw)
        if not course_key:
            return None

        title = str(row.get("Title", "")).strip()
        section = str(row.get("Section", "")).strip()
        term = str(row.get("Term", "")).strip()

        # Parse days and times
        days_str = str(row.get("Days", "")).strip()
        times_str = str(row.get("Times", "")).strip()

        days = parse_days(days_str)
        start_min, end_min = parse_times(times_str)

        # Build meetings
        meetings: List[Meeting] = []
        if days and start_min is not None and end_min is not None:
            location = str(row.get("Location", "")).strip()
            for day in days:
                meetings.append(
                    Meeting(
                        day=day,
                        start_min=start_min,
                        end_min=end_min,
                        location=location if location else None,
                    )
                )

        # Parse metadata
        status = normalize_status(str(row.get("Status", "")))
        delivery_str = str(row.get("Delivery Mode", ""))
        location_str = str(row.get("Location", ""))
        delivery = normalize_delivery(delivery_str, location_str)

        max_cap = row.get("Max")
        capacity = int(max_cap) if pd.notna(max_cap) and str(max_cap).strip() else None

        now_enrolled = row.get("Now")
        enrolled = int(now_enrolled) if pd.notna(now_enrolled) and str(now_enrolled).strip() else None

        credits_val = row.get("Credits")
        credits = float(credits_val) if pd.notna(credits_val) and str(credits_val).strip() else None

        instructor = str(row.get("Instructor", "")).strip() or None
        info = str(row.get("Info", "")).strip() or None
        comments = str(row.get("Comments", "")).strip() or None

        return Offering(
            crn=crn,
            course_key=course_key,
            section=section,
            title=title,
            term=term if term else None,
            meetings=meetings,
            status=status,
            capacity=capacity,
            enrolled=enrolled,
            instructor=instructor,
            delivery=delivery,
            credits=credits,
            info=info,
            comments=comments,
        )

    except Exception as e:
        # Log error and skip row
        print(f"Error normalizing row: {e}")
        return None


def normalize_csv(file_path: str) -> List[Offering]:
    """
    Read and normalize a single CSV file.

    Args:
        file_path: Path to CSV file

    Returns:
        List of Offering objects
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV {file_path}: {e}")
        return []

    offerings = []
    for _, row in df.iterrows():
        offering = normalize_csv_row(row)
        if offering:
            offerings.append(offering)

    return offerings


def deduplicate_offerings(offerings: List[Offering]) -> List[Offering]:
    """
    Deduplicate offerings by CRN and meeting signature.

    Args:
        offerings: List of offerings that may contain duplicates

    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []

    for offering in offerings:
        # Create signature: CRN + meeting days/times
        meeting_sig = tuple(
            (m.day, m.start_min, m.end_min) for m in sorted(offering.meetings, key=lambda x: (x.day.value, x.start_min))
        )
        sig = (offering.crn, meeting_sig)

        if sig not in seen:
            seen.add(sig)
            unique.append(offering)

    return unique


def merge_offerings_by_crn(offerings: List[Offering]) -> List[Offering]:
    """
    Merge offerings with the same CRN by combining their meetings.

    When a section has multiple rows in the CSV (e.g., meets Tue and Thu separately),
    this merges them into a single offering with all meetings.

    Args:
        offerings: List of offerings that may have duplicate CRNs

    Returns:
        List with offerings merged by CRN
    """
    crn_map: Dict[str, Offering] = {}

    for offering in offerings:
        crn = offering.crn

        if crn not in crn_map:
            # First occurrence of this CRN
            crn_map[crn] = offering
        else:
            # Merge meetings from this offering into the existing one
            existing = crn_map[crn]

            # Add meetings that aren't already present
            for meeting in offering.meetings:
                # Check if this exact meeting already exists
                meeting_exists = any(
                    m.day == meeting.day and
                    m.start_min == meeting.start_min and
                    m.end_min == meeting.end_min
                    for m in existing.meetings
                )

                if not meeting_exists:
                    existing.meetings.append(meeting)

    return list(crn_map.values())


def normalize_multiple_csvs(file_paths: List[str]) -> List[Offering]:
    """
    Normalize multiple CSV files and merge into a single catalog.

    Args:
        file_paths: List of CSV file paths

    Returns:
        Combined and deduplicated list of offerings
    """
    all_offerings = []

    for path in file_paths:
        offerings = normalize_csv(path)
        all_offerings.extend(offerings)

    # Merge offerings with same CRN (sections with multiple meeting times)
    merged = merge_offerings_by_crn(all_offerings)

    # Deduplicate any remaining duplicates
    return deduplicate_offerings(merged)
