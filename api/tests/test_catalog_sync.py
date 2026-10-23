"""Snapshot reloads must be complete and preserve the running catalog on failure."""

import gzip
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app import main
from app.catalog_sync import download_catalog, normalize_snapshot


def snapshot(term='202710'):
    return gzip.compress((
        'Term,Course,Title,Section,CRN,Days,Times,Location,Status,Credits\n'
        f'{term},CS 100,Computing,001,10001,M,10:00 AM - 11:20 AM,CKB 101,Open,3\n'
        f'{term},CS 100,Computing,001,10001,W,10:00 AM - 11:20 AM,CKB 101,Open,3\n'
    ).encode())


def test_snapshot_merges_each_sections_meeting_rows():
    offerings = normalize_snapshot(snapshot())
    assert len(offerings) == 1
    assert offerings[0].term == '202710'
    assert len(offerings[0].meetings) == 2


def test_snapshot_rejects_another_semester():
    with pytest.raises(ValueError, match='unexpected semester'):
        normalize_snapshot(snapshot('202695'))


@pytest.mark.asyncio
async def test_revision_is_validated_before_any_network_request():
    with pytest.raises(ValueError, match='commit SHA'):
        await download_catalog('../other-repo')


@pytest.mark.asyncio
async def test_failed_revision_reload_preserves_running_catalog(monkeypatch):
    existing = normalize_snapshot(snapshot())
    monkeypatch.setattr(main, 'catalog', existing)
    monkeypatch.setenv('RELOAD_SECRET', 'test-secret')
    monkeypatch.setattr(main, 'download_catalog', AsyncMock(side_effect=RuntimeError('unavailable')))
    with pytest.raises(HTTPException) as error:
        await main.reload_catalog(x_reload_secret='test-secret', revision='a' * 40)
    assert error.value.status_code == 503
    assert main.catalog is existing
