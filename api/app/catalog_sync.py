"""Load the same immutable catalog revision that the frontend pipeline published."""

import gzip
import asyncio
import re
import tempfile
from pathlib import Path

import httpx

from app.models import Offering
from app.normalizer import normalize_multiple_csvs
from app.terms import SPRING_2027_TERM


def normalize_snapshot(payload: bytes) -> list[Offering]:
    contents = gzip.decompress(payload)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'catalog.csv'
        path.write_bytes(contents)
        offerings = normalize_multiple_csvs([str(path)])
    if not offerings or {item.term for item in offerings} != {SPRING_2027_TERM}:
        raise ValueError('Downloaded catalog is empty or contains an unexpected semester')
    return offerings


async def download_catalog(revision: str) -> list[Offering]:
    if revision != 'main' and not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Catalog revision must be a full Git commit SHA')
    url = f'https://raw.githubusercontent.com/donovanmchenry/njitschedulepro/{revision}/web/public/catalog/catalog.csv.gz'
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    return await asyncio.to_thread(normalize_snapshot, response.content)
