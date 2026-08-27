"""FastAPI main application."""

import base64
import binascii
import csv
import glob
import io
import logging
import os
import re
import time as _time
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.ai_parser import AIParseRequest, parse_natural_language
from app.ics_export import generate_ics
from app.models import Offering, Schedule, SolveRequest, SolveResponse
from app.normalizer import normalize_csv, normalize_multiple_csvs
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
from app.solver import solve_schedules

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NJIT Schedule Pro API",
    description="Backend API for course schedule generation",
    version="1.0.0",
)

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
)

# In-memory catalog storage (can be replaced with database)
catalog: List[Offering] = []
catalog_metadata: Dict = {}

# Prerequisites cache: normalized course_key → prereq text or None
_prereqs_cache: Dict[str, Optional[str]] = {}

class RatingsRequest(BaseModel):
    names: List[str]


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


@app.on_event("startup")
async def startup_event():
    """Load existing CSVs from courseschedules directory on startup."""
    global catalog, catalog_metadata
    catalog, catalog_metadata = _load_catalog_from_disk()


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

    # Get unique course keys for frontend
    unique_courses = {}
    for offering in catalog:
        if offering.course_key not in unique_courses:
            unique_courses[offering.course_key] = {
                "course_key": offering.course_key,
                "title": offering.title,
                "section_count": 0,
            }
        unique_courses[offering.course_key]["section_count"] += 1

    return {
        "offerings": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "unique_courses": list(unique_courses.values()),
        "metadata": catalog_metadata,
    }


@app.get("/catalog/courses")
async def get_courses(search: Optional[str] = None):
    """
    Get list of unique courses with section counts.

    Args:
        search: Optional search filter

    Returns:
        List of courses
    """
    course_map = {}

    for offering in catalog:
        if offering.course_key not in course_map:
            course_map[offering.course_key] = {
                "course_key": offering.course_key,
                "title": offering.title,
                "sections": {},  # Changed to dict to group by CRN
            }

        # Group sections by CRN to avoid duplicates
        crn = offering.crn
        if crn not in course_map[offering.course_key]["sections"]:
            course_map[offering.course_key]["sections"][crn] = {
                "crn": offering.crn,
                "section": offering.section,
                "status": offering.status.value,
                "delivery": offering.delivery.value,
                "instructor": offering.instructor,
                "credits": offering.credits,
            }

    # Convert sections dict back to list
    courses = []
    for course_data in course_map.values():
        course_data["sections"] = list(course_data["sections"].values())
        courses.append(course_data)

    if search:
        search_lower = search.lower()
        courses = [
            c
            for c in courses
            if search_lower in c["course_key"].lower() or search_lower in c["title"].lower()
        ]

    return {"courses": courses, "total": len(courses)}


@app.post("/solve", response_model=SolveResponse)
async def solve(request_body: SolveRequest, request: Request):
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

    # Validate required courses exist
    catalog_course_keys = {o.course_key for o in catalog}
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

    catalog_crns = {o.crn for o in catalog}
    missing_crns = [crn for crn in request_body.required_crns if crn not in catalog_crns]
    if missing_crns:
        raise HTTPException(
            status_code=400, detail=f"Required CRNs not found in catalog: {', '.join(missing_crns)}"
        )

    # Solve
    schedules = solve_schedules(catalog, request_body)

    # Count unique courses in catalog
    unique_courses = len(set(o.course_key for o in catalog))

    return SolveResponse(
        schedules=schedules,
        count=len(schedules),
        catalog_course_count=unique_courses,
        catalog_section_count=len(catalog),
    )


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

    started = _time.perf_counter()
    try:
        # Parse using AI
        result = await parse_natural_language(parse_request.prompt, catalog)

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


@app.get("/catalog/prerequisites/{course_key:path}")
async def get_prerequisites(course_key: str):
    """
    Fetch prerequisites for a course from the NJIT course catalog.
    Scrapes catalog.njit.edu and caches results in memory.
    """
    cache_key = course_key.strip().upper()
    if cache_key in _prereqs_cache:
        return {"prerequisites": _prereqs_cache[cache_key]}

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
                    return {"prerequisites": prereqs}
    except Exception:
        pass

    _prereqs_cache[cache_key] = None
    return {"prerequisites": None}


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
