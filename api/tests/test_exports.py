"""Tests for schedule exports."""

import csv
import io

import pytest
from fastapi import HTTPException

from app import main as main_module
from app.main import _schedule_to_csv, create_share, get_share
from app.models import DayOfWeek, Meeting, Offering, Schedule


def test_csv_preserves_each_meeting_and_njit_day_codes():
    schedule = Schedule(
        offerings=[
            Offering(
                crn="91901",
                course_key="CS 114",
                section="001",
                title="Computer Science II",
                credits=3,
                meetings=[
                    Meeting(day=DayOfWeek.THURSDAY, start_min=600, end_min=680, location="CKB 204"),
                    Meeting(day=DayOfWeek.SUNDAY, start_min=720, end_min=780, location="GITC 1100"),
                ],
            )
        ],
        total_credits=3,
        score=0,
    )

    rows = list(csv.DictReader(io.StringIO(_schedule_to_csv(schedule))))

    assert [row["Days"] for row in rows] == ["R", "U"]
    assert [row["Times"] for row in rows] == ["10:00 AM - 11:20 AM", "12:00 PM - 1:00 PM"]
    assert [row["Location"] for row in rows] == ["CKB 204", "GITC 1100"]


@pytest.mark.asyncio
async def test_share_token_rebuilds_schedule_from_catalog(monkeypatch):
    offering = Offering(
        crn="91901",
        course_key="CS 114",
        section="001",
        title="Computer Science II",
        credits=3,
        meetings=[],
    )
    schedule = Schedule(offerings=[offering], total_credits=3, score=12)
    monkeypatch.setattr(main_module, "catalog", [offering])

    share_id = (await create_share(schedule))["id"]
    restored = await get_share(share_id)

    assert [item.crn for item in restored.offerings] == ["91901"]
    assert restored.total_credits == 3


@pytest.mark.asyncio
async def test_share_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        await get_share("not!valid")

    assert exc_info.value.status_code == 404
