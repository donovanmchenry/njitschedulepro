"""RateMyProfessor integration — fetches professor ratings for NJIT instructors."""

import asyncio
from typing import Optional

import httpx

# NJIT school ID on RateMyProfessors (base64 of "School-668")
NJIT_SCHOOL_ID = "U2Nob29sLTY2OA=="

RMP_URL = "https://www.ratemyprofessors.com/graphql"
RMP_HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "User-Agent": "Mozilla/5.0 (compatible; NJITSchedulePro/1.0)",
    "Content-Type": "application/json",
}

_SEARCH_QUERY = """
query TeacherSearch($query: TeacherSearchQuery!) {
  newSearch {
    teachers(query: $query, first: 3) {
      edges {
        node {
          firstName
          lastName
          avgRating
          numRatings
          wouldTakeAgainPercent
          department
        }
      }
    }
  }
}
"""

# Module-level cache: name → result dict or None
# None means "looked up, no match found" — avoids repeated misses
_cache: dict[str, Optional[dict]] = {}


def _normalize_name(catalog_name: str) -> str:
    """Convert catalog format 'Last, First M.' to 'First M. Last' for RMP search."""
    if "," in catalog_name:
        parts = catalog_name.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return catalog_name


async def fetch_professor_rating(name: str) -> Optional[dict]:
    """
    Fetch a single professor's RMP rating. Returns None if not found or on any error.
    Results are cached for the lifetime of the process.
    """
    if name in _cache:
        return _cache[name]

    try:
        normalized = _normalize_name(name)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                RMP_URL,
                headers=RMP_HEADERS,
                json={
                    "query": _SEARCH_QUERY,
                    "variables": {
                        "query": {
                            "text": normalized,
                            "schoolID": NJIT_SCHOOL_ID,
                        }
                    },
                },
            )

        data = resp.json()
        edges = data["data"]["newSearch"]["teachers"]["edges"]
        if not edges:
            _cache[name] = None
            return None

        node = edges[0]["node"]
        result = {
            "avg_rating": node["avgRating"],
            "num_ratings": node["numRatings"],
            "would_take_again": node["wouldTakeAgainPercent"],
        }
        _cache[name] = result
        return result

    except Exception:
        # Never cached on error so a transient failure allows a future retry
        return None


async def batch_fetch_ratings(names: list[str]) -> dict[str, Optional[dict]]:
    """Fetch ratings for multiple instructors concurrently."""
    results = await asyncio.gather(*[fetch_professor_rating(n) for n in names])
    return dict(zip(names, results))
