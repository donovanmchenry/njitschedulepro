"""A stale API must never solve a request for a different browser semester."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request, Response

from app import main
from app.models import Offering, SolveRequest


@pytest.mark.asyncio
async def test_stale_api_rejects_browser_semester(monkeypatch):
    monkeypatch.setattr(main, 'acquire_solve_request', AsyncMock())
    monkeypatch.setattr(main, 'catalog', [Offering(
        course_key='CS 100', crn='95065', section='W01', title='Computing',
        term='202695', meetings=[],
    )])
    monkeypatch.setattr(main, 'catalog_metadata', {'terms': ['202695']})
    request = Request({'type': 'http', 'client': ('127.0.0.1', 1234)})
    with pytest.raises(HTTPException) as error:
        await main.solve(SolveRequest(term='202710', required_course_keys=['CS 100']), request, Response())
    assert error.value.status_code == 409
