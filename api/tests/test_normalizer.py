"""Tests for CSV normalization."""

import pandas as pd
import pytest

from app.models import DayOfWeek, DeliveryMode, Status
from app.normalizer import (
    deduplicate_offerings,
    extract_course_key,
    normalize_csv_row,
    normalize_delivery,
    normalize_status,
    parse_days,
    parse_time,
    parse_times,
)


class TestParseDays:
    """Tests for parse_days function."""

    def test_monday_wednesday(self):
        assert parse_days("MW") == [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]

    def test_tuesday_thursday(self):
        # 'R' represents Thursday
        assert parse_days("TR") == [DayOfWeek.TUESDAY, DayOfWeek.THURSDAY]

    def test_monday_wednesday_friday(self):
        assert parse_days("MWF") == [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY]

    def test_tuesday_friday(self):
        assert parse_days("TF") == [DayOfWeek.TUESDAY, DayOfWeek.FRIDAY]

    def test_saturday(self):
        assert parse_days("S") == [DayOfWeek.SATURDAY]

    def test_monday_thursday(self):
        assert parse_days("MR") == [DayOfWeek.MONDAY, DayOfWeek.THURSDAY]

    def test_empty_string(self):
        assert parse_days("") == []

    def test_tba(self):
        assert parse_days("TBA") == []

    def test_lowercase(self):
        assert parse_days("mw") == [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]


class TestParseTime:
    """Tests for parse_time function."""

    def test_morning_time(self):
        assert parse_time("8:30 AM") == 8 * 60 + 30  # 510 minutes

    def test_afternoon_time(self):
        assert parse_time("2:45 PM") == 14 * 60 + 45  # 885 minutes

    def test_noon(self):
        assert parse_time("12:00 PM") == 12 * 60  # 720 minutes

    def test_midnight(self):
        assert parse_time("12:00 AM") == 0

    def test_evening_time(self):
        assert parse_time("11:20 PM") == 23 * 60 + 20  # 1400 minutes

    def test_lowercase_am_pm(self):
        assert parse_time("8:30 am") == 8 * 60 + 30

    def test_tba(self):
        assert parse_time("TBA") is None

    def test_empty_string(self):
        assert parse_time("") is None


class TestParseTimes:
    """Tests for parse_times function."""

    def test_morning_class(self):
        start, end = parse_times("8:30 AM - 9:50 AM")
        assert start == 8 * 60 + 30  # 510
        assert end == 9 * 60 + 50  # 590

    def test_afternoon_class(self):
        start, end = parse_times("2:30 PM - 3:50 PM")
        assert start == 14 * 60 + 30  # 870
        assert end == 15 * 60 + 50  # 950

    def test_evening_class(self):
        start, end = parse_times("6:00 PM - 8:50 PM")
        assert start == 18 * 60  # 1080
        assert end == 20 * 60 + 50  # 1250

    def test_tba(self):
        start, end = parse_times("TBA")
        assert start is None
        assert end is None

    def test_empty_string(self):
        start, end = parse_times("")
        assert start is None
        assert end is None


class TestNormalizeStatus:
    """Tests for normalize_status function."""

    def test_open(self):
        assert normalize_status("Open") == Status.OPEN

    def test_closed(self):
        assert normalize_status("Closed") == Status.CLOSED

    def test_waitlist(self):
        assert normalize_status("Waitlist") == Status.WAITLIST

    def test_case_insensitive(self):
        assert normalize_status("CLOSED") == Status.CLOSED
        assert normalize_status("waitlist") == Status.WAITLIST

    def test_empty_defaults_to_open(self):
        assert normalize_status("") == Status.OPEN


class TestNormalizeDelivery:
    """Tests for normalize_delivery function."""

    def test_face_to_face(self):
        assert normalize_delivery("Face-to-Face") == DeliveryMode.IN_PERSON

    def test_online(self):
        assert normalize_delivery("Online") == DeliveryMode.ONLINE

    def test_hybrid(self):
        assert normalize_delivery("Hybrid") == DeliveryMode.HYBRID

    def test_async(self):
        assert normalize_delivery("Asynchronous Online") == DeliveryMode.ASYNC

    def test_infer_from_location(self):
        assert normalize_delivery("", "Online Platform") == DeliveryMode.ONLINE

    def test_case_insensitive(self):
        assert normalize_delivery("ONLINE") == DeliveryMode.ONLINE


class TestExtractCourseKey:
    """Tests for extract_course_key function."""

    def test_with_space(self):
        assert extract_course_key("CS 100") == "CS 100"

    def test_without_space(self):
        assert extract_course_key("CS100") == "CS 100"

    def test_multiple_letters(self):
        assert extract_course_key("ACCT115") == "ACCT 115"
        assert extract_course_key("ARCH 196") == "ARCH 196"

    def test_lowercase(self):
        assert extract_course_key("cs100") == "CS 100"


class TestNormalizeCSVRow:
    """Tests for normalize_csv_row function."""

    def test_basic_row(self):
        row = pd.Series(
            {
                "Term": "202610",
                "Course": "CS100",
                "Title": "ROADMAP TO COMPUTING",
                "Section": "002",
                "CRN": "11757",
                "Days": "MW",
                "Times": "11:30 AM - 12:50 PM",
                "Location": "CKB 217",
                "Status": "Open",
                "Max": "80",
                "Now": "0",
                "Instructor": "Spirollari, Junilda",
                "Delivery Mode": "Face-to-Face",
                "Credits": "3",
                "Info": "",
                "Comments": "",
            }
        )

        offering = normalize_csv_row(row)
        assert offering is not None
        assert offering.crn == "11757"
        assert offering.course_key == "CS 100"
        assert offering.section == "002"
        assert offering.title == "ROADMAP TO COMPUTING"
        assert offering.term == "202610"
        assert len(offering.meetings) == 2  # Monday and Wednesday
        assert offering.meetings[0].day == DayOfWeek.MONDAY
        assert offering.meetings[0].start_min == 11 * 60 + 30
        assert offering.meetings[0].end_min == 12 * 60 + 50
        assert offering.status == Status.OPEN
        assert offering.capacity == 80
        assert offering.enrolled == 0
        assert offering.delivery == DeliveryMode.IN_PERSON
        assert offering.credits == 3.0

    def test_tba_times(self):
        row = pd.Series(
            {
                "Term": "202610",
                "Course": "CS101",
                "Title": "TEST COURSE",
                "Section": "HS1",
                "CRN": "15862",
                "Days": "",
                "Times": "TBA",
                "Location": "",
                "Status": "Closed",
                "Max": "0",
                "Now": "0",
                "Instructor": "",
                "Delivery Mode": "Face-to-Face",
                "Credits": "3",
                "Info": "",
                "Comments": "",
            }
        )

        offering = normalize_csv_row(row)
        assert offering is not None
        assert offering.crn == "15862"
        assert len(offering.meetings) == 0  # TBA = no meetings
        assert offering.status == Status.CLOSED

    def test_thursday_friday(self):
        row = pd.Series(
            {
                "Term": "202610",
                "Course": "CS100",
                "Title": "TEST",
                "Section": "010",
                "CRN": "11761",
                "Days": "TF",
                "Times": "1:00 PM - 2:20 PM",
                "Location": "CKB 124",
                "Status": "Open",
                "Max": "43",
                "Now": "0",
                "Instructor": "Nemane, Nikita",
                "Delivery Mode": "Face-to-Face",
                "Credits": "3",
                "Info": "",
                "Comments": "",
            }
        )

        offering = normalize_csv_row(row)
        assert offering is not None
        assert len(offering.meetings) == 2
        assert offering.meetings[0].day == DayOfWeek.TUESDAY
        assert offering.meetings[1].day == DayOfWeek.FRIDAY

    def test_invalid_row_no_crn(self):
        row = pd.Series(
            {
                "Term": "202610",
                "Course": "CS100",
                "Title": "TEST",
                "Section": "002",
                "CRN": "",  # Missing CRN
                "Days": "MW",
                "Times": "11:30 AM - 12:50 PM",
                "Location": "CKB 217",
                "Status": "Open",
                "Max": "80",
                "Now": "0",
                "Instructor": "",
                "Delivery Mode": "Face-to-Face",
                "Credits": "3",
                "Info": "",
                "Comments": "",
            }
        )

        offering = normalize_csv_row(row)
        assert offering is None


class TestDeduplicateOfferings:
    """Tests for deduplicate_offerings function."""

    def test_removes_duplicates(self):
        # Create mock offerings with duplicate CRN + meetings
        from app.models import Meeting, Offering

        offering1 = Offering(
            crn="12345",
            course_key="CS 100",
            section="002",
            title="Test",
            meetings=[
                Meeting(day=DayOfWeek.MONDAY, start_min=600, end_min=720),
                Meeting(day=DayOfWeek.WEDNESDAY, start_min=600, end_min=720),
            ],
        )

        offering2 = Offering(
            crn="12345",
            course_key="CS 100",
            section="002",
            title="Test",
            meetings=[
                Meeting(day=DayOfWeek.MONDAY, start_min=600, end_min=720),
                Meeting(day=DayOfWeek.WEDNESDAY, start_min=600, end_min=720),
            ],
        )

        offering3 = Offering(
            crn="67890",
            course_key="CS 200",
            section="004",
            title="Test 2",
            meetings=[Meeting(day=DayOfWeek.TUESDAY, start_min=600, end_min=720)],
        )

        result = deduplicate_offerings([offering1, offering2, offering3])
        assert len(result) == 2
        assert result[0].crn in ["12345", "67890"]
        assert result[1].crn in ["12345", "67890"]
