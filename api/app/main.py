"""FastAPI main application."""

import asyncio
import base64
import binascii
import csv
import glob
import hashlib
import io
import json
import logging
import os
import re
import time as _time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.ai_parser import AIParseRequest, AIParseResponse, parse_natural_language
from app.ics_export import generate_ics
from app.models import Offering, Schedule, SolveRequest, SolveResponse
from app.normalizer import normalize_csv, normalize_multiple_csvs
from app.performance import AsyncTTLCache
from app.rmp import batch_fetch_ratings
from app.shared_rate_limiter import (
    RateLimitExceededError,
    RateLimitUnavailableError,
    acquire_ai_request,
    acquire_solve_request,
    get_global_stats,
    get_rate_limiter_health,
    get_usage_stats,
    record_ai_tokens,
)
from app.solver import build_offering_masks, solve_schedules

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load the current catalog before serving traffic."""
    global catalog, catalog_metadata
    catalog, catalog_metadata = _load_catalog_from_disk()
    _rebuild_catalog_indexes()
    yield


app = FastAPI(
    title="NJIT Schedule Pro API",
    description="Backend API for course schedule generation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_performance_headers(request: Request, call_next):
    """Expose end-to-end API time to browsers and production diagnostics."""
    started = _time.perf_counter()
    response = await call_next(request)
    duration_ms = (_time.perf_counter() - started) * 1000
    existing_timing = response.headers.get("Server-Timing")
    app_timing = f"app;dur={duration_ms:.1f}"
    response.headers["Server-Timing"] = (
        f"{existing_timing}, {app_timing}" if existing_timing else app_timing
    )
    response.headers["Timing-Allow-Origin"] = "*"
    response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
    return response

# CORS middleware for frontend access
default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [
        origin.strip().rstrip("/") for origin in allowed_origins_env.split(",") if origin.strip()
    ]
    # Always include local development defaults
    allowed_origins.extend(default_origins)
else:
    allowed_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["ETag", "Server-Timing", "X-Response-Time", "X-Schedule-Cache"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

# In-memory catalog storage (can be replaced with database)
catalog: List[Offering] = []
catalog_metadata: Dict = {}
catalog_by_course: Dict[str, List[Offering]] = {}
catalog_by_crn: Dict[str, Offering] = {}
catalog_offering_masks: Dict[str, int] = {}
catalog_course_summaries: List[dict] = []
catalog_version = "empty"
_catalog_index_bytes = b'{"version":"empty","courses":[],"total":0}'
_catalog_index_etag = '"empty"'
_catalog_subject_bytes: Dict[str, bytes] = {}
_catalog_subject_etags: Dict[str, str] = {}

_solve_cache = AsyncTTLCache[SolveResponse](max_entries=64, ttl_seconds=300)
_ai_cache = AsyncTTLCache[AIParseResponse](max_entries=256, ttl_seconds=3600)
_solve_semaphore = asyncio.Semaphore(max(1, int(os.getenv("SOLVE_CONCURRENCY", "1"))))

# Prerequisites cache: normalized course_key → prereq text or None
_prereqs_cache: Dict[str, Optional[str]] = {}

class RatingsRequest(BaseModel):
    names: List[str]


class PrerequisitesRequest(BaseModel):
    course_keys: List[str]


def _section_summary(offering: Offering) -> dict:
    return {
        "crn": offering.crn,
        "section": offering.section,
        "status": offering.status.value,
        "delivery": offering.delivery.value,
        "instructor": offering.instructor,
        "credits": offering.credits,
    }


def _rebuild_catalog_indexes() -> None:
    """Build immutable lookup and response structures once per catalog version."""
    global catalog_by_course, catalog_by_crn, catalog_offering_masks, catalog_course_summaries
    global catalog_version, _catalog_index_bytes, _catalog_index_etag
    global _catalog_subject_bytes, _catalog_subject_etags

    by_course: dict[str, list[Offering]] = defaultdict(list)
    by_crn: dict[str, Offering] = {}
    for offering in catalog:
        by_course[offering.course_key].append(offering)
        by_crn[offering.crn] = offering

    summaries: list[dict] = []
    subjects: dict[str, list[dict]] = defaultdict(list)
    for course_key in sorted(by_course):
        offerings = by_course[course_key]
        subject = course_key.split(" ", 1)[0]
        open_count = sum(offering.status.value == "Open" for offering in offerings)
        summary = {
            "course_key": course_key,
            "title": offerings[0].title,
            "subject": subject,
            "section_count": len(offerings),
            "open_section_count": open_count,
        }
        summaries.append(summary)
        subjects[subject].append(
            {
                **summary,
                "sections": [_section_summary(offering) for offering in offerings],
            }
        )

    # Include section-level data so cache keys change when seats, status, or instructors change.
    digest_source = json.dumps(subjects, sort_keys=True, separators=(",", ":")).encode()
    version = hashlib.sha256(digest_source).hexdigest()[:16]
    index_payload = {
        "version": version,
        "courses": summaries,
        "total": len(summaries),
    }
    subject_bytes: dict[str, bytes] = {}
    subject_etags: dict[str, str] = {}
    for subject, courses in subjects.items():
        raw = json.dumps(
            {"version": version, "subject": subject, "courses": courses},
            separators=(",", ":"),
        ).encode()
        subject_bytes[subject] = raw
        subject_etags[subject] = f'"{hashlib.sha256(raw).hexdigest()[:16]}"'

    catalog_by_course = dict(by_course)
    catalog_by_crn = by_crn
    catalog_offering_masks = build_offering_masks(catalog)
    catalog_course_summaries = summaries
    catalog_version = version
    _catalog_index_bytes = json.dumps(index_payload, separators=(",", ":")).encode()
    _catalog_index_etag = f'"{version}"'
    _catalog_subject_bytes = subject_bytes
    _catalog_subject_etags = subject_etags
    catalog_metadata["version"] = version


def _catalog_cache_headers(etag: str) -> dict[str, str]:
    return {
        "Cache-Control": "public, max-age=300, s-maxage=300, stale-while-revalidate=86400",
        "ETag": etag,
    }


def _get_courseschedules_dir() -> str:
    """Resolve the courseschedules directory, checking the mounted volume path first."""
    # Docker volume mounts courseschedules to /app/courseschedules
    volume_path = "/app/courseschedules"
    if os.path.exists(volume_path):
        return volume_path
    # Fallback: parent of cwd (when running from api/ locally)
    parent_dir = os.path.dirname(os.getcwd())
    parent_path = os.path.join(parent_dir, "courseschedules")
    if os.path.exists(parent_path):
        return parent_path
    return os.path.join(os.getcwd(), "courseschedules")


def _load_catalog_from_disk() -> tuple[List[Offering], Dict]:
    """Read all CSVs from the courseschedules directory and return offerings + metadata."""
    courseschedules_dir = _get_courseschedules_dir()
    if not os.path.exists(courseschedules_dir):
        return [], {}
    csv_files = glob.glob(os.path.join(courseschedules_dir, "*.csv"))
    if not csv_files:
        return [], {}
    print(f"Loading {len(csv_files)} CSV files from {courseschedules_dir}...")
    offerings = normalize_multiple_csvs(csv_files)
    metadata = {
        "loaded_at": datetime.now().isoformat(),
        "file_count": len(csv_files),
        "offering_count": len(offerings),
    }
    print(f"Loaded {len(offerings)} offerings from {len(csv_files)} files")
    return offerings, metadata


@app.get("/")
async def root():
    """Health check endpoint."""
    limiter_health = await get_rate_limiter_health()
    return {
        "status": "healthy",
        "service": "NJIT Schedule Pro API",
        "version": "1.0.0",
        "catalog_loaded": len(catalog) > 0,
        "catalog_size": len(catalog),
        "rate_limiting": limiter_health,
    }


@app.post("/reload")
async def reload_catalog(x_reload_secret: Optional[str] = Header(default=None)):
    """
    Reload the course catalog from disk without restarting the server.
    If the RELOAD_SECRET env var is set, the X-Reload-Secret header must match it.
    """
    global catalog, catalog_metadata

    reload_secret = os.getenv("RELOAD_SECRET")
    if reload_secret and x_reload_secret != reload_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Reload-Secret header")

    catalog, catalog_metadata = _load_catalog_from_disk()
    _rebuild_catalog_indexes()
    await _solve_cache.clear()
    await _ai_cache.clear()
    return {
        "status": "reloaded",
        "offering_count": len(catalog),
        "loaded_at": catalog_metadata.get("loaded_at"),
    }


@app.post("/ingest/csv")
async def ingest_csv(file: UploadFile = File(...)):
    """
    Ingest a single CSV file and add to catalog.

    Args:
        file: CSV file upload

    Returns:
        Status and updated catalog info
    """
    global catalog, catalog_metadata

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Save temporarily
        temp_path = f"/tmp/{file.filename}"
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)

        # Normalize
        new_offerings = normalize_csv(temp_path)

        # Add to catalog (with deduplication by CRN)
        existing_crns = {o.crn for o in catalog}
        added = 0
        for offering in new_offerings:
            if offering.crn not in existing_crns:
                catalog.append(offering)
                existing_crns.add(offering.crn)
                added += 1

        catalog_metadata = {
            "updated_at": datetime.now().isoformat(),
            "offering_count": len(catalog),
        }
        _rebuild_catalog_indexes()
        await _solve_cache.clear()
        await _ai_cache.clear()

        # Clean up
        os.remove(temp_path)

        return {
            "status": "success",
            "filename": file.filename,
            "new_offerings": len(new_offerings),
            "added_to_catalog": added,
            "total_catalog_size": len(catalog),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.get("/catalog")
async def get_catalog(
    course_key: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get catalog of offerings with optional filtering.

    Args:
        course_key: Filter by specific course key (e.g., 'CS 100')
        search: Search in course key or title
        limit: Max results to return
        offset: Pagination offset

    Returns:
        List of offerings and metadata
    """
    filtered = catalog

    if course_key:
        filtered = [o for o in filtered if o.course_key.lower() == course_key.lower()]

    if search:
        search_lower = search.lower()
        filtered = [
            o
            for o in filtered
            if search_lower in o.course_key.lower() or search_lower in o.title.lower()
        ]

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "offerings": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "unique_courses": catalog_course_summaries,
        "metadata": catalog_metadata,
    }


@app.get("/catalog/courses")
async def get_courses(request: Request, search: Optional[str] = None):
    """Return the small course index; section details are loaded by subject."""
    if not search:
        headers = _catalog_cache_headers(_catalog_index_etag)
        if request.headers.get("if-none-match") == _catalog_index_etag:
            return Response(status_code=304, headers=headers)
        return Response(content=_catalog_index_bytes, media_type="application/json", headers=headers)

    search_lower = search.lower()
    courses = [
        course
        for course in catalog_course_summaries
        if search_lower in course["course_key"].lower()
        or search_lower in course["title"].lower()
    ]
    return {"version": catalog_version, "courses": courses, "total": len(courses)}


@app.get("/catalog/subjects/{subject}")
async def get_subject_courses(subject: str, request: Request):
    """Return section details for one subject, cached as immutable serialized JSON."""
    normalized_subject = subject.strip().upper()
    raw = _catalog_subject_bytes.get(normalized_subject)
    if raw is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    etag = _catalog_subject_etags[normalized_subject]
    headers = _catalog_cache_headers(etag)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=raw, media_type="application/json", headers=headers)


@app.get("/catalog/courses/{course_key:path}/sections")
async def get_course_sections(course_key: str):
    """Small API fallback for clients that cannot load the static subject chunk."""
    normalized_key = course_key.strip().upper()
    offerings = catalog_by_course.get(normalized_key)
    if not offerings:
        raise HTTPException(status_code=404, detail="Course not found")
    return {
        "version": catalog_version,
        "course_key": normalized_key,
        "sections": [_section_summary(offering) for offering in offerings],
    }


@app.post("/solve", response_model=SolveResponse)
async def solve(request_body: SolveRequest, request: Request, response: Response):
    """
    Generate schedules based on constraints.

    Args:
        request_body: Solve request with constraints
        request: FastAPI request object (for rate limiting)

    Returns:
        List of valid schedules
    """
    client_ip = request.client.host if request.client else "unknown"
    try:
        await acquire_solve_request(client_ip)
    except RateLimitExceededError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers=headers,
        )
    except RateLimitUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not catalog:
        raise HTTPException(
            status_code=400, detail="Catalog is empty. Please ingest CSV files first."
        )

    # Validate required courses exist using the precomputed catalog indexes.
    catalog_course_keys = catalog_by_course.keys()
    missing = [ck for ck in request_body.required_course_keys if ck not in catalog_course_keys]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Required courses not found in catalog: {', '.join(missing)}"
        )

    missing_group_courses = {
        course_key
        for group in request_body.course_choice_groups
        for course_key in group.eligible_course_keys
        if course_key not in catalog_course_keys
    }
    if missing_group_courses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Requirement courses not found in catalog: "
                + ", ".join(sorted(missing_group_courses))
            ),
        )

    missing_crns = [crn for crn in request_body.required_crns if crn not in catalog_by_crn]
    if missing_crns:
        raise HTTPException(
            status_code=400, detail=f"Required CRNs not found in catalog: {', '.join(missing_crns)}"
        )

    cache_key = hashlib.sha256(
        f"{catalog_version}:{request_body.model_dump_json()}".encode()
    ).hexdigest()
    # Large custom API responses are deliberately not retained on the 512 MB instance.
    should_cache = request_body.max_results <= 100
    cached = await _solve_cache.get(cache_key) if should_cache else None
    if cached is not None:
        response.headers["X-Schedule-Cache"] = "HIT"
        response.headers["Server-Timing"] = "solve;dur=0;desc=cache-hit"
        return cached

    started = _time.perf_counter()
    async with _solve_semaphore:
        # Recheck after queueing so identical concurrent requests only solve once.
        cached = await _solve_cache.get(cache_key) if should_cache else None
        if cached is not None:
            response.headers["X-Schedule-Cache"] = "HIT"
            response.headers["Server-Timing"] = "solve;dur=0;desc=cache-hit-after-wait"
            return cached
        schedules = await run_in_threadpool(
            solve_schedules,
            catalog,
            request_body,
            catalog_by_course,
            catalog_by_crn,
            catalog_offering_masks,
        )
    duration_ms = (_time.perf_counter() - started) * 1000
    result = SolveResponse(
        schedules=schedules,
        count=len(schedules),
        catalog_course_count=len(catalog_by_course),
        catalog_section_count=len(catalog),
    )
    if should_cache:
        await _solve_cache.set(cache_key, result)
    response.headers["X-Schedule-Cache"] = "MISS"
    response.headers["Server-Timing"] = f"solve;dur={duration_ms:.1f}"
    logger.info(
        "schedule_solve duration_ms=%.1f results=%s requested_results=%s cache=miss",
        duration_ms,
        len(schedules),
        request_body.max_results,
    )
    return result


@app.post("/ai/parse-schedule")
async def ai_parse_schedule(parse_request: AIParseRequest, request: Request):
    """
    Parse natural language schedule description into structured constraints using AI.

    Args:
        parse_request: Contains the student's schedule description
        request: FastAPI request object (for IP address)

    Returns:
        Parsed constraints and usage information
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    try:
        usage_stats = await acquire_ai_request(client_ip)
    except RateLimitExceededError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        raise HTTPException(status_code=429, detail=str(exc), headers=headers)
    except RateLimitUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    normalized_prompt = " ".join(parse_request.prompt.lower().split())
    cache_key = hashlib.sha256(f"{catalog_version}:{normalized_prompt}".encode()).hexdigest()
    cached = await _ai_cache.get(cache_key)
    if cached is not None:
        return {
            "success": True,
            "constraints": cached.constraints.model_dump(),
            "confidence": cached.confidence,
            "usage": usage_stats,
            "meta": {
                "model": cached.model,
                "duration_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_hit": True,
            },
        }

    started = _time.perf_counter()
    try:
        # Parse using AI
        result = await parse_natural_language(parse_request.prompt, catalog)
        await _ai_cache.set(cache_key, result)

        try:
            await record_ai_tokens(result.input_tokens or 0, result.output_tokens or 0)
        except RateLimitUnavailableError:
            logger.warning("ai_schedule_parse telemetry_unavailable")
        duration_ms = round((_time.perf_counter() - started) * 1000)
        blocking_issue_count = sum(
            issue.severity.value == "blocking" for issue in result.constraints.issues
        )
        logger.info(
            "ai_schedule_parse success duration_ms=%s confidence=%s "
            "blocking_issues=%s course_groups=%s input_tokens=%s output_tokens=%s",
            duration_ms,
            result.confidence,
            blocking_issue_count,
            len(result.constraints.course_groups),
            result.input_tokens,
            result.output_tokens,
        )

        return {
            "success": True,
            "constraints": result.constraints.model_dump(),
            "confidence": result.confidence,
            "usage": usage_stats,
            "meta": {
                "model": result.model,
                "duration_ms": duration_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_hit": False,
            },
        }

    except RuntimeError as exc:
        logger.warning("ai_schedule_parse unavailable error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        logger.warning("ai_schedule_parse invalid error=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as e:
        logger.exception("ai_schedule_parse failed")
        raise HTTPException(status_code=500, detail="Could not interpret that description") from e


@app.get("/ai/usage")
async def get_ai_usage(request: Request):
    """
    Get AI usage statistics for the current user.

    Args:
        request: FastAPI request object (for IP address)

    Returns:
        Usage statistics
    """
    client_ip = request.client.host if request.client else "unknown"
    try:
        return await get_usage_stats(client_ip)
    except RateLimitUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/ai/global-stats")
async def get_ai_global_stats():
    """
    Get global AI usage statistics (admin endpoint).

    Returns:
        Global usage statistics
    """
    try:
        return await get_global_stats()
    except RateLimitUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/export/ics")
async def export_ics(
    schedule: Schedule,
    term_start: str = "2026-09-01",  # Default Fall 2026 start
    term_end: str = "2026-12-13",  # Default Fall 2026 end (last day of classes)
):
    """
    Export a schedule as an ICS calendar file.

    Args:
        schedule: Schedule to export
        term_start: Term start date (YYYY-MM-DD)
        term_end: Term end date (YYYY-MM-DD)

    Returns:
        ICS file download
    """
    try:
        start_date = datetime.strptime(term_start, "%Y-%m-%d")
        end_date = datetime.strptime(term_end, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    ics_bytes = generate_ics(schedule, start_date, end_date)

    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=njit_schedule.ics"},
    )


def _minutes_to_ampm(total_minutes: int) -> str:
    """Convert minutes-from-midnight to 12-hour AM/PM string (e.g. 780 → '1:00 PM')."""
    h = total_minutes // 60
    m = total_minutes % 60
    period = "PM" if h >= 12 else "AM"
    display_h = h % 12 or 12
    return f"{display_h}:{m:02d} {period}"


@app.post("/export/csv")
async def export_csv(schedule: Schedule):
    """
    Export a schedule as a CSV file.

    Args:
        schedule: Schedule to export

    Returns:
        CSV file download
    """
    csv_content = _schedule_to_csv(schedule)
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=njit_schedule.csv"},
    )


DAY_TO_CSV_CODE = {
    "Mon": "M",
    "Tue": "T",
    "Wed": "W",
    "Thu": "R",
    "Fri": "F",
    "Sat": "S",
    "Sun": "U",
}


def _schedule_to_csv(schedule: Schedule) -> str:
    """Serialize every meeting without losing day, time, or location details."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Course",
            "Title",
            "CRN",
            "Section",
            "Days",
            "Times",
            "Location",
            "Instructor",
            "Delivery",
            "Credits",
            "Status",
        ]
    )

    for offering in schedule.offerings:
        meetings = offering.meetings or [None]
        for meeting in meetings:
            writer.writerow(
                [
                    offering.course_key,
                    offering.title,
                    offering.crn,
                    offering.section,
                    DAY_TO_CSV_CODE[meeting.day.value] if meeting else "TBA",
                    (
                        f"{_minutes_to_ampm(meeting.start_min)} - "
                        f"{_minutes_to_ampm(meeting.end_min)}"
                        if meeting
                        else "TBA"
                    ),
                    meeting.location or "" if meeting else "",
                    offering.instructor or "",
                    offering.delivery.value,
                    offering.credits or "",
                    offering.status.value,
                ]
            )

    csv_content = output.getvalue()
    output.close()
    return csv_content


@app.post("/professors/ratings")
async def get_professor_ratings(req: RatingsRequest):
    """
    Fetch RateMyProfessor ratings for a list of instructor names.
    Never raises — returns empty dict if RMP is unreachable.
    """
    if not req.names:
        return {}
    valid = [n for n in req.names if n and n.strip() and n != "Staff TBA"]
    if not valid:
        return {}
    try:
        return await batch_fetch_ratings(valid)
    except Exception:
        return {}


async def _get_prerequisite_value(course_key: str) -> Optional[str]:
    """Fetch and process one prerequisite value with process-local caching."""
    cache_key = course_key.strip().upper()
    if cache_key in _prereqs_cache:
        return _prereqs_cache[cache_key]

    # Build catalog search URL, e.g. "CS 114" → "?P=CS+114"
    search_term = cache_key.replace(" ", "+")

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(
                f"https://catalog.njit.edu/search/?P={search_term}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                # Find the first "Prerequisite" sentence on the page
                match = re.search(
                    r"Prerequisite[s]?:\s*(.*?)(?:<br|</p|<div)",
                    resp.text,
                    re.IGNORECASE | re.DOTALL,
                )
                if match:
                    raw = match.group(1)
                    # Strip HTML tags and collapse whitespace
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    # Keep only the first sentence (prereq condition);
                    # the catalog appends the course description after it
                    first_sentence = re.split(r"\.\s+[A-Z]", clean)[0].rstrip(" .")
                    prereqs = first_sentence if len(first_sentence) > 3 else None
                    _prereqs_cache[cache_key] = prereqs
                    return prereqs
    except Exception:
        pass

    _prereqs_cache[cache_key] = None
    return None


@app.get("/catalog/prerequisites/{course_key:path}")
async def get_prerequisites(course_key: str):
    """Fetch prerequisites for one course."""
    return {"prerequisites": await _get_prerequisite_value(course_key)}


@app.post("/catalog/prerequisites")
async def get_prerequisites_batch(req: PrerequisitesRequest):
    """Fetch prerequisite information for an entire displayed schedule in one request."""
    course_keys = list(dict.fromkeys(key.strip().upper() for key in req.course_keys if key.strip()))
    values = await asyncio.gather(*[_get_prerequisite_value(key) for key in course_keys])
    return dict(zip(course_keys, values))


@app.post("/share")
async def create_share(schedule: Schedule):
    """
    Return a compact token containing the schedule's public CRNs.

    Tokens survive API restarts because the current catalog is authoritative.
    """
    crns = ",".join(sorted({offering.crn for offering in schedule.offerings}))
    if not crns:
        raise HTTPException(status_code=400, detail="Cannot share an empty schedule")
    share_id = base64.urlsafe_b64encode(crns.encode("utf-8")).decode("ascii").rstrip("=")
    return {"id": share_id}


@app.get("/share/{share_id}")
async def get_share(share_id: str):
    """Rebuild a shared schedule from a URL-safe CRN token."""
    if len(share_id) > 512 or not re.fullmatch(r"[A-Za-z0-9_-]+", share_id):
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    try:
        padding = "=" * (-len(share_id) % 4)
        decoded = base64.urlsafe_b64decode(f"{share_id}{padding}").decode("utf-8")
        requested_crns = [crn for crn in decoded.split(",") if crn]
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    if not requested_crns or any(not re.fullmatch(r"[A-Za-z0-9-]+", crn) for crn in requested_crns):
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    offerings_by_crn = {offering.crn: offering for offering in catalog}
    if any(crn not in offerings_by_crn for crn in requested_crns):
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    offerings = [offerings_by_crn[crn] for crn in requested_crns]
    return Schedule(
        offerings=offerings,
        total_credits=sum(offering.credits or 0 for offering in offerings),
        score=0,
    )
